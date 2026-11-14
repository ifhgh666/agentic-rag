"""V3-7 五题本地冒烟；实际运行 Graph，不用标准答案填充响应，不执行 RAGAS。"""

from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.config import Settings
from scripts.replay_v3_6_q3 import (
    BACKEND_ROOT, DEFAULT_CASE, capture_local_once, digest, inspect_q3_steps,
    protected_files, validate_local_capture_settings,
)


OUTPUT_ROOT = BACKEND_ROOT / "tmp/v3-7"
QUESTIONS = {
    "Q1": "设备上电前需要检查哪些内容？",
    "Q2": "PX-200 的过流保护阈值是多少？",
    "Q3": "过流保护后如何恢复？",
    "Q4": "运行记录默认保留多久？",
    "Q5": "设备多久进行一次例行维护？",
}
# 仅测试验收定位，绝不传给生成模型；不是生产意图规则或语义评分。
FACT_PROBES = {
    "Q1": [("接地",), ("负载",), ("急停",), ("保护指示灯",), ("故障",)],
    "Q2": [("16A",), ("100ms",)],
    "Q4": [("三年", "3年"), ("先进先出",)],
    "Q5": [("六个月", "6个月"),],
}


def inspect_capture(capture: dict, q3_case: dict) -> dict:
    case_id = capture["case_id"]
    body = capture["response"].split("\n\n依据：", 1)[0]
    normalized = "".join(body.split())
    missing = [list(terms) for terms in FACT_PROBES.get(case_id, [])
               if not any(term in normalized for term in terms)]
    cost = capture["answer_cost"]
    sources = capture.get("sources", [])
    check = {
        "case_id": case_id, "question": capture["question"], "response": capture["response"],
        "status": capture["status"], "sources": sources, "usage": cost,
        "missing_fixture_facts": missing,
        "kind": "fixture_literal_checks_not_ragas_or_semantic_judge",
        "verification": capture["verification"],
        "human_semantic_review_required": True,
    }
    passed = (capture["status"] == "completed" and not missing and bool(sources)
              and cost["model_calls"] <= 2 and cost["cloud_calls"] == 0
              and not cost["budget_exceeded"] and capture["protected_files_unchanged"])
    if case_id == "Q3":
        probe = inspect_q3_steps(capture["response"], q3_case)
        check["step_probe"] = probe
        check["detailed_page_cited"] = any(item.get("page_start") == 3 for item in sources)
        check["procedure_extract"] = any(item.get("validation_status") == "procedure_extract"
                                         for item in capture["model_trace"])
        passed = (passed and not probe["missing_steps"] and probe["ordered"]
                  and check["detailed_page_cited"] and check["procedure_extract"])
    check["literal_checks_passed"] = passed
    return check


def load_current_q3(path: Path, settings: Settings) -> dict:
    capture = json.loads(path.read_text(encoding="utf-8"))
    current = {name: digest(file) for name, file in protected_files(settings).items()}
    if (capture.get("capture_kind") != "formal_index_snapshot_graph_run"
        or capture.get("case_id") != "Q3" or capture.get("question") != QUESTIONS["Q3"]
        or capture.get("protected_hashes_before") != current
        or capture.get("protected_hashes_after") != current
        or not capture.get("model_calls") or capture.get("workbench_ui_run") is not False):
        raise ValueError("不能复用过期、模拟或来源指纹不一致的 Q3 捕获")
    return capture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-local", action="store_true", help="必须显式启用本地模型调用")
    parser.add_argument("--reuse-q3", type=Path, help="复用当前代码与正式数据指纹一致的实际 Q3 捕获")
    args = parser.parse_args()
    if not args.capture_local:
        parser.error("请显式指定 --capture-local；不会自动调用模型")
    settings = Settings()
    validate_local_capture_settings(settings)
    case = json.loads(DEFAULT_CASE.read_text(encoding="utf-8"))
    # 首先校验复用输入，避免四题完成后才发现 Q3 已过期。
    reused = load_current_q3(args.reuse_q3.resolve(), settings) if args.reuse_q3 else None
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    run_dir = OUTPUT_ROOT / f"smoke-{uuid4().hex[:8]}"
    run_dir.mkdir()
    rows = []
    for case_id, question in QUESTIONS.items():
        actual_case = copy.deepcopy(case)
        actual_case.update({"case_id": case_id, "question": question})
        if case_id == "Q3" and reused is not None:
            result = load_current_q3(args.reuse_q3.resolve(), settings)
            artifact = args.reuse_q3.resolve()
        else:
            result = capture_local_once(actual_case, settings)
            artifact = run_dir / f"{case_id.lower()}-capture.json"
            artifact.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        row = inspect_capture(result, case)
        row.update({"raw_capture": str(artifact.relative_to(BACKEND_ROOT.parent).as_posix()),
                    "raw_capture_sha256": digest(artifact), "reused_capture": case_id == "Q3" and reused is not None})
        rows.append(row)
        print(json.dumps({"case_id": case_id, "artifact": str(artifact),
                          "literal_checks_passed": row["literal_checks_passed"], "usage": row["usage"]},
                         ensure_ascii=False), flush=True)
        if not row["literal_checks_passed"]:
            break  # 不挑选结果，不无界重试；先保留本次失败。
    report = {
        "schema_version": 1, "captured_at": datetime.now(timezone.utc).isoformat(),
        "workbench_ui_run": False, "ragas_run": False, "judge_calls": 0,
        "cases": rows, "literal_checks_passed": len(rows) == 5 and all(row["literal_checks_passed"] for row in rows),
        "totals_for_five_captures": {key: sum(row["usage"][key] for row in rows)
                                     for key in ("model_calls", "total_tokens", "duration_ms", "cloud_calls")},
        "human_semantic_review_required": True,
    }
    report_path = run_dir / "summary.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"summary": str(report_path), "literal_checks_passed": report["literal_checks_passed"]},
                     ensure_ascii=False), flush=True)
    if not report["literal_checks_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
