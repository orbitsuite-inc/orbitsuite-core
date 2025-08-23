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

from src.base_agent import BaseAgent


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
        # Promote generic tasks to a full pipeline: engineer -> codegen -> tester -> patcher
        is_generic = agent_target == "unassigned" or task.get("type", "").lower() in ("general", "")
        if is_generic:
            agent_target = "codegen"
        engineer_result: Dict[str, Any] | None = None
        pre_steps: List[Dict[str, Any]] = []
        if agent_target == "codegen" and not any(k in description.lower() for k in ("spec", "architecture", "design")):
            engineer_agent = self.agents.get("engineer")
            if engineer_agent:
                try:
                    eng_payload = {"command": "analyze", "description": description, "project_type": "web_application"}
                    engineer_result = engineer_agent.dispatch(eng_payload)  # type: ignore[arg-type]
                    pre_steps.append({
                        "step": 0,
                        "action": "engineer_analysis",
                        "agent": "engineer",
                        "status": "completed" if engineer_result and engineer_result.get("success") else "failed",
                        "output": engineer_result.get("artifact_dir") if engineer_result else "analysis_skipped",
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
        """Execute the plan, dispatching the primary agent then optional tester/patcher chain."""
        executed: List[StepExecution] = []
        final_output: Optional[Dict[str, Any]] = None
        failures = 0
        pipeline_artifacts: PipelineArtifacts = {}
        for step in plan.get("steps", []):
            s: StepExecution = {
                "step": step.get("step", -1),
                "action": step.get("action", "unknown"),
                "status": "completed",  # updated below on failure/skip
                "output": f"Step {step.get('step')} executed successfully",
            }
            if s["action"] == "execute_agent":
                agent_name = step.get("agent", "unassigned")
                s["agent"] = agent_name
                if agent_name == "unassigned" or agent_name not in self.agents:
                    s["status"] = "skipped"
                    s["output"] = "No agent assigned (Core has no fallback)"
                else:
                    payload: Dict[str, Any] = {
                        "prompt": task.get("description", ""),
                        "description": task.get("description", ""),
                        "task_id": task.get("task_id", ""),
                    }
                    if engineer_result and engineer_result.get("success"):
                        payload["spec"] = engineer_result.get("core_analysis", {})
                    try:
                        out = self.agents[agent_name].dispatch(payload)
                        final_output = out if isinstance(out, dict) else {"raw": out}  # type: ignore[assignment]
                        s["output"] = "agent_executed"
                        s["agent_result"] = {k: final_output[k] for k in list(final_output)[:5]}
                        if final_output and final_output.get("artifact_path"):
                            pipeline_artifacts.setdefault("codegen_artifact", str(final_output["artifact_path"]))
                    except Exception as e:  # pragma: no cover
                        failures += 1
                        s["status"] = "failed"
                        s["output"] = f"agent error: {e}"
            executed.append(s)

        # Automatic tester + patcher chaining if code produced
        if final_output and "code" in final_output:
            code_text = str(final_output.get("code", ""))
            next_idx = (max([e.get("step", 0) for e in executed]) + 1) if executed else 1
            tester = self.agents.get("tester")
            if tester and code_text:
                try:
                    test_res = tester.dispatch({"type": "syntax_check", "target": code_text})
                    executed.append({
                        "step": next_idx,
                        "action": "tester_validation",
                        "agent": "tester",
                        "status": "completed" if test_res.get("success") else "failed",
                        "output": "tester_executed",
                        "agent_result": {k: test_res[k] for k in list(test_res)[:5]},
                    })
                    if test_res.get("artifact_path"):
                        pipeline_artifacts.setdefault("tester_artifact", str(test_res["artifact_path"]))
                except Exception as e:  # pragma: no cover
                    executed.append({
                        "step": next_idx,
                        "action": "tester_validation",
                        "agent": "tester",
                        "status": "failed",
                        "output": f"tester error: {e}",
                    })
                next_idx += 1
            patcher = self.agents.get("patcher")
            if patcher and code_text:
                try:
                    patch_res = patcher.dispatch({"type": "auto", "code": code_text, "issues": []})
                    executed.append({
                        "step": next_idx,
                        "action": "patcher_auto",
                        "agent": "patcher",
                        "status": "completed" if patch_res.get("success") else "failed",
                        "output": "patcher_executed",
                        "agent_result": {k: patch_res[k] for k in list(patch_res)[:5]},
                    })
                    if patch_res.get("artifact_path"):
                        pipeline_artifacts.setdefault("patcher_artifact", str(patch_res["artifact_path"]))
                    # Aggregate final output artifact (code + patch info) to output/final directory
                    try:
                        from pathlib import Path
                        import json, time, hashlib, shutil
                        base_dir = Path.cwd()
                        if getattr(__import__('sys'), 'frozen', False):  # type: ignore[attr-defined]
                            # Mirror EngineerCore strategy (write alongside dist if in dist)
                            if base_dir.name.lower() == 'dist' and base_dir.parent.exists():
                                base_dir = base_dir.parent
                        final_dir = base_dir / 'output' / 'final'
                        final_dir.mkdir(parents=True, exist_ok=True)
                        # Derive name from task description or fallback to timestamp hash
                        desc = task.get('description', '') or 'task'
                        stem = '_'.join(desc.lower().split())[:40] or f"task_{int(time.time())}"
                        # Ensure uniqueness with short hash
                        h = hashlib.sha1(desc.encode()).hexdigest()[:8]
                        stem = f"{stem}_{h}"
                        final_payload: Dict[str, Any] = {
                            'task_id': task.get('task_id'),
                            'description': task.get('description'),
                            'code': code_text,
                            'patched_code': patch_res.get('patched_code', code_text),
                            'fixes_applied': patch_res.get('fixes_applied', []),
                            'artifacts': dict(pipeline_artifacts),
                        }
                        out_path = final_dir / f"{stem}.json"
                        with open(out_path, 'w', encoding='utf-8') as f:
                            json.dump(final_payload, f, indent=2)
                        pipeline_artifacts.setdefault('final_output', str(out_path))

                        # Optional executable build: detect intent keywords
                        want_exe = any(k in desc.lower() for k in (
                            ' build an executable', 'executable', ' .exe', ' build exe', 'make an exe', 'windows binary', 'create exe'
                        )) or any(k in desc.lower().split() for k in ('exe', 'executable'))
                        if want_exe:
                            exe_note: str | None = None
                            try:
                                # Only attempt if PyInstaller available (not typically inside frozen core executable)
                                try:
                                    from PyInstaller.__main__ import run as pyinstaller_run  # type: ignore
                                except Exception:
                                    pyinstaller_run = None  # type: ignore
                                script_path = None
                                # Attempt to locate generated code artifact path recorded earlier
                                gen_path = pipeline_artifacts.get('codegen_artifact')
                                if gen_path:
                                    script_path = Path(gen_path)
                                # Fallback: write code to a temp file if not found
                                if not script_path or not script_path.exists():
                                    script_path = final_dir / f"{stem}_app.py"
                                    with open(script_path, 'w', encoding='utf-8') as sf:
                                        sf.write(code_text)
                                if pyinstaller_run is None:
                                    exe_note = 'PyInstaller not bundled; skip build (install dev deps to enable)'
                                else:
                                    # Prepare isolated build dirs under output/final/_build_<stem>
                                    build_root = final_dir / f"_build_{stem}"
                                    dist_path = build_root / 'dist'
                                    work_path = build_root / 'work'
                                    spec_path = build_root / 'spec'
                                    for p in (dist_path, work_path, spec_path):
                                        p.mkdir(parents=True, exist_ok=True)
                                    args = [
                                        '--onefile',
                                        '--noconfirm',
                                        '--clean',
                                        '--distpath', str(dist_path),
                                        '--workpath', str(work_path),
                                        '--specpath', str(spec_path),
                                    ]
                                    # GUI heuristic: if tkinter present, use windowed
                                    if 'tkinter' in code_text:
                                        args.append('--windowed')
                                    args.append(str(script_path))
                                    try:
                                        import sys
                                        exit_codes: list[int] = []
                                        orig_exit = sys.exit
                                        def _fake_exit(code: int = 0):
                                            try:
                                                exit_codes.append(int(code))
                                            except Exception:
                                                exit_codes.append(1)
                                        sys.exit = _fake_exit  # type: ignore
                                        try:
                                            pyinstaller_run(args)  # type: ignore[misc]
                                        finally:
                                            sys.exit = orig_exit  # type: ignore
                                        if exit_codes and exit_codes[0] != 0:
                                            exe_note = f"PyInstaller non-zero exit code {exit_codes[0]}"
                                    except Exception as pe:  # pragma: no cover
                                        exe_note = f"PyInstaller run error: {pe}"  # noqa: E501
                                    # Find built exe
                                    exe_candidates = list(dist_path.glob('*.exe'))
                                    if exe_candidates:
                                        built_exe = exe_candidates[0]
                                        target_exe = final_dir / f"{stem}.exe"
                                        try:
                                            shutil.copy2(built_exe, target_exe)
                                            pipeline_artifacts.setdefault('executable_artifact', str(target_exe))
                                            exe_note = f"Executable built: {target_exe.name}"
                                        except Exception as copy_e:  # pragma: no cover
                                            exe_note = f"Copy failed: {copy_e}"  # noqa: E501
                                    else:
                                        exe_note = 'PyInstaller run completed but no .exe produced'
                            except Exception as build_e:  # pragma: no cover
                                exe_note = f"Exe build error: {build_e}"  # noqa: E501
                            if exe_note:
                                # Append a small note file for transparency
                                try:
                                    note_file = final_dir / f"{stem}_exe_build.txt"
                                    with open(note_file, 'w', encoding='utf-8') as nf:
                                        nf.write(exe_note)
                                    pipeline_artifacts.setdefault('executable_note', str(note_file))
                                except Exception:
                                    pass
                    except Exception:  # pragma: no cover
                        pass
                except Exception as e:  # pragma: no cover
                    executed.append({
                        "step": next_idx,
                        "action": "patcher_auto",
                        "agent": "patcher",
                        "status": "failed",
                        "output": f"patcher error: {e}",
                    })

        return cast(PlanExecutionResult, {
            "plan_executed": True,
            "steps_completed": len([x for x in executed if x.get("status") == "completed"]),
            "steps_failed": failures,
            "execution_details": executed,
            "final_status": "success" if failures == 0 else "partial",
            "agent_output": final_output or {},
            "pipeline_artifacts": pipeline_artifacts,
        })

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