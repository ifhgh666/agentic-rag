"""真实词表加载失败应在问答前暴露；同版本稳定性不能混用旧响应。"""

import hashlib
import json

import pytest

from app.config import Settings
from scripts.replay_v3_6_q3 import verified_bm25_cache
from scripts.smoke_v3_8 import captures_stable


def test_q3_needs_three_distinct_requests_same_version_not_one_reused_answer():
    rows = [{"case_id": "Q3", "literal_checks_passed": True, "request_id": str(i), "source_fingerprint": "version"}
            for i in range(3)]
    assert not captures_stable(rows[:2]) and captures_stable(rows)
    rows[2]["request_id"] = "0"
    assert not captures_stable(rows)
    rows[2]["request_id"] = "2"
    rows[2]["source_fingerprint"] = "another-version"
    assert not captures_stable(rows)


def test_default_stopword_cache_must_match_metadata_before_model_use(tmp_path, monkeypatch):
    root = tmp_path / "models--Qdrant--bm25"
    directory = root / "snapshots/revision"
    directory.mkdir(parents=True)
    word_file = directory / "english.txt"
    content = b"the\nand\n"
    word_file.write_bytes(content)
    metadata = {str(word_file.relative_to(root)): {
        "size": len(content), "blob_id": hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()}}
    (root / "files_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    monkeypatch.setattr("fastembed.common.utils.define_cache_dir", lambda _: tmp_path)
    monkeypatch.setattr("huggingface_hub.snapshot_download", lambda **kwargs: str(directory))
    settings = Settings(_env_file=None, sparse_offline_fallback=False)
    assert verified_bm25_cache(settings) == directory
    word_file.write_bytes(b"changed")
    with pytest.raises(ValueError, match="不匹配"):
        verified_bm25_cache(settings)
