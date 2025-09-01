# core/src/orchestrator_agent.py
# Enhanced Orchestrator Agent with real agent execution and engineer->codegen pre-step
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from typing import (
    Dict,
    Any,
    List,
    TypedDict,
    cast,
    Optional,
    Literal,
)

# Stage 1 typing imports (progressive integration)
try:
    from .orbit_types import StepAction, StepStatus, PipelineArtifacts as TypedPipelineArtifacts, unwrap_legacy_agent_output  # type: ignore
except Exception:  # pragma: no cover
    # Fallback if running in an environment before new module packaged
    StepAction = type('StepAction', (), {'EXECUTE_AGENT': 'execute_agent'})  # type: ignore
    StepStatus = type('StepStatus', (), {'COMPLETED': 'completed', 'FAILED': 'failed', 'SKIPPED': 'skipped'})  # type: ignore
    unwrap_legacy_agent_output = lambda x: x  # type: ignore

from src.base_agent import BaseAgent
from src.utils import is_verbose  # lightweight verbosity helper


class Task(TypedDict, total=False):
    """Incoming task description produced by TaskLinguist or direct caller."""
    task_id: str
    type: str
    description: str
    agent_target: str
    input: Any


class StepExecution(TypedDict, total=False):
    """Single executed (or planned) step record."""
    step: int
    action: str
    agent: str
    status: Literal["completed", "failed", "skipped"]
    output: str
    agent_result: Dict[str, Any]


class ExecutionPlan(TypedDict):
    """Static execution plan before run (may be prefixed with engineer pre-step)."""
    steps: List[Dict[str, Any]]  # kept generic to allow simple extension
    estimated_time: int
    complexity: str
    dependencies: List[Dict[str, Any]]


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
    # Added build diagnostics
    executable_build_args: str
    executable_build_root: str
    executable_build_log: str
    task_slug: str
    task_dir: str


class PlanExecutionResult(TypedDict, total=False):
    plan_executed: bool
    steps_completed: int
    steps_failed: int
    execution_details: List[StepExecution]
    final_status: Literal["success", "partial"]
    agent_output: Dict[str, Any]
    pipeline_artifacts: PipelineArtifacts


class SingleTaskExecutionResult(TypedDict, total=False):
    success: bool
    task_id: str
    agent_used: str
    execution_plan: ExecutionPlan
    result: PlanExecutionResult


class BatchExecutionResult(TypedDict, total=False):
    success: bool
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    results: List[SingleTaskExecutionResult]


OrchestratorReturn = Dict[str, Any]  # outward facing (kept broad for external callers)


class Dependency(TypedDict):
    task_index: int
    depends_on: int
    reason: str


