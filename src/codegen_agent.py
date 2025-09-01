from __future__ import annotations

"""Refactored CodeGen Agent (Core edition).

Design goals:
 - Separate LLM vs template logic cleanly
 - Deterministic concise templates (removed large calculator blocks)
 - Support for orchestrator-provided relative target path
 - Stronger typing & small helpers
"""

import hashlib, time
from pathlib import Path
from typing import Dict, Any, Optional, Protocol, runtime_checkable, cast

from src.base_agent import BaseAgent

# Try OpenAI provider; keep silent fallback
try:  # pragma: no cover - env dependent
    from .llm_provider import get_provider_from_env  # type: ignore
except Exception:  # pragma: no cover
    try:  # pragma: no cover
        from llm_provider import get_provider_from_env  # type: ignore
    except Exception:  # pragma: no cover
        get_provider_from_env = None  # type: ignore


from typing import TypedDict

# Prefer the shared schema when available; otherwise provide a runtime stub.
try:
    from .orbit_types import CodegenResult  # type: ignore
except Exception:  # pragma: no cover
    class CodegenResult(TypedDict, total=False):
        success: bool
        code: str
        language: str
        prompt: str
        method: str
        llm_used: bool
        artifact_path: str
        artifact_write_error: str
        target_rel_path: str


@runtime_checkable
class TemplateStrategy(Protocol):
    language: str
    def generate(self, prompt: str) -> str: ...  # pragma: no cover


class PythonTemplateStrategy:
    language = "python"
    _HEADER = "# Generated Python code\n"
    _PRIME_SNIPPET = (
        "from math import isqrt\n\n"
        "def is_prime(n: int) -> bool:\n"
        "    if n < 2: return False\n"
        "    if n % 2 == 0: return n == 2\n"
        "    lim = isqrt(n); f = 3\n"
        "    while f <= lim:\n"
        "        if n % f == 0: return False\n"
        "        f += 2\n"
        "    return True\n\n"
        "def primes_up_to(limit: int) -> list[int]:\n"
        "    return [x for x in range(2, limit+1) if is_prime(x)]\n"
    )

    def generate(self, prompt: str) -> str:  # noqa: C901
        p = prompt.lower()
        if "fastapi" in p or "api" in p:
            return (
                "from fastapi import FastAPI\n\n"
                "app = FastAPI()\n\n"
                "@app.get('/')\n"
                "def root(): return {'status':'ok'}\n"
            )
        if "prime" in p:
            return self._HEADER + self._PRIME_SNIPPET + "\nif __name__=='__main__': print(primes_up_to(100))\n"
        if any(k in p for k in ("test", "unittest")):
            return (
                "import unittest\n\n"
                "class TestExample(unittest.TestCase):\n"
                "    def test_truth(self): self.assertTrue(True)\n\n"
                "if __name__=='__main__': unittest.main()\n"
            )
        if "class" in p:
            return (
                "class GeneratedClass:\n"
                "    def __init__(self): self._ready = True\n\n"
                "    def status(self) -> str: return 'ready'\n"
            )
        if "function" in p or "def" in p:
            return (
                "def generated_function(x):\n"
                "    \"\"\"Generated function skeleton. Adjust as needed.\n\n"
                "    Args:\n"
                "        x: input value\n\n"
                "    Returns:\n"
                "        Any: processed value\n"
                "    \"\"\"\n"
                "    return x\n"
            )
        if "calculator" in p:
            return (
                "import ast, operator\n\n"
                "OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv,ast.Pow:operator.pow}\n"
                "def _eval(node):\n"
                "    if isinstance(node, ast.Expression): return _eval(node.body)\n"
                "    if isinstance(node, ast.Constant) and isinstance(node.value,(int,float)): return node.value\n"
                "    if isinstance(node, ast.BinOp):\n"
                "        t=type(node.op)\n"
                "        if t in OPS: return OPS[t](_eval(node.left), _eval(node.right))\n"
                "        raise ValueError('Unsupported operator')\n"
                "    raise ValueError('Unsupported expression node')\n"
                "def safe_eval(expr:str): return _eval(ast.parse(expr, mode='eval'))\n"
                "def main():\n"
                "    import sys; expr=' '.join(sys.argv[1:]) or '2+2'; print(safe_eval(expr))\n"
                "if __name__=='__main__': main()\n"
            )
        return (
            self._HEADER
            + f"# Task: {prompt}\n\n"
            + "def main():\n    print('Task placeholder')\n    return True\n\n"
            + "if __name__=='__main__': main()\n"
        )


