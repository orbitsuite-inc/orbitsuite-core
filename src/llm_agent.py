#!/usr/bin/env python3
# core/src/llm_agent.py
# Local LLM agent using either llama-cpp-python bindings or a llama.cpp server backend.
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
from typing import Any, Dict, Optional, List, Tuple, cast, Protocol

import json
import urllib.request
import urllib.error


class SupportsLlama(Protocol):
    def create_chat_completion(self, *a: Any, **kw: Any) -> Any:
        ...
    def create_completion(self, *a: Any, **kw: Any) -> Any:
        ...


from src.base_agent import BaseAgent


class LLMAgent(BaseAgent):
    """
    LLMAgent executes prompts against a local LLM via either llama-cpp-python or a local llama.cpp server.

    Configuration (env or constructor):
    - ORBITSUITE_LLM_MODEL_PATH: path to .gguf file
    - ORBITSUITE_LLM_CTX: context window size (default 4096)
    - ORBITSUITE_LLM_GPU_ONLY: '1' to enforce GPU-only
    - ORBITSUITE_LLM_TEMPERATURE, ORBITSUITE_LLM_TOP_P, ORBITSUITE_LLM_MAX_TOKENS
    - ORBITSUITE_LLM_SERVER_URL: http://127.0.0.1:8080/v1 to use llama.cpp server instead of bindings
    - ORBITSUITE_LLM_SERVER_MODEL: model name to send to server (optional)
    - ORBITSUITE_LLM_SERVER_API_KEY: bearer token if the server enforces auth (optional)
    """

    # Class-level attribute annotations for better type checking
    _llm: Optional[SupportsLlama]
    _messages: List[Dict[str, str]]

    def __init__(
        self,
        model_path: Optional[str] = None,
        n_ctx: int = 4096,
        n_gpu_layers: Optional[int] = None,
        gpu_only: bool = True,
        temperature: float = 0.2,
        top_p: float = 0.95,
        max_tokens: int = 512,
    ) -> None:
        super().__init__(name="llm")
        self.version = "llm-local-1.1"

        # Core config
        self.model_path = model_path or os.getenv("ORBITSUITE_LLM_MODEL_PATH")
        self.n_ctx = int(os.getenv("ORBITSUITE_LLM_CTX", n_ctx))
        self.gpu_only = bool(gpu_only or os.getenv("ORBITSUITE_LLM_GPU_ONLY", "1") in ("1", "true", "True"))
        # If gpu_only, default to all layers on GPU
        self.n_gpu_layers = -1 if (n_gpu_layers is None and self.gpu_only) else (n_gpu_layers or 0)
        self.temperature = float(os.getenv("ORBITSUITE_LLM_TEMPERATURE", temperature))
        self.top_p = float(os.getenv("ORBITSUITE_LLM_TOP_P", top_p))
        self.max_tokens = int(os.getenv("ORBITSUITE_LLM_MAX_TOKENS", max_tokens))

        # Optional llama.cpp server config
        self.server_url = os.getenv("ORBITSUITE_LLM_SERVER_URL")
        self.server_model = os.getenv("ORBITSUITE_LLM_SERVER_MODEL")
        self.server_api_key = os.getenv("ORBITSUITE_LLM_SERVER_API_KEY", "")

        # Runtime state
        self._llm = None
        self._messages: List[Dict[str, str]] = []

    def _load_model(self) -> None:
        if self._llm is not None:
            return
        if self.server_url:
            return
        if not self.model_path:
            raise RuntimeError("LLMAgent: model_path is not set. Set ORBITSUITE_LLM_MODEL_PATH or pass to constructor.")
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"LLMAgent: model not found at '{self.model_path}'")

        try:
            from llama_cpp import Llama  # type: ignore
        except Exception as e:
            raise RuntimeError("LLMAgent: llama-cpp-python is not installed.") from e

        try:
            self._llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_gpu_layers=self.n_gpu_layers,
                logits_all=False,
                vocab_only=False,
                use_mlock=False,
                use_mmap=True,
                seed=0,
            )
        except Exception as e:
            raise RuntimeError(f"LLMAgent: failed to load model. Error: {e}") from e

    def run(self, input_data: Any) -> Dict[str, Any]:
        messages: Optional[List[Dict[str, str]]] = None
        system: Optional[str] = None
        reset = False

        if isinstance(input_data, dict):
            data = cast(Dict[str, Any], input_data)
            system = str(data.get("system", ""))
            reset = bool(data.get("reset", False))
            msgs = data.get("messages")
            if isinstance(msgs, list):
                # Explicitly type msgs as List[Dict[str, Any]] for type safety
                msgs_typed: List[Any] = msgs  # type: ignore
                typed_msgs: List[Dict[str, Any]] = [dict(cast(Dict[str, Any], m)) for m in msgs_typed if isinstance(m, dict)]
                messages = [{"role": str(m.get("role", "user")), "content": str(m.get("content", ""))} for m in typed_msgs]
            else:
                prompt = data.get("prompt") or data.get("description") or data.get("input") or data.get("request")
                if not prompt:
                    return {"success": False, "error": "LLM prompt is empty"}
                messages = [{"role": "user", "content": str(prompt)}]
        else:
            # Handle non-dict input (strings, etc.)
            input_str = str(input_data).strip()
            if not input_str:
                return {"success": False, "error": "LLM prompt is empty"}
            messages = [{"role": "user", "content": input_str}]

        if reset:
            self._messages = []

        if system and not self._messages:
            self._messages.append({"role": "system", "content": system})

        for m in messages or []:
            self._messages.append({"role": m.get("role", "user"), "content": m.get("content", "")})

        if self.server_url:
            try:
                text, usage = self._server_chat_completion(self._messages)
                self._messages.append({"role": "assistant", "content": text})
                return {
                    "success": True,
                    "output": text,
                    "usage": usage,
                    "messages": self._messages[-6:],
                }
            except Exception as e:
                return {"success": False, "error": str(e)}

        self._load_model()
        if not self._llm:
            raise RuntimeError("Model failed to load")

        try:
            if hasattr(self._llm, "create_chat_completion"):
                out = cast(Dict[str, Any], self._llm.create_chat_completion(
                    messages=self._messages,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    max_tokens=self.max_tokens,
                    stop=["</s>", "END_MARKER"],
                ))
                text = str(out.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()
            else:
                full_prompt = "\n".join([f"[{m['role'].upper()}] {m['content']}" for m in self._messages])
                out = cast(Dict[str, Any], self._llm.create_completion(
                    prompt=full_prompt,
                    temperature=self.temperature,
                    top_p=self.top_p,
                    max_tokens=self.max_tokens,
                    stop=["</s>", "END_MARKER"],
                ))
                text = str(out.get("choices", [{}])[0].get("text", "")).strip()

            self._messages.append({"role": "assistant", "content": text})
            return {
                "success": True,
                "output": text,
                "messages": self._messages[-6:],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- HTTP backend: llama.cpp OpenAI-compatible server ---
    def _server_chat_completion(self, messages: List[Dict[str, str]]) -> Tuple[str, Dict[str, Any]]:
        if not self.server_url:
            raise RuntimeError("LLMAgent: server_url not configured")
        url = self.server_url.rstrip("/") + "/chat/completions"
        headers = {"Content-Type": "application/json"}
        # Some servers require Authorization, others ignore it
        if self.server_api_key:
            headers["Authorization"] = f"Bearer {self.server_api_key}"

        payload: Dict[str, Any] = {
            "model": self.server_model or (os.path.basename(self.model_path) if self.model_path else "llama"),
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "stream": False,
            "stop": ["</s>", "END_MARKER"]
        }
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = resp.read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"LLMAgent(server): HTTP {e.code} {e.reason}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"LLMAgent(server): URL error {e.reason}")

        try:
            data = json.loads(body.decode("utf-8"))
        except Exception:
            raise RuntimeError("LLMAgent(server): Failed to parse JSON response")

        choices = cast(List[Dict[str, Any]], data.get("choices") or [])
        if not choices:
            raise RuntimeError("LLMAgent(server): No choices in response")
        msg = cast(Dict[str, Any], choices[0].get("message", {}))
        text = str(msg.get("content", "")).strip()
        usage = cast(Dict[str, Any], data.get("usage", {}))
        return text, usage
