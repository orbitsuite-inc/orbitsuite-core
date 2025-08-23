#!/usr/bin/env python3
# core/src/test_core.py
"""
Basic test script for OrbitSuite Core minimal functionality.
Tests individual agents and supervisor functionality.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from typing import Any, Callable, Dict, List, Tuple
import pytest

from src.supervisor import Supervisor
from src.base_agent import BaseAgent
from src.task_linguist import TaskLinguistAgent
from src.codegen_agent import CodegenAgent
from src.engineer_agent import EngineerAgent
from src.memory_agent import MemoryAgent
from src.tester_agent import TesterAgentClass
from src.patcher_agent import PatcherAgent
from src.orchestrator_agent import OrchestratorAgent

# Replace BaseAgent instantiation with ConcreteAgent
class ConcreteAgent(BaseAgent):
    def run(self, input_data: Any) -> Dict[str, Any]:
        return {"success": True, "data": input_data}


def test_base_agent():
    """Test that BaseAgent is properly abstract."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class BaseAgent"):
        BaseAgent()  # type: ignore # Attempting to instantiate should raise TypeError


def test_task_linguist():
    """Test TaskLinguistAgent functionality."""
    agent = TaskLinguistAgent()

    # Test valid input
    result = agent.run("Generate a Python function")
    assert result.get("success"), f"TaskLinguist failed: {result}"
    assert "task" in result, "TaskLinguist didn't return task structure"

    task = result["task"]
    assert "task_id" in task and "type" in task, "TaskLinguist task missing required fields"

    # Test invalid input
    result = agent.run("")
    assert not result.get("success"), "TaskLinguist should fail on empty input"


def test_codegen_agent():
    """Test CodegenAgent functionality."""
    agent = CodegenAgent()

    # Test function generation
    result = agent.run({"prompt": "create a function", "language": "python"})
    assert result.get("success"), f"Codegen failed: {result}"
    assert "code" in result, "Codegen didn't return code"

    # Test that code contains function definition
    code = result["code"]
    assert "def " in code, "Generated code doesn't contain function definition"


def test_memory_agent():
    """Test MemoryAgent functionality."""
    agent = MemoryAgent()

    # Test save operation
    result = agent.run({"action": "save", "key": "test_key", "value": "test_value"})
    assert result.get("success"), f"Memory save failed: {result}"

    # Test recall operation
    result = agent.run({"action": "recall", "key": "test_key"})
    assert result.get("success"), f"Memory recall failed: {result}"
    assert result.get("value") == "test_value", "Memory recall returned wrong value"

    # Test list operation
    result = agent.run({"action": "list"})
    assert result.get("success"), f"Memory list failed: {result}"

    # Test clear operation
    result = agent.run({"action": "clear", "key": "test_key"})
    assert result.get("success"), f"Memory clear failed: {result}"


def test_tester_agent():
    """Test TesterAgent functionality."""
    agent = TesterAgentClass()

    # Test syntax checking with valid code
    valid_code = "def hello():\n    return 'world'"
    result = agent.run({"type": "syntax_check", "target": valid_code})
    assert result.get("success"), f"Tester failed on valid syntax: {result}"

    # Test syntax checking with invalid code
    invalid_code = "def hello(\n    return 'world'"
    result = agent.run({"type": "syntax_check", "target": invalid_code})
    assert not result.get("success"), "Tester should fail on invalid syntax"


def test_patcher_agent():
    """Test PatcherAgent functionality."""
    agent = PatcherAgent()

    # Test auto patching
    code_with_issues = "def hello()\n    print 'hello'"
    result = agent.run({"code": code_with_issues, "type": "auto"})
    assert result.get("success"), f"Patcher failed: {result}"
    assert "patched_code" in result, "Patcher didn't return patched code"


def test_engineer_agent():
    """Test EngineerAgent functionality."""
    agent = EngineerAgent()

    # Test system design
    result = agent.run("Design a web application with database")
    assert result.get("success"), f"Engineer failed: {result}"
    assert "design" in result, "Engineer didn't return design"

    design = result["design"]
    required_fields = ["architecture_pattern", "components", "technology_stack"]
    for field in required_fields:
        assert field in design, f"Engineer design missing {field}"


def test_orchestrator_agent():
    """Test OrchestratorAgent functionality."""
    agent = OrchestratorAgent()

    # Test single task execution
    task = {"description": "test task", "type": "general"}
    result = agent.run(task)
    assert result.get("success"), f"Orchestrator failed: {result}"

    # Test batch execution
    tasks = [
        {"description": "task 1", "type": "codegen"},
        {"description": "task 2", "type": "testing"},
    ]
    result = agent.run({"tasks": tasks})
    assert result.get("success"), f"Orchestrator batch failed: {result}"


def test_supervisor():
    """Test Supervisor functionality."""
    supervisor = Supervisor(include_llm=False)  # Exclude LLMAgent for this test

    # Test initialization
    assert len(supervisor.agents) == 7, f"Supervisor should have 7 agents, has {len(supervisor.agents)}"

    # Test health check
    health = supervisor.health_check()
    assert health["overall_status"] == "healthy", f"Supervisor health check failed: {health}"

    # Test request processing
    result = supervisor.process_request("test request")
    assert result.get("success"), f"Supervisor request processing failed: {result}"

    # Test status
    status = supervisor.get_status()
    assert "agents" in status, "Supervisor status missing agents list"


def run_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("OrbitSuite Core - Test Suite")
    print("=" * 60)

    # Define the type of tests as a list of tuples (test_name, test_func)
    tests: List[Tuple[str, Callable[[], None]]] = [
        ("BaseAgent", test_base_agent),
        ("TaskLinguist", test_task_linguist),
        ("CodegenAgent", test_codegen_agent),
        ("MemoryAgent", test_memory_agent),
        ("TesterAgent", test_tester_agent),
        ("PatcherAgent", test_patcher_agent),
        ("EngineerAgent", test_engineer_agent),
        ("OrchestratorAgent", test_orchestrator_agent),
        ("Supervisor", test_supervisor),
    ]

    passed = 0
    failed = 0

    # Iterate over tests with proper type annotations
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"✅ {test_name}: Passed")
            passed += 1
        except AssertionError as e:
            print(f"❌ {test_name}: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {test_name}: Exception - {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! OrbitSuite Core is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        return False


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)