class OrchestratorAgent(BaseAgent):
    """Coordinates tasks; executes agents with optional engineering pre-analysis."""

    def __init__(self):
        super().__init__(name="orchestrator")
        self.version = "enhanced-1.1"
        self.agents: Dict[str, BaseAgent] = {}
        self.task_queue: List[Dict[str, Any]] = []

    def run(self, input_data: Dict[str, Any]) -> OrchestratorReturn:  # public surface kept broad
        if not input_data:
            return {"success": False, "error": "Task input required"}
        # Optional streaming callback: caller may pass a callable under '_progress_cb'
        self._progress_cb = input_data.get('_progress_cb') if isinstance(input_data, dict) else None  # type: ignore[attr-defined]
        tasks_data = cast(List[Dict[str, Any]], input_data.get("tasks", []))
        if tasks_data:
            tasks = [self._convert_to_task(t) for t in tasks_data]
            return cast(OrchestratorReturn, self._execute_task_batch(tasks))
        task_data = cast(Dict[str, Any], input_data.get("task", {}))
        if task_data:
            return cast(OrchestratorReturn, self._execute_single_task(self._convert_to_task(task_data)))
        return cast(OrchestratorReturn, self._execute_single_task(self._convert_to_task(input_data)))

    # --- Core Execution Paths ---
    def _execute_single_task(self, task: Task) -> SingleTaskExecutionResult:
        task_id = task.get("task_id", f"task_{len(self.task_queue)}")
        description = task.get("description", "")
        agent_target = task.get("agent_target", self._determine_agent_for_task(task))
        
        # Create task directory early so engineer agent can use it
        import hashlib
        from pathlib import Path as _P
        slug_words = [w for w in description.lower().replace(",", " ").replace(".", " ").split() if w.isalnum()][:8]
        slug_base = "-".join(slug_words) if slug_words else "general-task"
        h = hashlib.sha1(description.encode()).hexdigest()[:8]
        task_slug = f"{slug_base}_{h}"[:56]
        task_dir = _P.cwd() / 'output' / task_slug
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / 'engineering').mkdir(exist_ok=True)
        (task_dir / 'codegen').mkdir(exist_ok=True)
        (task_dir / 'final').mkdir(exist_ok=True)
        (task_dir / 'tests').mkdir(exist_ok=True)
        (task_dir / 'patches').mkdir(exist_ok=True)
        (task_dir / 'tmpdist').mkdir(exist_ok=True)
        
        # Promote generic tasks to a full pipeline: engineer -> codegen -> tester -> patcher
        is_generic = agent_target == "unassigned" or task.get("type", "").lower() in ("general", "")
        if is_generic:
            agent_target = "codegen"
        engineer_result: Optional[Dict[str, Any]] = None
        pre_steps: List[Dict[str, Any]] = []
        if agent_target == "codegen" and not any(k in description.lower() for k in ("spec", "architecture", "design")):
            engineer_agent = self.agents.get("engineer")
            if engineer_agent:
                try:
                    eng_payload = {
                        "command": "analyze", 
                        "description": description, 
                        "project_type": "web_application",
                        "output_dir": str(task_dir)
                    }
                    engineer_result = engineer_agent.dispatch(eng_payload)  # type: ignore[arg-type]
                    # If agent returned a coroutine (async run), resolve it
                    import asyncio
                    if hasattr(engineer_result, '__await__'):
                        engineer_result = asyncio.run(engineer_result)  # type: ignore[assignment]
                    # Attempt file plan generation if analysis succeeded
                    if engineer_result is not None and isinstance(engineer_result, dict) and cast(Dict[str, Any], engineer_result).get("success"):
                        try:
                            plan_res = engineer_agent.dispatch({
                                "command": "plan_files",
                                "description": description,
                                "analysis": cast(Dict[str, Any], engineer_result).get("core_analysis", {}),
                                "project_type": "web_application",
                                "output_dir": str(task_dir)
                            })
                            if hasattr(plan_res, '__await__'):
                                import asyncio as _a
                                plan_res = _a.run(plan_res)  # type: ignore[assignment]
                            if isinstance(plan_res, dict) and cast(Dict[str, Any], plan_res).get("success"):
                                engineer_result["file_plan"] = plan_res
                        except Exception:  # pragma: no cover
                            pass
                    pre_steps.append({
                        "step": 0,
                        "action": "engineer_analysis",
                        "agent": "engineer",
                        "status": "completed" if engineer_result is not None and isinstance(engineer_result, dict) and cast(Dict[str, Any], engineer_result).get("success") else "failed",
                        "output": cast(Dict[str, Any], engineer_result).get("artifact_dir") if engineer_result is not None and isinstance(engineer_result, dict) else "analysis_skipped",
                    })
                except Exception as e:  # pragma: no cover
                    pre_steps.append({
                        "step": 0,
                        "action": "engineer_analysis",
                        "agent": "engineer",
                        "status": "skipped",
                        "output": f"engineer error: {e}",
                    })
        plan = self._create_execution_plan(task, agent_target)
        if pre_steps:
            plan["steps"] = pre_steps + plan["steps"]
        # Ensure precise typing for engineer_result before passing along
        engineer_result = cast(Optional[Dict[str, Any]], engineer_result)
        # Execute full plan (engineer pre-step + main pipeline)
        exec_result = self._execute_plan(plan, task, engineer_result)
        return cast(SingleTaskExecutionResult, {
            "success": True,
            "task_id": task_id,
            "agent_used": agent_target,
            "execution_plan": plan,
            "result": exec_result,
        })

    def _execute_task_batch(self, tasks: List[Task]) -> BatchExecutionResult:
        results: List[SingleTaskExecutionResult] = []
        for i, t in enumerate(tasks):
            r = self._execute_single_task(t)
            # augment with non-schema key for diagnostics (not part of TypedDict contract)
            cast(Dict[str, Any], r)["batch_index"] = i  # type: ignore[index]
            results.append(r)
        success_count = sum(1 for r in results if r.get("success"))
        return cast(BatchExecutionResult, {
            "success": success_count == len(results),
            "total_tasks": len(results),
            "successful_tasks": success_count,
            "failed_tasks": len(results) - success_count,
            "results": results,
        })

    # --- Planning & Execution Helpers ---
    def _determine_agent_for_task(self, task: Task) -> str:
        desc = task.get("description", "").lower()
        ttype = task.get("type", "").lower()
        if ttype == "codegen" or any(w in desc for w in ("code", "generate", "write", "implement")):
            return "codegen"
        if ttype == "testing" or any(w in desc for w in ("test", "verify", "check", "validate")):
            return "tester"
        if ttype == "patching" or any(w in desc for w in ("fix", "patch", "repair", "debug")):
            return "patcher"
        if ttype == "engineering" or any(w in desc for w in ("design", "architect", "plan", "requirements")):
            return "engineer"
        if ttype == "memory" or any(w in desc for w in ("save", "store", "remember", "recall")):
            return "memory"
        return "unassigned"

    def _create_execution_plan(self, task: Task, agent_target: str) -> ExecutionPlan:
        return cast(ExecutionPlan, {
            "steps": [
                {"step": 1, "action": "validate_input", "description": "Validate task input parameters"},
                {"step": 2, "action": "execute_agent", "agent": agent_target, "description": f"Execute task using {agent_target} agent"},
                {"step": 3, "action": "validate_output", "description": "Validate and format output"},
            ],
            "estimated_time": 30,
            "complexity": self._assess_complexity(task),
            "dependencies": [],
        })

    def _execute_plan(self, plan: ExecutionPlan, task: Task, engineer_result: Optional[Dict[str, Any]]) -> PlanExecutionResult:
        """Execute full plan via decomposed helper steps (Stage 1 extraction)."""
        executed: List[StepExecution] = []
        pipeline_artifacts: PipelineArtifacts = {}
        if engineer_result:
            self._propagate_engineer_artifacts(engineer_result, pipeline_artifacts)
        final_output, failures = self._run_plan_steps(plan, task, engineer_result, executed, pipeline_artifacts)
        if final_output and ("code" in final_output or pipeline_artifacts.get('generated_files')):
            self._run_quality_and_patch_chain(task, executed, pipeline_artifacts, final_output)
        if pipeline_artifacts.get('generated_files'):
            self._generate_traceability(task, pipeline_artifacts)
        return cast(PlanExecutionResult, {
            "plan_executed": True,
            "steps_completed": len([x for x in executed if x.get("status") == "completed"]),
            "steps_failed": failures,
            "execution_details": executed,
            "final_status": "success" if failures == 0 else "partial",
            "agent_output": final_output or {},
            "pipeline_artifacts": pipeline_artifacts,
        })

    # --- Step Helpers ---
    def _propagate_engineer_artifacts(self, engineer_result: Dict[str, Any], artifacts: PipelineArtifacts) -> None:
        for k in ("spec_path", "plan_path", "design_path"):
            if engineer_result.get(k):
                artifacts[k] = engineer_result.get(k)  # type: ignore[assignment]

    def _run_plan_steps(self, plan: ExecutionPlan, task: Task, engineer_result: Optional[Dict[str, Any]], executed: List[StepExecution], artifacts: PipelineArtifacts) -> tuple[Optional[Dict[str, Any]], int]:
        final_output: Optional[Dict[str, Any]] = None
        failures = 0
        for step in plan.get("steps", []):
            record: StepExecution = {
                "step": step.get("step", -1),
                "action": step.get("action", "unknown"),
                "status": "completed",
                "output": f"Step {step.get('step')} executed successfully",
            }
            self._emit_progress('step_start', record)
            if record["action"] == "execute_agent":
                agent_name = step.get("agent", "unassigned")
                record["agent"] = agent_name
                if agent_name == "unassigned" or agent_name not in self.agents:
                    record["status"] = "skipped"
                    record["output"] = "No agent assigned (Core has no fallback)"
                else:
                    try:
                        final_output = self._execute_primary_agent(agent_name, task, engineer_result, record, artifacts)
                    except Exception as e:  # pragma: no cover
                        failures += 1
                        record["status"] = "failed"
                        record["output"] = f"agent error: {e}"
            executed.append(record)
            self._emit_progress('step_end', record)
        return final_output, failures

    def _execute_primary_agent(self, agent_name: str, task: Task, engineer_result: Optional[Dict[str, Any]], record: StepExecution, artifacts: PipelineArtifacts) -> Optional[Dict[str, Any]]:
        # Calculate task directory for consistent output paths
        from pathlib import Path as _P
        import hashlib
        description = task.get('description', '') or 'task'
        slug_words = [w for w in description.lower().replace(",", " ").replace(".", " ").split() if w.isalnum()][:8]
        slug_base = "-".join(slug_words) if slug_words else "general-task"
        h = hashlib.sha1(description.encode()).hexdigest()[:8]
        task_slug = f"{slug_base}_{h}"[:56]
        task_dir = str(_P.cwd() / 'output' / task_slug)
        
        payload: Dict[str, Any] = {
            "prompt": task.get("description", ""),
            "description": task.get("description", ""),
            "task_id": task.get("task_id", ""),
            "output_dir": task_dir + "/codegen",  # Include codegen subdirectory
        }
        if engineer_result and engineer_result.get("success"):
            payload["spec"] = engineer_result.get("core_analysis", {})
        file_plan = self._extract_file_plan(engineer_result)
        if file_plan:
            return self._execute_file_plan(agent_name, task, file_plan, record, artifacts)
        # Single output path
        dispatched: Any = self.agents[agent_name].dispatch(payload)
        normalized = cast(Dict[str, Any], unwrap_legacy_agent_output(dispatched))
        final_output = normalized
        record["output"] = "agent_executed"
        record["agent_result"] = {k: final_output[k] for k in list(final_output)[:5]}
        if final_output.get("artifact_path"):
            artifacts.setdefault("codegen_artifact", str(final_output["artifact_path"]))
        return final_output

    def _extract_file_plan(self, engineer_result: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not engineer_result or not isinstance(engineer_result.get("file_plan"), dict):
            return []
        plan_dict_any = engineer_result["file_plan"]
        plan_dict: Dict[str, Any] = cast(Dict[str, Any], plan_dict_any)
        raw_plan_val = plan_dict.get("plan")
        file_plan: List[Dict[str, Any]] = []
        if isinstance(raw_plan_val, list):
            for fp_any in raw_plan_val: # type: ignore
                fp_any = cast(Any, fp_any)
                fp_dict = cast(Dict[str, Any], fp_any)
                file_plan.append(fp_dict)
        return file_plan

    def _execute_file_plan(self, agent_name: str, task: Task, file_plan: List[Dict[str, Any]], record: StepExecution, artifacts: PipelineArtifacts) -> Dict[str, Any]:
        from pathlib import Path as _P
        
        # Use existing task directory structure (created in _execute_single_task)
        desc = task.get('description', '') or 'task'
        words = [w for w in desc.lower().split() if w.isalnum()][:6]
        slug_base = '-'.join(words) if words else 'task'
        import hashlib
        h = hashlib.sha1(desc.encode()).hexdigest()[:8]
        task_slug = f"{slug_base}_{h}"[:56]
        
        # Task directory should already exist from _execute_single_task
        task_dir = _P.cwd() / 'output' / task_slug
        base_codegen_dir = task_dir / 'codegen'
        
        generated_files: List[str] = []
        codegen_agent = self.agents[agent_name]
        for fp_entry in file_plan:
            rel_path: str = str(fp_entry.get('path') or fp_entry.get('file') or 'main.py')
            purpose: str = str(fp_entry.get('purpose', ''))
            lang: str = str(fp_entry.get('language', 'python'))
            cg_prompt: str = (f"Task: {task.get('description','')}\n"
                              f"Implement file '{rel_path}' for: {purpose}. Provide ONLY {lang} code.")
            cg_payload: Dict[str, str] = {
                'prompt': cg_prompt, 
                'language': lang, 
                'task_id': str(task.get('task_id','')),
                'output_dir': str(base_codegen_dir),
                'target_rel_path': rel_path
            }
            cg_out_any: Any = codegen_agent.dispatch(cg_payload)  # type: ignore[arg-type]
            if isinstance(cg_out_any, dict):
                artifact_val = cast(Dict[str, Any], cg_out_any).get('artifact_path')
                if isinstance(artifact_val, str):
                    src_file = _P(artifact_val)
                    target = base_codegen_dir / rel_path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        target.write_text(src_file.read_text(encoding='utf-8'), encoding='utf-8')
                        generated_files.append(str(target))
                    except Exception:  # pragma: no cover
                        pass
        if generated_files:
            artifacts.setdefault('generated_files', generated_files)
            artifacts.setdefault('codegen_artifact', generated_files[0])
            artifacts.setdefault('task_dir', str(task_dir))
            artifacts.setdefault('task_slug', task_slug)
            record['output'] = 'agent_executed'
            record['agent_result'] = {'files': len(generated_files)}
            return {'success': True, 'generated_files': generated_files, 'code': ''}
        return {'success': False}

    def _run_quality_and_patch_chain(self, task: Task, executed: List[StepExecution], artifacts: PipelineArtifacts, final_output: Dict[str, Any]) -> None:
        code_text = str(final_output.get("code", ""))
        if not code_text and artifacts.get('generated_files'):
            code_text = self._aggregate_generated_files(artifacts, final_output)
        
        # Calculate task directory for consistent agent output paths
        from pathlib import Path as _P
        import hashlib
        description = task.get('description', '') or 'task'
        slug_words = [w for w in description.lower().replace(",", " ").replace(".", " ").split() if w.isalnum()][:8]
        slug_base = "-".join(slug_words) if slug_words else "general-task"
        h = hashlib.sha1(description.encode()).hexdigest()[:8]
        task_slug = f"{slug_base}_{h}"[:56]
        task_dir = str(_P.cwd() / 'output' / task_slug)
        
        next_idx = (max([e.get("step", 0) for e in executed]) + 1) if executed else 1
        next_idx = self._invoke_tester(code_text, executed, artifacts, next_idx, task_dir)
        self._invoke_patcher_and_finalize(task, code_text, executed, artifacts, next_idx, task_dir)

    def _aggregate_generated_files(self, artifacts: PipelineArtifacts, final_output: Dict[str, Any]) -> str:
        try:
            aggregated_parts: List[str] = []
            import pathlib
            for fp in artifacts.get('generated_files', [])[:10]:
                p = pathlib.Path(fp)
                if p.exists() and p.suffix in ('.py', '.js', '.ts'):
                    txt = p.read_text(encoding='utf-8')
                    aggregated_parts.append(f"# FILE: {p.name}\n" + txt[:4000])
            if aggregated_parts:
                combined = "\n\n".join(aggregated_parts)
                final_output['combined_code'] = f"Aggregated {len(aggregated_parts)} files"
                return combined
        except Exception:  # pragma: no cover
            pass
        return ""

    def _invoke_tester(self, code_text: str, executed: List[StepExecution], artifacts: PipelineArtifacts, next_idx: int, task_dir: str) -> int:
        tester = self.agents.get("tester")
        if tester and code_text:
            try:
                test_res = tester.dispatch({
                    "type": "syntax_check", 
                    "target": code_text,
                    "output_dir": task_dir
                })
                executed.append({
                    "step": next_idx,
                    "action": "tester_validation",
                    "agent": "tester",
                    "status": "completed" if test_res.get("success") else "failed",
                    "output": "tester_executed",
                    "agent_result": {k: test_res[k] for k in list(test_res)[:5]},
                })
                if test_res.get("artifact_path"):
                    artifacts.setdefault("tester_artifact", str(test_res["artifact_path"]))
            except Exception as e:  # pragma: no cover
                executed.append({
                    "step": next_idx,
                    "action": "tester_validation",
                    "agent": "tester",
                    "status": "failed",
                    "output": f"tester error: {e}",
                })
            next_idx += 1
        return next_idx

    def _invoke_patcher_and_finalize(self, task: Task, code_text: str, executed: List[StepExecution], artifacts: PipelineArtifacts, next_idx: int, task_dir: str) -> None:
        patcher = self.agents.get("patcher")
        if not (patcher and code_text):
            return
        try:
            patch_res = patcher.dispatch({
                "type": "auto", 
                "code": code_text, 
                "issues": [],
                "output_dir": task_dir
            })
            executed.append({
                "step": next_idx,
                "action": "patcher_auto",
                "agent": "patcher",
                "status": "completed" if patch_res.get("success") else "failed",
                "output": "patcher_executed",
                "agent_result": {k: patch_res[k] for k in list(patch_res)[:5]},
            })
            if patch_res.get("artifact_path"):
                artifacts.setdefault("patcher_artifact", str(patch_res["artifact_path"]))
            self._persist_patched_code(code_text, patch_res, artifacts)
            self._write_final_payload(task, artifacts)
        except Exception as e:  # pragma: no cover
            executed.append({
                "step": next_idx,
                "action": "patcher_auto",
                "agent": "patcher",
                "status": "failed",
                "output": f"patcher error: {e}",
            })

    def _persist_patched_code(self, code_text: str, patch_res: Dict[str, Any], artifacts: PipelineArtifacts) -> None:
        try:
            patched_code = patch_res.get('patched_code') or code_text
            from pathlib import Path as _P
            gen_path = artifacts.get('codegen_artifact')
            if not gen_path:
                return
            gp = _P(gen_path)
            if gp.exists():
                original_text = None
                try:
                    with gp.open('r', encoding='utf-8') as _rf:
                        original_text = _rf.read()
                except Exception:
                    pass
                if original_text != patched_code:
                    with gp.open('w', encoding='utf-8') as _wf:
                        _wf.write(patched_code)
            else:
                with gp.open('w', encoding='utf-8') as _wf:
                    _wf.write(patched_code)
        except Exception:  # pragma: no cover
            pass

    def _write_final_payload(self, task: Task, artifacts: PipelineArtifacts) -> Dict[str, Any]:
        from pathlib import Path as _P
        import json as _json
        from datetime import datetime as _datetime
        
        # Use the task directory already created in _execute_file_plan
        task_dir = _P(artifacts.get('task_dir', ''))
        if not task_dir.exists():
            # Fallback: recreate the task directory structure if needed
            desc = task.get('description', '') or 'task'
            words = [w for w in desc.lower().split() if w.isalnum()][:6]
            slug_base = '-'.join(words) if words else 'task'
            import hashlib
            h = hashlib.sha1(desc.encode()).hexdigest()[:8]
            task_slug = f"{slug_base}_{h}"[:56]
            task_dir = _P.cwd() / 'output' / task_slug
            task_dir.mkdir(parents=True, exist_ok=True)
        
        final_dir = task_dir / 'final'
        final_dir.mkdir(exist_ok=True)
        
        # Convert all paths to relative paths from the task directory
        relative_artifacts = {}
        for k, v in artifacts.items():
            if isinstance(v, str) and ('output' in v or 'generated' in k):
                try:
                    full_path = _P(v)
                    if full_path.is_absolute() and task_dir in full_path.parents:
                        relative_artifacts[k] = str(full_path.relative_to(task_dir))
                    else:
                        relative_artifacts[k] = v
                except ValueError:
                    relative_artifacts[k] = v
            else:
                relative_artifacts[k] = v
        
        payload_data = {
            'task_id': task.get('task_id'),
            'description': task.get('description'),
            'final_result': {
                'status': 'completed',
                'timestamp': _datetime.now().isoformat(),
                'task_directory': str(task_dir.name),
                'artifacts': relative_artifacts
            }
        }
        
        payload_file = final_dir / 'task_payload.json'
        try:
            payload_file.write_text(_json.dumps(payload_data, indent=2), encoding='utf-8')
            return {'payload_file': str(payload_file), 'task_directory': str(task_dir)}
        except Exception:  # pragma: no cover
            return {'error': 'payload_write_failed'}

    def _should_build_exe(self, desc: str) -> bool:
        import os
        if os.getenv('ORBITSUITE_FORCE_EXE', '').lower() in ('1','true','yes','on'):
            return True
        lowered = desc.lower()
        return any(k in lowered for k in (
            ' build an executable', 'executable', ' .exe', ' build exe', 'make an exe', 'windows binary', 'create exe'
        )) or any(k in lowered.split() for k in ('exe', 'executable'))

    def _build_executable(self, stem: str, code_text: str, artifacts: PipelineArtifacts, final_dir: Any) -> Optional[str]:
        try:
            from pathlib import Path
            import sys, os, subprocess, shutil
            # Determine input script path
            script_path = None
            gen_path = artifacts.get('codegen_artifact')
            if gen_path:
                script_path = Path(gen_path)
            if not script_path or not script_path.exists():
                script_path = final_dir / f"{stem}_app.py"
                with open(script_path, 'w', encoding='utf-8') as sf:
                    sf.write(code_text)
            build_root = final_dir / f"_build_{stem}"
            dist_path = build_root / 'dist'
            work_path = build_root / 'work'
            spec_path = build_root / 'spec'
            for p in (dist_path, work_path, spec_path):
                p.mkdir(parents=True, exist_ok=True)
            build_log = build_root / 'build.log'
            args = ['--onefile', '--noconfirm', '--clean', '--distpath', str(dist_path), '--workpath', str(work_path), '--specpath', str(spec_path)]
            if 'tkinter' in code_text:
                args.append('--windowed')
            args.append(str(script_path))
            # Persist planned build info early
            artifacts.setdefault('executable_build_args', ' '.join(args))  # type: ignore[arg-type]
            artifacts.setdefault('executable_build_root', str(build_root))  # type: ignore[arg-type]
            try:
                from PyInstaller.__main__ import run as pyinstaller_run  # type: ignore
            except Exception:
                pyinstaller_run = None  # type: ignore
            frozen_env = getattr(sys, 'frozen', False)
            external_python = os.getenv('ORBITSUITE_BUILD_PYTHON')
            used_external = False
            exit_status: int | None = None
            if frozen_env and external_python and os.path.exists(external_python):
                used_external = True
                cmd = [external_python, '-m', 'PyInstaller', *args]
                try:
                    if is_verbose():
                        print(f"[Orchestrator][exe] Using external Python for build: {' '.join(cmd)}")
                    with open(build_log, 'w', encoding='utf-8') as lf:
                        lf.write('# OrbitSuite external build log\n')
                        lf.flush()
                        proc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, text=True)
                        exit_status = proc.returncode
                except Exception as ext_e:  # pragma: no cover
                    return f"External build error: {ext_e}"
            elif frozen_env and pyinstaller_run is None:
                return ('Skipped: running inside frozen executable without bundled PyInstaller. '
                        'Set ORBITSUITE_BUILD_PYTHON to an external python with PyInstaller installed.')
            elif pyinstaller_run is None:
                return 'PyInstaller not installed in environment; cannot build executable.'
            else:
                try:
                    exit_codes: List[int] = []
                    orig_exit = sys.exit
                    def _fake_exit(code: int = 0):
                        try:
                            exit_codes.append(int(code))
                        except Exception:
                            exit_codes.append(1)
                    sys.exit = _fake_exit  # type: ignore
                    try:
                        with open(build_log, 'w', encoding='utf-8') as lf:
                            lf.write('# OrbitSuite internal build log (PyInstaller API)\n')
                            if is_verbose():
                                lf.write(f"# Args: {' '.join(args)}\n")
                        pyinstaller_run(args)  # type: ignore[misc]
                    finally:
                        sys.exit = orig_exit  # type: ignore
                    if exit_codes:
                        exit_status = exit_codes[0]
                except Exception as pe:  # pragma: no cover
                    return f"PyInstaller run error: {pe}"
            if exit_status not in (None, 0):
                note = f"PyInstaller exit status {exit_status}"
            else:
                note = None
            exe_candidates = list(dist_path.glob('*.exe')) if dist_path.exists() else []
            if exe_candidates:
                built_exe = exe_candidates[0]
                target_exe = final_dir / f"{stem}.exe"
                try:
                    shutil.copy2(built_exe, target_exe)
                    artifacts.setdefault('executable_artifact', str(target_exe))
                    artifacts.setdefault('executable_build_log', str(build_log))  # type: ignore[arg-type]
                    note = f"Executable built: {target_exe.name}{' (external python)' if used_external else ''}"
                except Exception as copy_e:  # pragma: no cover
                    note = f"Copy failed: {copy_e}"
            else:
                if not note:
                    guidance: List[str] = []
                    if frozen_env:
                        guidance.append('running inside frozen build')
                    if not external_python:
                        guidance.append('no ORBITSUITE_BUILD_PYTHON specified')
                    note = 'No executable produced (' + ', '.join(guidance) + ').'
                note += '\nSuggestion: Install PyInstaller in a regular Python env and set ORBITSUITE_BUILD_PYTHON="C:/Path/Python.exe"'
            # Also store note text so downstream JSON can embed it
            if note:
                artifacts.setdefault('executable_note_text', note)  # type: ignore[arg-type]
                artifacts.setdefault('executable_build_log', str(build_log))  # ensure path recorded
            return note
        except Exception as build_e:  # pragma: no cover
            return f"Exe build error: {build_e}"

    def _generate_traceability(self, task: Task, artifacts: PipelineArtifacts) -> None:
        try:
            from pathlib import Path as _P
            import json as _json, os
            
            # Use task-specific directory instead of global final directory
            task_dir = _P(artifacts.get('task_dir', ''))
            if not task_dir.exists():
                # Fallback: recreate the task directory structure if needed
                desc = task.get('description', '') or 'task'
                words = [w for w in desc.lower().split() if w.isalnum()][:6]
                slug_base = '-'.join(words) if words else 'task'
                import hashlib
                h = hashlib.sha1(desc.encode()).hexdigest()[:8]
                task_slug = f"{slug_base}_{h}"[:56]
                task_dir = _P.cwd() / 'output' / task_slug
                
            trace_dir = task_dir / 'final'
            trace_dir.mkdir(parents=True, exist_ok=True)
            requirements: List[Dict[str, str]] = []
            spec_path = artifacts.get('spec_path')
            if spec_path and _P(spec_path).exists():
                try:
                    spec_json_raw: Any = _json.loads(_P(spec_path).read_text(encoding='utf-8'))
                    if isinstance(spec_json_raw, dict):
                        spec_json = cast(Dict[str, Any], spec_json_raw)
                        spec_section_val = spec_json.get('spec')
                        if isinstance(spec_section_val, dict):
                            spec_section = cast(Dict[str, Any], spec_section_val)
                            reqs_val_any = spec_section.get('requirements')
                            if isinstance(reqs_val_any, list):
                                for r_any in reqs_val_any: # type: ignore
                                    r_any = cast(Any, r_any)
                                    r_dict = cast(Dict[str, Any], r_any)
                                    rid_raw = cast(str, r_dict.get('requirement_id') or r_dict.get('id') or '')
                                    desc_raw = cast(str, r_dict.get('description') or r_dict.get('title') or '')
                                    requirements.append({'requirement_id': str(rid_raw), 'description': str(desc_raw)})
                except Exception:
                    pass
            if not requirements and task.get('description'):
                desc = str(task.get('description',''))
                requirements = [{'requirement_id': f'implicit_{i+1}', 'description': s.strip()} for i, s in enumerate(desc.split('.')) if s.strip()]
            trace_detail: Dict[str, List[str]] = {}
            for gf in artifacts.get('generated_files', []):
                fname_lc = os.path.basename(gf).lower()
                hits: List[str] = []
                for req in requirements:
                    txt = req.get('description','').lower()
                    tokens = {w for w in txt.split() if len(w) > 4}
                    if any(t in fname_lc for t in tokens):
                        hits.append(req.get('requirement_id') or 'unknown')
                if hits:
                    trace_detail[gf] = sorted(set(hits))
            simple_map: Dict[str, List[str]] = {
                gf: [w for w in set(str(task.get('description','')).lower().split()) if w in os.path.basename(gf).lower() and len(w) > 3]
                for gf in artifacts.get('generated_files', [])
            }
            combined: Dict[str, Any] = {
                'detailed_requirement_map': trace_detail,
                'keyword_map': simple_map,
                'generated_files': artifacts.get('generated_files', []),
            }
            trace_path = trace_dir / 'traceability.json'
            trace_path.write_text(_json.dumps(combined, indent=2), encoding='utf-8')
            artifacts.setdefault('traceability_path', str(trace_path))
        except Exception:  # pragma: no cover
            pass

    def _emit_progress(self, event: str, record: StepExecution) -> None:
        try:
            if getattr(self, '_progress_cb', None):  # type: ignore[attr-defined]
                getattr(self, '_progress_cb')({  # type: ignore[attr-defined]
                    'event': event,
                    'step': record.get('step'),
                    'action': record.get('action'),
                    'status': record.get('status'),
                })
        except Exception:  # pragma: no cover
            pass

    def _assess_complexity(self, task: Task) -> str:
        desc = task.get("description", "")
        if len(desc) > 500:
            return "high"
        if len(desc) > 100:
            return "medium"
        return "low"

    # --- Registration / Delegation ---
    def register_agent(self, name: str, agent: BaseAgent) -> None:
        self.agents[name] = agent
        print(f"[Orchestrator] Registered agent: {name}")

    def get_available_agents(self) -> List[str]:
        return list(self.agents.keys())

    def delegate_to_agent(self, agent_name: str, task_data: Any) -> Dict[str, Any]:
        if agent_name not in self.agents:
            return {"success": False, "error": f"Agent '{agent_name}' not found", "available_agents": self.get_available_agents()}
        try:
            out = self.agents[agent_name].dispatch(task_data)
            return {"success": True, "agent": agent_name, "result": out}
        except Exception as e:  # pragma: no cover
            return {"success": False, "agent": agent_name, "error": str(e)}

    # --- Workflows & Dependencies ---
    def create_workflow(self, tasks: List[Task]) -> Dict[str, Any]:
        workflow: Dict[str, Any] = {
            "workflow_id": f"workflow_{len(self.task_queue)}",
            "tasks": tasks,
            "total_tasks": len(tasks),
            "status": "created",
            "dependencies": self._analyze_dependencies(tasks),
        }
        self.task_queue.append(workflow)
        return workflow

    def _analyze_dependencies(self, tasks: List[Task]) -> List[Dependency]:
        deps: List[Dependency] = []
        for i, t in enumerate(tasks):
            for j, other in enumerate(tasks):
                if i != j and self._has_dependency(t, other):
                    deps.append({"task_index": i, "depends_on": j, "reason": "Output dependency detected"})
        return deps

    def _has_dependency(self, task1: Task, task2: Task) -> bool:
        d1 = task1.get("description", "").lower()
        d2 = task2.get("description", "").lower()
        return ("result" in d1 or "output" in d1) and ("generate" in d2 or "create" in d2)

    def _convert_to_task(self, data: Dict[str, Any]) -> Task:
        return Task(
            task_id=data.get("task_id", ""),
            type=data.get("type", ""),
            description=data.get("description", ""),
            agent_target=data.get("agent_target", ""),
            input=data.get("input"),
        )