"""Centralized minimal type definitions for OrbitSuite Core.

This trimmed module intentionally limits exports to the small set currently
consumed by the orchestrator to reduce type noise during the staged refactor.
"""
from __future__ import annotations
from typing import TypedDict, List, Dict, Any, Literal

StepAction = Literal['execute_agent']
StepStatus = Literal['completed', 'failed', 'skipped']

class StepExecution(TypedDict, total=False):
    step: int
    action: StepAction
    agent: str
    status: StepStatus
    output: str
    agent_result: Dict[str, Any]

class PipelineArtifacts(TypedDict, total=False):
    codegen_artifact: str
    tester_artifact: str
    patcher_artifact: str
    final_output: str
    executable_artifact: str
    executable_note: str
    executable_note_text: str
    spec_path: str
    design_path: str
    plan_path: str
    traceability_path: str
    generated_files: List[str]
    executable_build_args: str
    executable_build_root: str
    executable_build_log: str
    task_slug: str
    task_dir: str

def unwrap_legacy_agent_output(obj: Any) -> Any:
    return obj

__all__ = ['StepAction','StepStatus','StepExecution','PipelineArtifacts','unwrap_legacy_agent_output']
