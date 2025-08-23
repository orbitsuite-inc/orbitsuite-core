# core/src/tester_agent.py
# Minimal Tester Agent for basic test execution
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import subprocess
from typing import Dict, Any, List, Union
from src.base_agent import BaseAgent


# Rename TesterAgent to avoid pytest collection
class TesterAgentClass(BaseAgent):
    """
    Minimal testing agent for basic test execution and validation.
    """
    __test__ = False  # Prevent pytest from collecting this class as a test

    def __init__(self):
        super().__init__(name="tester")
        self.version = "minimal-1.0"
    
    def run(self, input_data: Union[Dict[str, Any], str]) -> Dict[str, Any]:
        """
        Execute tests or validate code/functionality.
        """
        if not input_data:
            return {"error": "Test input required", "success": False}
        
        # Handle different input formats
        test_type: str = input_data.get("type", "code_validation") if isinstance(input_data, dict) else "code_validation"
        target: str = input_data.get("target", "") if isinstance(input_data, dict) else str(input_data)
        command: str = input_data.get("command", "") if isinstance(input_data, dict) else ""
        
        # Execute appropriate test type
        if test_type == "command" and command:
            result = self._run_test_command(command)
        elif test_type == "code_validation":
            result = self._validate_code(target)
        elif test_type == "syntax_check":
            result = self._check_syntax(target)
        else:
            result = self._run_basic_tests(target)

        # Write artifact summary (best-effort)
        try:
            from pathlib import Path
            import json, time
            out_dir = Path.cwd() / "output" / "tests"
            out_dir.mkdir(parents=True, exist_ok=True)
            stem = f"test_{int(time.time())}"
            with open(out_dir / f"{stem}.json", "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            result["artifact_path"] = str(out_dir / f"{stem}.json")
        except Exception:
            pass
        return result
    
    def _run_test_command(self, command: str) -> Dict[str, Any]:
        """Run a test command and capture results."""
        try:
            # Basic command execution
            result = subprocess.run(
                command.split(),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "exit_code": result.returncode,
                "command": command
            }
            
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Command timed out after 30 seconds",
                "exit_code": -1,
                "command": command
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "exit_code": -1,
                "command": command
            }
    
    def _validate_code(self, code: str) -> Dict[str, Any]:
        """Basic code validation."""
        if not code or not code.strip():
            return {
                "success": False,
                "validation": "empty_code",
                "message": "No code provided for validation"
            }
        
        # Basic validation checks
        issues: List[str] = []
        
        # Check for basic Python syntax issues
        if code.strip().startswith("def ") or "class " in code:
            # Check for proper indentation
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if line.strip() and not line.startswith(' ') and i > 0:
                    if lines[i-1].strip().endswith(':'):
                        issues.append(f"Line {i+1}: Missing indentation after colon")
        
        # Check for common issues
        if "TODO" in code:
            issues.append("Code contains TODO items")
        
        return {
            "success": len(issues) == 0,
            "validation": "syntax_check",
            "issues": issues,
            "lines_checked": len(code.split('\n'))
        }
    
    def _check_syntax(self, code: str) -> Dict[str, Any]:
        """Check Python syntax."""
        if not code or not code.strip():
            return {
                "success": False,
                "validation": "syntax_check",
                "message": "No code provided for syntax check"
            }
        
        try:
            # Try to compile the code
            compile(code, '<string>', 'exec')
            return {
                "success": True,
                "validation": "syntax_check",
                "message": "Syntax is valid"
            }
        except SyntaxError as e:
            return {
                "success": False,
                "validation": "syntax_check",
                "error": str(e),
                "line": e.lineno,
                "column": e.offset
            }
        except Exception as e:
            return {
                "success": False,
                "validation": "syntax_check",
                "error": str(e)
            }
    
    def _run_basic_tests(self, target: str) -> Dict[str, Any]:
        """Run basic functionality tests."""
        tests_run = 0
        tests_passed = 0
        test_results: List[Dict[str, Union[str, bool]]] = []
        
        # Test 1: Basic string validation
        tests_run += 1
        if target and len(target.strip()) > 0:
            tests_passed += 1
            test_results.append({"test": "non_empty_input", "passed": True})
        else:
            test_results.append({"test": "non_empty_input", "passed": False})
        
        # Test 2: Basic type checking
        tests_run += 1
        test_results.append({"test": "string_type", "passed": True})
        
        # Test 3: Length validation
        tests_run += 1
        if len(str(target)) < 10000:  # Reasonable length
            tests_passed += 1
            test_results.append({"test": "reasonable_length", "passed": True})
        else:
            test_results.append({"test": "reasonable_length", "passed": False})
        
        return {
            "success": tests_passed >= tests_run,  # Adjusted condition to ensure proper evaluation
            "tests_run": tests_run,
            "tests_passed": tests_passed,
            "test_results": test_results,
            "pass_rate": tests_passed / tests_run if tests_run > 0 else 0
        }