LANGUAGE_STRATEGIES: Dict[str, TemplateStrategy] = {
    "python": PythonTemplateStrategy(),
}


class HtmlTemplateStrategy:
    language = "html"
    def generate(self, prompt: str) -> str:  # pragma: no cover - deterministic
        title = "Landing Page"
        if 'title' in prompt.lower():
            # naive extraction
            import re as _re
            m = _re.search(r"title[:=]\s*([\w \-]{3,60})", prompt, flags=_re.I)
            if m:
                title = m.group(1).strip()
        return (
            f"<!DOCTYPE html>\n<html lang='en'>\n<head>\n  <meta charset='UTF-8'/>\n  <meta name='viewport' content='width=device-width,initial-scale=1'/>\n  <title>{title}</title>\n  <link rel='stylesheet' href='styles.css'/>\n</head>\n<body>\n  <header class='hero'>\n    <h1>{title}</h1>\n    <p class='tagline'>Generated static landing page shell.</p>\n    <button id='ctaBtn'>Get Started</button>\n  </header>\n  <main id='content'></main>\n  <script src='script.js'></script>\n</body>\n</html>\n"
        )


class CssTemplateStrategy:
    language = "css"
    def generate(self, prompt: str) -> str:  # pragma: no cover - deterministic
        return (
            "/* Basic responsive layout & gradient */\n"
            ":root { --primary:#4b6ef5; --accent:#ff9966; --bg-gradient:linear-gradient(135deg,#141e30,#243b55); }\n"
            "body { margin:0; font-family:system-ui,Arial,sans-serif; color:#f5f7fa; background:var(--bg-gradient); min-height:100vh; }\n"
            ".hero { text-align:center; padding:12vh 2rem; }\n"
            ".hero h1 { font-size:clamp(2.5rem,6vw,4rem); margin:.2em 0; }\n"
            ".tagline { font-size:1.2rem; opacity:.85; }\n"
            "#ctaBtn { background:var(--primary); color:#fff; border:none; padding:.9rem 1.6rem; border-radius:6px; font-size:1rem; cursor:pointer; box-shadow:0 4px 16px -4px #0008; transition:background .2s; }\n"
            "#ctaBtn:hover { background:#3651c7; }\n"
            "@media (max-width:700px){ .hero{padding:8vh 1.2rem;} }\n"
        )


class JsTemplateStrategy:
    language = "javascript"
    def generate(self, prompt: str) -> str:  # pragma: no cover - deterministic
        return (
            "// Basic interactive enhancements\n"
            "document.addEventListener('DOMContentLoaded',()=>{\n"
            "  const btn=document.getElementById('ctaBtn');\n"
            "  if(btn){btn.addEventListener('click',()=>{\n"
            "    const c=document.getElementById('content');\n"
            "    if(c){c.innerHTML='<p>CTA clicked at '+new Date().toLocaleTimeString()+'</p>'; }\n"
            "  });}\n"
            "});\n"
        )

LANGUAGE_STRATEGIES.update({
    'html': HtmlTemplateStrategy(),
    'css': CssTemplateStrategy(),
    'javascript': JsTemplateStrategy(),
    'js': JsTemplateStrategy(),
})

_EXTENSIONS = {
    "python": ".py",
    "py": ".py",
    "js": ".js",
    "javascript": ".js",
    "html": ".html",
    "css": ".css",
    "ts": ".ts",
    "typescript": ".ts",
    "go": ".go",
}


