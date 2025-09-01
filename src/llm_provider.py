# Developer Notes:
# - Minimal provider abstraction for Core.
# - OpenAI provider uses stdlib urllib to avoid extra deps.
# - Local LLM provider is intentionally a stub here; the real one ships in Pro/Enterprise.
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import json, time, urllib.request, urllib.error
from typing import Dict, List, Any, cast, Optional

JSON = "application/json"

# --- Lightweight .env loader -------------------------------------------------
# We intentionally avoid adding python-dotenv dependency to keep Core minimal.
# This will parse a .env.local (preferred) then .env file if present, without
# overwriting existing environment variables (so externally set vars win).

_env_loaded: bool = False


def _load_local_env() -> None:
    global _env_loaded
    if _env_loaded:
        return
    for fname in (".env.local", ".env"):
        if not os.path.isfile(fname):
            continue
        try:
            with open(fname, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    # Remove optional surrounding quotes
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
        except Exception:
            # Silently ignore file parse errors to avoid import-time failures.
            pass
    _env_loaded = True


# Load env early so providers see variables even when running frozen binaries.
_load_local_env()


class LLMProvider:
    def generate(
        self,
        messages: List[Dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        timeout: int | None = None,
    ) -> str:
        raise NotImplementedError

class NoopProvider(LLMProvider):
    def generate(self, messages: List[Dict[str, str]], **kw: object) -> str:
        return ("[LLM disabled] Set ORBITSUITE_LLM_PROVIDER=openai and provide VS_CODE_OPENAI_KEY "
                "to enable inference in OrbitSuite-Core. Local LLM is part of Pro/Enterprise.")


class LocalStubProvider(LLMProvider):
    """Deterministic offline stub for debugging without network.

    Activate with: ORBITSUITE_LLM_PROVIDER=local
    Behavior: Inspects the latest user message, extracts basic intent keywords,
    and emits minimal code in a best-effort guessed language (default python).
    This is intentionally simplistic and NOT a real model.
    """

    def _infer_language(self, text: str) -> str:
        t = text.lower()
        if any(k in t for k in ("<html", "<!doctype html", "html", "landing page")):
            return "html"
        if any(k in t for k in ("css", "stylesheet")):
            return "css"
        if any(k in t for k in ("javascript", "js", "frontend")):
            return "javascript"
        if any(k in t for k in ("fastapi", "api")):
            return "python"
        return "python"

    def generate(self, messages: List[Dict[str, str]], **kw: object) -> str:
        user_content = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_content = m.get("content", "")
                break
        lang = self._infer_language(user_content)
        if lang == "python":
            return (
                "# LocalStubProvider generated code\n"
                "def stub_entry():\n"
                "    return 'stub-ok'\n\n"
                "if __name__=='__main__':\n"
                "    print(stub_entry())\n"
            )
        if lang == "html":
            return (
                "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Stub Page</title></head>"
                "<body><h1>Local Stub Landing</h1><p>Offline debug mode.</p></body></html>"
            )
        if lang == "css":
            return "/* Local stub CSS */\nbody{font-family:system-ui;margin:0;padding:2rem;}\n"
        if lang == "javascript":
            return "// Local stub JS\nconsole.log('stub-js');\n"
        return "// Local stub output (unrecognized language)\n"

class OpenAIChatProvider(LLMProvider):
    """Provider for OpenAI-compatible chat completion APIs.

    Environment variables:
      - VS_CODE_OPENAI_KEY (preferred) or OPENAI_API_KEY: bearer token
      - OPENAI_BASE_URL: base URL (default https://api.openai.com)
      - OPENAI_CHAT_PATH: path (default /v1/chat/completions). Set to /v1/responses for Responses API.
      - ORBITSUITE_OPENAI_MODEL: default model name (default gpt-4o-mini)
      - ORBITSUITE_TEMPERATURE, ORBITSUITE_MAX_TOKENS, ORBITSUITE_LLM_TIMEOUT
    """

    def __init__(self):
        # Support both custom VAR and the common OPENAI_API_KEY fallback.
        self.api_key = (os.getenv("VS_CODE_OPENAI_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com").rstrip("/")
        self.chat_path = os.getenv("OPENAI_CHAT_PATH", "/v1/chat/completions")
        self.default_model = os.getenv("ORBITSUITE_OPENAI_MODEL", "gpt-4o-mini")
        self.default_temperature = float(os.getenv("ORBITSUITE_TEMPERATURE", "0.8"))
        self.default_max_tokens = int(os.getenv("ORBITSUITE_MAX_TOKENS", "4096"))
        self.default_timeout = int(os.getenv("ORBITSUITE_LLM_TIMEOUT", "60"))

    def _build_payload(self, model: str, messages: List[Dict[str, str]], temperature: float, max_tokens: int) -> Dict[str, Any]:
        # Basic Chat Completions payload.
        if self.chat_path.endswith("/responses"):
            # Rough compatibility for Responses API: wrap messages into input (system+user merging simplistic).
            user_parts: List[str] = []
            for m in messages:
                role = m.get("role")
                content = m.get("content", "")
                if role == "system":
                    user_parts.append(f"[SYSTEM]\n{content}\n")
                else:
                    user_parts.append(content)
            return {
                "model": model,
                "input": "\n".join(user_parts),
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            }
        return {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

    @staticmethod
    def _extract_text(obj: Dict[str, Any]) -> str:
        # Try standard chat completions first
        try:
            return obj["choices"][0]["message"]["content"]
        except Exception:
            pass
        # Responses API shape possibilities
        if "output_text" in obj and isinstance(obj["output_text"], list):
            output_text_list = cast(List[Any], obj["output_text"])
            return "".join(str(x) for x in output_text_list).strip()
        if "output" in obj and isinstance(obj["output"], list):
            parts: List[str] = []
            for p in cast(List[Any], obj["output"]):
                if isinstance(p, dict):
                    p_dict = cast(Dict[str, Any], p)
                    txt_obj: Any = p_dict.get("content")
                    if not isinstance(txt_obj, str):
                        txt_obj = p_dict.get("text")
                    if isinstance(txt_obj, str):
                        parts.append(txt_obj)
            if parts:
                return "".join(parts).strip()
        # Last resort: dump JSON snippet
        return f"[LLM parse warning] Unexpected response shape: {json.dumps(list(obj.keys()))}"

    def generate(self, messages: List[Dict[str, str]], *, model: str | None = None, temperature: float | None = None, max_tokens: int | None = None, timeout: int | None = None) -> str:
        if not self.api_key:
            return "[LLM misconfigured] VS_CODE_OPENAI_KEY / OPENAI_API_KEY is not set."
        model = model or self.default_model
        temperature = self.default_temperature if temperature is None else float(temperature)
        max_tokens = self.default_max_tokens if max_tokens is None else int(max_tokens)
        timeout = self.default_timeout if timeout is None else int(timeout)

        url = f"{self.base_url}{self.chat_path}"
        payload = self._build_payload(model, messages, temperature, max_tokens)
        data = json.dumps(payload).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": JSON,
            "Accept": JSON,
        }
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
            obj = json.loads(body.decode("utf-8"))
            return self._extract_text(obj)
        except urllib.error.HTTPError as e:
            try:
                err = e.read().decode("utf-8")
            except Exception:
                err = str(e)
            return f"[LLM HTTP {e.code}] {err}"
        except Exception as e:
            elapsed = time.time() - start
            return f"[LLM error after {elapsed:.1f}s] {e!r}"


class LocalHTTPProvider(LLMProvider):
    """Simple local HTTP JSON provider.

    Expects an OpenAI-compatible endpoint OR a minimal endpoint that accepts:
        POST /v1/chat/completions { model, messages:[{role,content}], temperature?, max_tokens? }
    and returns standard OpenAI chat format. If response parsing fails we return
    a diagnostic message and allow caller to fallback.

    Environment variables:
      ORBITSUITE_LOCAL_LLM_BASE (default http://172.23.80.1:8080)
      ORBITSUITE_LOCAL_LLM_PATH (default /v1/chat/completions)
      ORBITSUITE_LOCAL_LLM_MODEL (default local-model)
      ORBITSUITE_LLM_TIMEOUT (shared) seconds
    """

    def __init__(self):
        self.base = os.getenv("ORBITSUITE_LOCAL_LLM_BASE", "http://172.23.80.1:8080").rstrip("/")
        self.path = os.getenv("ORBITSUITE_LOCAL_LLM_PATH", "/v1/chat/completions")
        self.model = os.getenv("ORBITSUITE_LOCAL_LLM_MODEL", "local-model")
        self.default_timeout = int(os.getenv("ORBITSUITE_LLM_TIMEOUT", "20"))
        self.default_temperature = float(os.getenv("ORBITSUITE_TEMPERATURE", "0.7"))
        self.default_max_tokens = int(os.getenv("ORBITSUITE_MAX_TOKENS", "2048"))

    def generate(self, messages: List[Dict[str, str]], *, model: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None, timeout: Optional[int] = None) -> str:  # type: ignore[override]
        url = f"{self.base}{self.path}"
        model = model or self.model
        temperature = self.default_temperature if temperature is None else float(temperature)
        max_tokens = self.default_max_tokens if max_tokens is None else int(max_tokens)
        timeout = self.default_timeout if timeout is None else int(timeout)
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": JSON, "Accept": JSON}
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        start = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
            obj_raw = json.loads(body.decode("utf-8"))
            obj = cast(Dict[str, Any], obj_raw) if isinstance(obj_raw, dict) else {"_raw": obj_raw}
            # Attempt to reuse OpenAI extraction logic for compatibility
            try:
                return OpenAIChatProvider._extract_text(obj)  # type: ignore[arg-type]
            except Exception:
                # Fallback: raw text fields
                for k in ("text", "output", "content"):
                    v = obj.get(k)
                    if isinstance(v, str) and v.strip():
                        return v
                return f"[local-llm warning] Unrecognized response shape keys={list(obj.keys())[:6]}"
        except Exception as e:
            elapsed = time.time() - start
            return f"[local-llm error after {elapsed:.1f}s] {e}"  # caller may fallback


# --- Chained fallback provider ------------------------------------------------
class ChainedProvider(LLMProvider):
    """Tries a sequence of providers (local-first) until one yields a non-errorish result.

    A result is considered *errorish* if it begins with one of the known diagnostic
    prefixes (e.g. "[local-llm error", "[LLM misconfigured", etc.). This keeps the
    caller code simple: they still invoke a single provider.

    Environment flags:
      ORBITSUITE_LLM_DISABLE_CHAIN=1   -> disable fallback (first provider only)
    """

    ERROR_PREFIXES = (
        "[local-llm error",
        "[local-llm warning",
        "[LLM misconfigured",
        "[LLM HTTP ",
        "[LLM error",
        "[LLM parse warning",
    )

    def __init__(self, *factories: "ProviderFactory") -> None:
        # Factories are zero-arg callables returning providers (lazy instantiation avoids
        # initializing network-backed providers unless needed).
        self._factories = factories
        self._disable_chain = os.getenv("ORBITSUITE_LLM_DISABLE_CHAIN", "0").lower() in ("1", "true", "yes", "on")

    @classmethod
    def _is_errorish(cls, text: str) -> bool:
        t = text.strip()
        for p in cls.ERROR_PREFIXES:
            if t.startswith(p):
                return True
        return False

    def generate(self, messages: List[Dict[str, str]], **kw: Any) -> str:  # type: ignore[override]
        last_output: str = ""
        for factory in self._factories:
            provider = factory()
            try:
                out = provider.generate(messages, **kw)
            except Exception as e:  # pragma: no cover - defensive
                out = f"[chain provider internal error] {e!r}"
            last_output = out
            if self._disable_chain:
                return out
            if not self._is_errorish(out):
                return out
            # else continue to next provider
        return last_output  # all failed/errorish


# Type alias for clarity of factory callables
from typing import Callable as _Callable
ProviderFactory = _Callable[[], LLMProvider]


def get_provider_from_env() -> LLMProvider:
    """Return a provider honoring local-first preference with graceful fallback.

    Updated behavior:
      - If ORBITSUITE_LLM_PROVIDER explicitly set, obey it. For 'localhttp' we wrap
        a chain LocalHTTP->OpenAI->Stub->Noop unless ORBITSUITE_LLM_DISABLE_CHAIN=1.
      - If unset, attempt a probe for localhttp; if reachable build the chain.
      - Otherwise pick OpenAI (if key), else stub (if stub hints), else noop.
    """
    explicit = os.getenv("ORBITSUITE_LLM_PROVIDER", "").strip().lower()

    def _openai_factory() -> LLMProvider:
        return OpenAIChatProvider() if (os.getenv("VS_CODE_OPENAI_KEY") or os.getenv("OPENAI_API_KEY")) else NoopProvider()

    def _stub_factory() -> LLMProvider:
        if os.getenv("ENABLE_LOCAL_LLM_STUB") or os.getenv("ORBITSUITE_NL_MODE"):
            return LocalStubProvider()
        return NoopProvider()

    # Explicit selection
    if explicit:
        if explicit == 'localhttp':
            return ChainedProvider(LocalHTTPProvider, _openai_factory, _stub_factory, NoopProvider)
        if explicit in ('local', 'stub'):
            return LocalStubProvider()
        if explicit == 'openai':
            return _openai_factory()
        if explicit == 'noop':  # optional manual override
            return NoopProvider()
        # Unknown explicit => fallback chain
        return ChainedProvider(LocalHTTPProvider, _openai_factory, _stub_factory, NoopProvider)

    # Implicit detection (no explicit variable)
    local_disabled = os.getenv("ORBITSUITE_DISABLE_LOCALHTTP", "0").lower() in ("1", "true", "yes", "on")
    if not local_disabled:
        base = os.getenv("ORBITSUITE_LOCAL_LLM_BASE", "http://172.23.80.1:8080").rstrip("/")
        probe_url = base
        try:
            req = urllib.request.Request(probe_url, method='GET')
            with urllib.request.urlopen(req, timeout=1) as _:
                return ChainedProvider(LocalHTTPProvider, _openai_factory, _stub_factory, NoopProvider)
        except Exception:
            pass

    # No local server reachable
    oa = _openai_factory()
    if isinstance(oa, OpenAIChatProvider):
        return oa
    stub = _stub_factory()
    if isinstance(stub, LocalStubProvider):
        return stub
    return NoopProvider()
