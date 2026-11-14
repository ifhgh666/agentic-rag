"""同一版本 Q3 三次及五题隔离回归；必须显式调用本机模型，不运行 Judge。"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from app.config import Settings
from scripts.replay_v3_6_q3 import BACKEND_ROOT, DEFAULT_CASE, capture_local_once, digest, protected_files
from scripts.smoke_v3_7 import QUESTIONS, inspect_capture


OUTPUT_ROOT = BACKEND_ROOT / "tmp/v3-8"


def captures_stable(rows: list[dict]) -> bool:
    q3 = [row for row in rows if row["case_id"] == "Q3"]
    return (len(q3) == 3 and all(row["literal_checks_passed"] for row in q3)
            and len({row["request_id"] for row in q3}) == 3
            and len({row["source_fingerprint"] for row in q3}) == 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-local", action="store_true")
    args = parser.parse_args()
    if not args.capture_local:
        parser.error("必须显式指定 --capture-local；默认不调用模型")
    settings = Settings()
    case = json.loads(DEFAULT_CASE.read_text(encoding="utf-8"))
    fingerprint = {name: digest(path) for name, path in protected_files(settings).items()}
    version = hashlib.sha256(json.dumps(fingerprint, sort_keys=True).encode()).hexdigest()
    run_dir = OUTPUT_ROOT / f"snapshot-{uuid4().hex[:8]}"
    run_dir.mkdir(parents=True)
    rows = []
    plan = [("Q3", index) for index in range(1, 4)] + [(key, 1) for key in ("Q1", "Q2", "Q4", "Q5")]
    for case_id, attempt in plan:
        current = {name: digest(path) for name, path in protected_files(settings).items()}
        if current != fingerprint:
            raise RuntimeError("版本或正式数据变化，不能把不同版本算作连续三次")
        actual_case = copy.deepcopy(case)
        actual_case.update({"case_id": case_id, "question": QUESTIONS[case_id]})
        capture = capture_local_once(actual_case, settings, use_configured_sparse=True)
        artifact = run_dir / f"{case_id.lower()}-{attempt}.json"
        artifact.write_text(json.dumps(capture, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        row = inspect_capture(capture, case)
        row.update({"attempt": attempt, "raw_capture": artifact.relative_to(BACKEND_ROOT.parent).as_posix(),
                    "raw_capture_sha256": digest(artifact), "request_id": capture["request_id"],
                    "source_fingerprint": version,
                    "configured_sparse_encoder": capture["configured_sparse_encoder"]})
        rows.append(row)
        report = {"schema_version": 1, "captured_at": datetime.now(timezone.utc).isoformat(),
                  "workbench_ui_run": False, "ragas_run": False, "judge_calls": 0,
                  "cases": rows, "q3_three_consecutive_passed": captures_stable(rows),
                  "all_cases_passed": len(rows) == 7 and all(item["literal_checks_passed"] for item in rows),
                  "protected_hashes": fingerprint,
                  "totals": {key: sum(item["usage"][key] for item in rows)
                             for key in ("model_calls", "total_tokens", "duration_ms", "cloud_calls")},
                  "human_semantic_review_required": True}
        # 每题更新，异常或中断仍留已完成结果，不挑选成功样本。
        (run_dir / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"case_id": case_id, "attempt": attempt, "artifact": str(artifact),
                          "passed": row["literal_checks_passed"], "usage": row["usage"]}, ensure_ascii=False), flush=True)
        if not row["literal_checks_passed"]:
            raise SystemExit(1)
    print(json.dumps({"summary": str(run_dir / "summary.json"), "q3_three_consecutive_passed": captures_stable(rows)},
                     ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