def _safe_stem(raw: str) -> str:
    s = "_".join(raw.lower().split())[:48]
    return s or hashlib.sha1(raw.encode()).hexdigest()[:12]


def _derive_filename(task_id: str, prompt: str, language: str) -> str:
    base = task_id or prompt[:60] or f"snippet_{int(time.time())}"
    stem = _safe_stem(base)
    ext = _EXTENSIONS.get(language, f".{language}")
    return f"{stem}{ext}"


class CodegenAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="codegen")
        self.version = "refactored-1.2"

    def run(self, input_data: Any) -> CodegenResult:  # type: ignore[override]
        if not input_data:
            return CodegenResult(success=False, code="", language="", prompt="", method="error", llm_used=False, artifact_path="")

        data: Dict[str, Any]
        if isinstance(input_data, dict):
            data = cast(Dict[str, Any], input_data)
        else:
            data = {"prompt": str(input_data)}

        prompt = str(data.get("prompt") or data.get("description") or data.get("task") or "").strip()
        language = str(data.get("language") or "python").lower().strip()
        task_id = str(data.get("task_id") or data.get("id") or "").strip()
        target_rel = str(data.get("target_rel_path") or data.get("target_path") or "").strip()
        output_dir = data.get("output_dir")  # Can be None

        if not prompt:
            return CodegenResult(success=False, code="", language=language, prompt=prompt, method="error", llm_used=False, artifact_path="", artifact_write_error="empty_prompt")

        llm_used = False
        llm_code: Optional[str] = None
        if get_provider_from_env is not None:
            try:  # pragma: no cover - network
                provider = get_provider_from_env()
                messages = [
                    {"role": "system", "content": f"You output ONLY valid {language} source code."},
                    {"role": "user", "content": f"Generate {language} code for: {prompt}"},
                ]
                out_text = provider.generate(messages)
                if out_text and not out_text.lstrip().startswith("["):
                    llm_used = True
                    llm_code = self._strip_md_fence(out_text)
            except Exception:  # silent fallback
                pass

        if llm_used and llm_code:
            code = self._minimal_postprocess(llm_code, language)
            method = "llm"
        else:
            strategy = LANGUAGE_STRATEGIES.get(language) or LANGUAGE_STRATEGIES["python"]
            code = strategy.generate(prompt)
            method = "template"

        artifact_path, write_err = self._write_artifact(code, language, task_id, prompt, target_rel, output_dir)

        return CodegenResult(
            success=True,
            code=code,
            language=language,
            prompt=prompt,
            method=method,
            llm_used=llm_used,
            artifact_path=artifact_path,
            **({"artifact_write_error": write_err} if write_err else {}),
            **({"target_rel_path": target_rel} if target_rel else {}),
        )

    # Helpers
    def _strip_md_fence(self, text: str) -> str:
        t = text.strip()
        if t.startswith("```"):
            lines = t.splitlines()
            body = "\n".join(lines[1:])
            if body.rstrip().endswith("```"):
                body = body.rsplit("```", 1)[0]
            t = body.strip()
        return t

    def _minimal_postprocess(self, code: str, language: str) -> str:
        if language == "python" and not any(x in code for x in ("def ", "class ")):
            return "def generated():\n    return None\n"
        return code

    def _write_artifact(self, code: str, language: str, task_id: str, prompt: str, target_rel: str, output_dir: Optional[str] = None) -> tuple[str, Optional[str]]:
        if output_dir:
            base_dir = Path(output_dir)
        else:
            base_dir = Path.cwd() / "output" / "codegen"
        base_dir.mkdir(parents=True, exist_ok=True)
        if target_rel:
            out_path = base_dir / target_rel
        else:
            out_path = base_dir / _derive_filename(task_id, prompt, language)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            out_path.write_text(code, encoding="utf-8")
            return str(out_path), None
        except Exception as e:  # pragma: no cover
            return str(out_path), str(e)