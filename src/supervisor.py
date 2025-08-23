# core/src/supervisor.py
# Minimal Supervisor for OrbitSuite core functionality
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import time
from typing import Dict, Any, List, Optional
from src.task_linguist import TaskLinguistAgent
from src.codegen_agent import CodegenAgent
from src.engineer_agent import EngineerAgent
from src.memory_agent import MemoryAgent
from src.tester_agent import TesterAgentClass
from src.patcher_agent import PatcherAgent
from src.orchestrator_agent import OrchestratorAgent


def _is_verbose() -> bool:
    v = os.getenv("ORBITSUITE_VERBOSE", "")
    return v.strip().lower() in ("1", "true", "yes", "on")


def _truncate(text: str, max_len: int = 160) -> str:
    return text if len(text) <= max_len else text[: max_len - 3] + "..."


# Simple file logger for verbose output
_LOG_FILE_PATH = os.path.join(os.path.dirname(__file__), "orbitsuite.log")


def _append_log(msg: str) -> None:
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        with open(_LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {msg}\n")
    except Exception:
        # best-effort logging only
        pass


def _vlog(msg: str) -> None:
    if _is_verbose():
        print(msg)
        _append_log(msg)


class Supervisor:
    """
    Minimal supervisor for coordinating OrbitSuite agents.
    Handles task routing, agent coordination, and basic workflow management.
    """
    
    def __init__(self, include_llm: bool = True):
        self.version = "minimal-1.0"
        self.agents: Dict[str, Any] = {}
        self.status = "initialized"
        self.task_history: List[Dict[str, Any]] = []

        # Initialize all agents
        self._initialize_agents(include_llm)
        _vlog(f"[Supervisor] Initialized with {len(self.agents)} agents")

    def _initialize_agents(self, include_llm: bool):
        """Initialize all core agents."""
        self.agents = {
            "task_linguist": TaskLinguistAgent(),
            "codegen": CodegenAgent(),
            "engineer": EngineerAgent(),
            "memory": MemoryAgent(),
            "tester": TesterAgentClass(),
            "patcher": PatcherAgent(),
            "orchestrator": OrchestratorAgent()
        }

    # Local LLM env variables are ignored entirely in Core (no notice needed)
        
        # Register agents with orchestrator
        orchestrator = self.agents["orchestrator"]
        for name, agent in self.agents.items():
            if name != "orchestrator":
                orchestrator.register_agent(name, agent)
    
    def process_request(self, request: Any) -> Dict[str, Any]:
        """
        Main entry point for processing requests.
        """
        start_time = time.time()
        if _is_verbose():
            preview = _truncate(str(request), 160)
            _vlog(f"[Supervisor] Received request: {preview}")
        
        try:
            # Core: no direct LLM routing / fallback; always parse via TaskLinguist
            # Parse the request using task linguist
            if isinstance(request, str):
                if _is_verbose():
                    _vlog("[Supervisor] Using TaskLinguist to parse request")
                parsed_task = self.agents["task_linguist"].dispatch(request)
                if not parsed_task.get("success", False):
                    return self._error_response("Failed to parse request", parsed_task)
                
                task = parsed_task["task"]
            elif isinstance(request, dict):
                # Explicitly treat as Dict[str, Any] for static analysis
                from typing import cast
                task = cast(Dict[str, Any], request)
            else:
                return self._error_response("Invalid request format")
            
            # Ensure precise type for downstream calls
            from typing import cast
            task_dict = cast(Dict[str, Any], task)
            # Route to appropriate agent
            if _is_verbose():
                t_type = str(task_dict.get('type', ''))
                t_target = str(task_dict.get('agent_target', 'orchestrator'))
                _vlog(f"[Supervisor] Routing task type={t_type} target={t_target}")
            result = self._route_task(task_dict)
            
            # Log the task
            self._log_task(task_dict, result, time.time() - start_time)
            
            return {
                "success": True,
                "task_id": str(task_dict.get("task_id", "unknown")),
                "processing_time": time.time() - start_time,
                "result": result
            }
            
        except Exception as e:
            return self._error_response(f"Processing error: {str(e)}")
    
    def _route_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Route task to the appropriate agent."""
        agent_target = task.get("agent_target", "orchestrator")

        if agent_target == "llm":
            return {"success": False, "error": "PRO_FEATURE", "detail": "Local LLM usage requires Pro/Enterprise."}
        # If unknown target or a concrete agent (codegen/tester/etc), wrap via orchestrator so pipeline features apply
        if agent_target not in self.agents or agent_target != "orchestrator":
            orchestrator = self.agents["orchestrator"]
            # Ensure agent_target preserved for orchestrator planning
            task.setdefault("agent_target", agent_target if agent_target in self.agents else "unassigned")
            return orchestrator.dispatch({"task": task})

        # Orchestrator path
        orchestrator = self.agents["orchestrator"]
        return orchestrator.dispatch(task)
    
    def _log_task(self, task: Dict[str, Any], result: Dict[str, Any], processing_time: float):
        """Log task execution."""
        log_entry: Dict[str, Any] = {
            "timestamp": time.time(),
            "task_id": task.get("task_id", "unknown"),
            "task_type": task.get("type", "unknown"),
            "agent_used": task.get("agent_target", "unknown"),
            "success": result.get("success", False),
            "processing_time": processing_time,
        }

        self.task_history.append(log_entry)

        # Keep only last 100 entries
        if len(self.task_history) > 100:
            self.task_history = self.task_history[-100:]
    
    def _error_response(self, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create standardized error response."""
        response: Dict[str, Any] = {
            "success": False,
            "error": message,
            "timestamp": time.time(),
        }
        if details is not None:
            response["details"] = details
        return response
    
    def get_status(self) -> Dict[str, Any]:
        """Get supervisor status and statistics."""
        return {
            "status": self.status,
            "version": self.version,
            "agents": list(self.agents.keys()),
            "total_tasks_processed": len(self.task_history),
            "recent_tasks": self.task_history[-5:] if self.task_history else [],
            "uptime": "running"
        }
    
    def get_agent_info(self, agent_name: Optional[str] = None) -> Dict[str, Any]:
        """Get information about agents."""
        if agent_name:
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                return {
                    "name": agent.name,
                    "version": getattr(agent, "version", "unknown"),
                    "description": getattr(agent, "description", "No description available")
                }
            else:
                return {"error": f"Agent '{agent_name}' not found"}
        else:
            # Return info for all agents
            agent_info: Dict[str, Any] = {}
            for name, agent in self.agents.items():
                agent_info[name] = {
                    "name": agent.name,
                    "version": getattr(agent, "version", "unknown"),
                    "description": getattr(agent, "description", "No description available")
                }
            return agent_info
    
    def execute_workflow(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute a workflow of multiple tasks."""
        orchestrator = self.agents["orchestrator"]
        return orchestrator.dispatch({"tasks": tasks})
    
    def health_check(self) -> Dict[str, Any]:
        """Perform a basic health check."""
        checks: Dict[str, Dict[str, Any]] = {}

        # Check each agent
        for name, agent in self.agents.items():
            try:
                # Simple test dispatch
                if name == "task_linguist":
                    agent.dispatch("test")
                elif name == "memory":
                    agent.dispatch({"action": "list"})
                # For other agents, just ensure callable without executing heavy work
                checks[name] = {"status": "healthy", "responsive": True}
            except Exception as e:
                checks[name] = {"status": "error", "error": str(e)}

        all_healthy = all(v.get("status") == "healthy" for v in checks.values())

        return {
            "overall_status": "healthy" if all_healthy else "degraded",
            "agent_checks": checks,
            "timestamp": time.time(),
        }
    
    def reset(self):
        """Reset supervisor state."""
        self.task_history = []
        self.status = "reset"
        print("[Supervisor] State reset completed")
    
    def shutdown(self):
        """Graceful shutdown."""
        self.status = "shutdown"
        print("[Supervisor] Shutting down...")