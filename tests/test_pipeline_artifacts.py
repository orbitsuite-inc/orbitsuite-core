from pathlib import Path
from typing import Dict, Any
from src.supervisor import Supervisor


def test_codegen_pipeline_artifacts(tmp_path: Path, monkeypatch: Any) -> None:  # type: ignore[name-defined]
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    sup = Supervisor()
    resp: Dict[str, Any] = sup.process_request("Generate a simple Python function that returns 42")
    assert resp.get("success"), resp
    inner: Dict[str, Any] = {}
    result = resp.get("result")
    if isinstance(result, dict):
        inner = result.get("result") if isinstance(result.get("result"), dict) else result  # type: ignore[assignment]
    pipeline_artifacts: Dict[str, Any] = inner.get("pipeline_artifacts", {}) if isinstance(inner, dict) else {}
    codegen_path = pipeline_artifacts.get("codegen_artifact")
    assert isinstance(codegen_path, str) and codegen_path, f"No codegen artifact recorded: {pipeline_artifacts}"
    assert Path(codegen_path).exists(), f"Codegen artifact file missing: {codegen_path}"
    tester_path = pipeline_artifacts.get("tester_artifact")
    if isinstance(tester_path, str):
        assert Path(tester_path).exists(), f"Tester artifact missing: {tester_path}"
    patcher_path = pipeline_artifacts.get("patcher_artifact")
    if isinstance(patcher_path, str):
        assert Path(patcher_path).exists(), f"Patcher artifact missing: {patcher_path}"
