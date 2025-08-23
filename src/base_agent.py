# core/src/base_agent.py
# Minimal BaseAgent for OrbitSuite core functionality
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import abc
import time
from typing import Any, Dict
try:
    from .utils import is_verbose
except Exception:  # fallback for script execution
    from utils import is_verbose  # type: ignore


class BaseAgent(abc.ABC):
    """
    Minimal abstract agent class for OrbitSuite's core functionality.
    All agents inherit and implement their own run() method.
    """
    
    def __init__(self, name: str = "agent"):
        self.name = name
        self.context: Dict[str, Any] = {}
        self.result: Any = None

    def dispatch(self, input_data: Any) -> Any:
        """
        Entrypoint for agent execution. Wraps run() method.
        """
        start = time.time()
        snippet = str(input_data)
        if len(snippet) > 120:
            snippet = snippet[:117] + "..."
        print(f"[{self.name}] Processing: {snippet}")
        self.result = self.run(input_data)
        dur = time.time() - start
        if is_verbose():
            out_kind = type(self.result).__name__
            print(f"[{self.name}] Completed in {dur:.2f}s (type={out_kind})")
        else:
            print(f"[{self.name}] Completed.")
        return self.result

    @abc.abstractmethod
    def run(self, input_data: Any) -> Any:
        """
        Each subclass must implement this method to define agent behavior.
        """
        raise NotImplementedError(f"Agent {self.name} must implement run() method.")