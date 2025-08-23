#!/usr/bin/env python3
# core/src/demo.py
"""
Demo script showing how to use OrbitSuite Core minimal functionality.
This demonstrates the basic usage of all core agents and the supervisor.
"""

import sys
import os

# Add core/src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supervisor import Supervisor
from utils import SimpleLogger
from typing import TypedDict, Any, cast


class ProcessResult(TypedDict, total=False):
    success: bool
    processing_time: float
    result: dict[str, Any]
    task_id: str
    error: str


def run_demo():
    """Run a comprehensive demo of OrbitSuite Core functionality."""
    
    print("=" * 60)
    print("OrbitSuite Core - Minimal Functionality Demo")
    print("=" * 60)
    
    # Initialize logger and supervisor
    logger = SimpleLogger("CoreDemo")
    supervisor = Supervisor()
    
    logger.info("Supervisor initialized successfully")
    
    # Demo 1: Health Check
    print("\n1. Health Check")
    print("-" * 20)
    health = supervisor.health_check()
    print(f"Overall Status: {health['overall_status']}")
    for agent, status in health['agent_checks'].items():
        print(f"  {agent}: {status['status']}")
    
    # Demo 2: Natural Language Processing
    print("\n2. Natural Language Task Processing")
    print("-" * 40)
    
    test_requests = [
        "Generate a Python function to calculate fibonacci numbers",
        "Test the code for any syntax errors", 
        "Design a web application architecture",
        "Save this result to memory as 'demo_result'",
        "Fix any issues in the code"
    ]
    
    for i, request in enumerate(test_requests, 1):
        print(f"\nRequest {i}: {request}")
        result = cast(ProcessResult, supervisor.process_request(request))

        if result.get("success", False):
            processing_time = float(result.get("processing_time", 0.0))
            print(f"✅ Processed successfully (took {processing_time:.2f}s)")
            # Show abbreviated result
            if "result" in result and isinstance(result.get("result"), dict):
                inner: dict[str, Any] = result["result"]  # safe: checked above
                if "code" in inner:
                    print("📝 Generated code snippet")
                elif "design" in inner:
                    print("🏗️ Created system design")
                elif "success" in inner:
                    action = str(inner.get("action", "completed"))
                    print(f"🔧 Agent operation: {action}")
        else:
            print(f"❌ Failed: {result.get('error') or 'Unknown error'}")
    
    # Demo 3: Direct Agent Usage
    print("\n3. Direct Agent Usage Examples")
    print("-" * 35)
    
    # Test memory agent directly
    print("\nMemory Agent:")
    memory_agent = supervisor.agents["memory"]
    
    # Save something
    save_result = memory_agent.dispatch({
        "action": "save",
        "key": "demo_key",
        "value": "This is a demo value"
    })
    print(f"  Save: {save_result['success']}")
    
    # Recall it
    recall_result = memory_agent.dispatch({
        "action": "recall", 
        "key": "demo_key"
    })
    print(f"  Recall: {recall_result['value'] if recall_result['success'] else 'Failed'}")
    
    # Test code generation
    print("\nCodegen Agent:")
    codegen_agent = supervisor.agents["codegen"]
    code_result = codegen_agent.dispatch({
        "prompt": "Create a simple hello world function",
        "language": "python"
    })
    print(f"  Generated: {code_result['success']}")
    if code_result["success"]:
        print(f"  Code length: {len(code_result['code'])} characters")
    
    # Test code testing
    print("\nTester Agent:")
    tester_agent = supervisor.agents["tester"]
    test_result = tester_agent.dispatch({
        "type": "syntax_check",
        "target": "def hello():\n    print('Hello World')\n    return True"
    })
    print(f"  Syntax check: {'✅ Valid' if test_result['success'] else '❌ Invalid'}")
    
    # Demo 4: Workflow Execution
    print("\n4. Workflow Execution")
    print("-" * 25)
    
    workflow_tasks = [
        {
            "task_id": "step1",
            "type": "codegen",
            "description": "Create a simple calculator function",
            "agent_target": "codegen"
        },
        {
            "task_id": "step2", 
            "type": "testing",
            "description": "Test the calculator function",
            "agent_target": "tester"
        }
    ]
    
    workflow_result = supervisor.execute_workflow(workflow_tasks)
    print(f"Workflow executed: {workflow_result['success']}")
    print(f"Tasks completed: {workflow_result.get('successful_tasks', 0)}/{workflow_result.get('total_tasks', 0)}")
    
    # Demo 5: Supervisor Status
    print("\n5. Supervisor Status")
    print("-" * 22)
    
    status = supervisor.get_status()
    print(f"Status: {status['status']}")
    print(f"Version: {status['version']}")
    print(f"Available Agents: {', '.join(status['agents'])}")
    print(f"Total Tasks Processed: {status['total_tasks_processed']}")
    
    # Demo 6: Agent Information
    print("\n6. Agent Information")
    print("-" * 22)
    
    agent_info = supervisor.get_agent_info()
    for name, info in agent_info.items():
        print(f"  {name}: v{info['version']}")
    
    print("\n" + "=" * 60)
    print("Demo completed successfully!")
    print("OrbitSuite Core minimal functionality is working.")
    print("=" * 60)


def main():
    """Placeholder main function for demo.py."""
    print("Demo main function executed.")


if __name__ == "__main__":
    try:
        run_demo()
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)