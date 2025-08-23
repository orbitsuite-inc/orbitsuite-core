"""core/src/codegen_agent.py
CodeGen Agent (Core edition) – OpenAI provider when configured, otherwise deterministic templates.
Local model references (Nemo / llama.cpp) removed in Core.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from typing import Dict, Any, Optional, TYPE_CHECKING, cast

from src.base_agent import BaseAgent

LLMAgent = None  # Local LLMAgent disabled in Core (upgrade for local adapters)

# Provider abstraction (OpenAI only in Core)
try:
    from .llm_provider import get_provider_from_env  # type: ignore
except Exception:  # pragma: no cover
    try:
        from llm_provider import get_provider_from_env  # type: ignore
    except Exception:
        get_provider_from_env = None  # type: ignore


class CodegenAgent(BaseAgent):
    """Code generation using OpenAI when available; else template templates (no local LLM)."""

    def __init__(self):
        super().__init__(name="codegen")
        self.version = "openai-or-templates-1.0"
        # Lazy-initialized LLM client (placeholder for upgrade editions)
        if TYPE_CHECKING:
            from .llm_agent import LLMAgent as LLMAgentType  # type: ignore
            self._llm: Optional[LLMAgentType] = None
        else:
            self._llm: Optional[Any] = None

    def _llm_available(self) -> bool:  # Always False: Core has no local LLM
        return False

    def run(self, input_data: Any) -> Dict[str, Any]:
        """Generate code from a prompt/spec using LLM with safe fallback."""
        if not input_data:
            return {"error": "Input required for code generation", "success": False}

        # Normalize input
        if isinstance(input_data, dict):
            data = cast(Dict[str, Any], input_data)
            prompt = str(data.get("prompt") or data.get("description") or "")
            language = str(data.get("language") or "python").strip().lower()
            task_id = str(data.get("task_id") or data.get("id") or "")
        else:
            prompt = str(input_data)
            language = "python"
            task_id = ""

        if not prompt:
            return {"error": "No prompt provided", "success": False}

        # Core: Only OpenAI provider path (auto-detected). Local LLMAgent removed.
        llm_used = False
        llm_output: Optional[str] = None
        if get_provider_from_env is not None:
            try:
                provider = get_provider_from_env()
                messages = [
                    {"role": "system", "content": f"You are a world-class code generator. Output ONLY {language} code. No explanations. No markdown."},
                    {"role": "user", "content": f"Generate {language} code for the following requirement. Be concise, correct, and production-quality.\n\nRequirement:\n{prompt}"},
                ]
                out_text = provider.generate(messages)
                # Treat bracket-prefixed diagnostic messages as failure (e.g., [LLM disabled], [LLM HTTP 401])
                if out_text and not out_text.lstrip().startswith("["):
                    llm_used = True
                    llm_output = str(out_text).strip()
            except Exception:
                pass  # silent fallback to templates

        # Choose best output: prefer LLM if looks like code; else fallback template
        code: str
        method: str
        if llm_used and llm_output:
            code = self._postprocess_llm_output(llm_output, language)
            method = "llm"
        else:
            code = self._generate_code(prompt, language)
            method = "template_based"
        # Write artifact to disk (core output path)
        try:
            from pathlib import Path
            import hashlib, time
            base_dir = Path.cwd() / "output" / "codegen"
            base_dir.mkdir(parents=True, exist_ok=True)
            # Derive stable file stem
            stem_source = task_id or prompt[:80]
            if not stem_source:
                stem_source = f"snippet_{int(time.time())}"
            safe_stem = "_".join(stem_source.lower().split())[:40]
            if not safe_stem:
                safe_stem = hashlib.sha1(stem_source.encode()).hexdigest()[:12]
            ext = {
                "python": ".py",
                "js": ".js",
                "javascript": ".js",
                "ts": ".ts",
                "typescript": ".ts",
                "go": ".go",
            }.get(language, f".{language}")
            file_path = base_dir / f"{safe_stem}{ext}"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(code)
            artifact_path = str(file_path)
        except Exception as e:
            artifact_path = ""
            write_error = str(e)
        else:
            write_error = None

        return {
            "success": True,
            "code": code,
            "language": language,
            "prompt": prompt,
            "method": method,
            "llm_used": llm_used,
            "artifact_path": artifact_path,
            **({"artifact_write_error": write_error} if write_error else {}),
        }

    def _postprocess_llm_output(self, text: str, language: str) -> str:
        # Strip common markdown fences if any slipped through
        t = text.strip()
        if t.startswith("```"):
            # Remove first fence line
            lines = t.splitlines()
            # drop first line and possible trailing fence
            body = "\n".join(lines[1:])
            if body.rstrip().endswith("```"):
                body = body.rsplit("```", 1)[0]
            t = body.strip()
        # Ensure Python returns a sensible snippet if empty
        if language.lower() == "python" and ("def " not in t and "class " not in t):
            # wrap as a function to satisfy downstream expectations
            t = f"""def generated_solution():\n    \"\"\"Generated code body.\n    Replace with an implementation for: {t or 'requested task'}\n    \"\"\"\n    pass\n"""
        return t

    def _generate_code(self, prompt: str, language: str) -> str:
        # Deterministic templates as fallback
        prompt_lower = prompt.lower()
        if language.lower() == "python":
            return self._generate_python_code(prompt_lower)
        return f"# Code generation for {language}\n# Task: {prompt}\n\n# TODO: Implement this functionality"

    def _generate_python_code(self, prompt: str) -> str:
        # Specific implementations for common tasks
        if "prime" in prompt:
            return '''# Generated Python code: Prime number utilities
from math import isqrt

def is_prime(n: int) -> bool:
    """Return True if n is a prime number (n >= 2)."""
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    limit = isqrt(n)
    f = 3
    while f <= limit:
        if n % f == 0:
            return False
        f += 2
    return True

def primes_up_to(limit: int) -> list[int]:
    """Return a list of all prime numbers up to and including 'limit'."""
    if limit < 2:
        return []
    primes = [2]
    for x in range(3, limit + 1, 2):
        if is_prime(x):
            primes.append(x)
    return primes

if __name__ == "__main__":
    # Example: print primes up to 1000
    print(primes_up_to(1000))
'''

        if "function" in prompt or "def" in prompt:
            return '''def example_function():
    """
    Generated function based on prompt.
    """
    # TODO: Implement function logic
    pass
    
    return "result"'''

        if "class" in prompt:
            return '''class ExampleClass:
    """
    Generated class based on prompt.
    """
    
    def __init__(self):
      # TODO: Initialize class
      pass
    
    def example_method(self):
      # TODO: Implement method
      return "result"'''

        if "api" in prompt or "fastapi" in prompt:
            return '''from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    """Generated API endpoint."""
    return {"message": "Hello World"}

@app.get("/items/{item_id}")
def read_item(item_id: int):
    """Generated API endpoint with parameter."""
    return {"item_id": item_id}'''

        if "test" in prompt:
            return '''import unittest

class TestExample(unittest.TestCase):
    """Generated test class."""
    
    def test_example(self):
        """Generated test method."""
        # TODO: Implement test logic
        self.assertTrue(True)
    
    def setUp(self):
        """Set up test fixtures."""
        pass

if __name__ == '__main__':
    unittest.main()'''

        return f'''# Generated Python code
# Task: {prompt}

def main():
    """
    Main function to accomplish the task.
    """
    # TODO: Implement the requested functionality
    print("Task: {prompt}")
    return True

if __name__ == "__main__":
    main()'''