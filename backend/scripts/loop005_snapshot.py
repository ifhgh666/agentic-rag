"""Save the pre-change worktree and immutable knowledge hashes; no credentials."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / "output" / "loop005-baseline"

def knowledge_hashes():
    data = ROOT / "backend" / "data"
    return {p.relative_to(data).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in data.rglob("*") if p.is_file() and
            (p.suffix.lower() in {".pdf", ".md"} or "parent" in p.name.lower() or
             "manifest" in p.name.lower() or p.name == "documents.json")}

if __name__ == "__main__":
    DEST.mkdir(parents=True, exist_ok=True)
    if (DEST / "snapshot.json").exists():
        raise SystemExit("Snapshot already exists; refusing to overwrite")
    files = {}
    for folder in ("backend/app", "backend/tests", "frontend/src"):
        for p in (ROOT / folder).rglob("*"):
            if p.is_file() and p.suffix in {".py", ".ts", ".tsx", ".css"}:
                relative = p.relative_to(ROOT)
                target = DEST / "files" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, target)
                files[relative.as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    status = subprocess.check_output(["git", "status", "--short"], cwd=ROOT).decode("utf-8")
    (DEST / "worktree.diff").write_bytes(subprocess.check_output(["git", "diff", "--binary"], cwd=ROOT))
    (DEST / "snapshot.json").write_text(json.dumps({"files": files, "knowledge": knowledge_hashes(),
        "status": status}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"source_files": len(files), "knowledge_files": len(knowledge_hashes())}))
