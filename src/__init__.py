# core/src/__init__.py
"""
OrbitSuite Core - Minimal agent framework for basic functionality.

This package provides the bare minimum agents and supervisor functionality
needed for the OrbitSuite framework to operate.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from .base_agent import BaseAgent
from .task_linguist import TaskLinguistAgent
from .codegen_agent import CodegenAgent
from .engineer_agent import EngineerAgent
from .memory_agent import MemoryAgent
from .tester_agent import TesterAgentClass
from .patcher_agent import PatcherAgent
from .orchestrator_agent import OrchestratorAgent
from .supervisor import Supervisor

# Optional import
try:
    from .llm_agent import LLMAgent  # optional
except ImportError:
    LLMAgent = None  # type: ignore

__version__ = "1.0.0-minimal"
__author__ = "OrbitSuite Core Team"

# Core agent classes
__all__ = [
    "BaseAgent",
    "TaskLinguistAgent", 
    "CodegenAgent",
    "EngineerAgent",
    "MemoryAgent",
    "TesterAgentClass",
    "PatcherAgent",
    "OrchestratorAgent",
    "Supervisor",
    "LLMAgent",
]

def create_supervisor() -> Supervisor:
    """
    Create and initialize a new supervisor with all core agents.
    
    Returns:
        Supervisor: Initialized supervisor instance
    """
    return Supervisor()

def get_version() -> str:
    """Get the version of OrbitSuite Core."""
    return __version__