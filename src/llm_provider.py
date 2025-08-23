# Developer Notes:
# - Minimal provider abstraction for Core.
# - OpenAI provider uses stdlib urllib to avoid extra deps.
# - Local LLM provider is intentionally a stub here; the real one ships in Pro/Enterprise.
from __future__ import annotations
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import json, time, urllib.request, urllib.error
from typing import Dict, List, Any, cast

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


def get_provider_from_env() -> LLMProvider:
    """Return an appropriate provider for Core.

    Rules (Core):
      • If an OpenAI key is present (OPENAI_API_KEY or VS_CODE_OPENAI_KEY) use OpenAIChatProvider automatically.
      • Local provider env hints (nemo/local/llama) are treated as disabled in Core (return Noop with message).
      • ORBITSUITE_LLM_PROVIDER=openai still works explicitly.
    """
    # Core: if an OpenAI key is present (or explicitly requested), return OpenAI; else noop.
    provider = os.getenv("ORBITSUITE_LLM_PROVIDER", "").strip().lower()
    if provider == "openai" or os.getenv("VS_CODE_OPENAI_KEY") or os.getenv("OPENAI_API_KEY"):
        return OpenAIChatProvider()
    return NoopProvider()
