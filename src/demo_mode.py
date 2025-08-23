"""Demo mode logic (Core).

Implements a fixed, non-configurable cap of TWO (2) successful demo calls when:
  • DEMO_MODE_ENABLED=true (default in example) AND
  • OPENAI_API_KEY is NOT set.

After the cap is reached each attempt returns:
  {"success": false, "error": "NEED_API_KEY", "detail": "Demo limit reached (2/2). Please add your OPENAI_API_KEY."}

This module does NOT attempt to be persistent across process restarts; the
cap is deliberately ephemeral in Core. Maintainers can run a relay service
elsewhere; if DEMO_RELAY_URL is set we forward the request, otherwise we
return a synthetic stub reply for the first two calls.

Environment (read-only here):
  DEMO_MODE_ENABLED   -> enable demo path if truthy (default example: true)
  DEMO_RELAY_URL      -> optional OpenAI-compatible relay endpoint
  DEMO_RELAY_AUTH     -> optional shared secret for header X-Orbit-Demo

No environment variable can raise the cap beyond 2; attempts are ignored.
"""
from __future__ import annotations

import os, json, time, urllib.request, urllib.error
from typing import Dict, Any

_call_count = 0  # process-local counter (lowercase: mutable)
_CAP = 2  # immutable cap


def _truthy(key: str) -> bool:
    return os.getenv(key, "").strip().lower() in ("1", "true", "yes", "on")


def is_demo_active() -> bool:
    return _truthy("DEMO_MODE_ENABLED") and not os.getenv("OPENAI_API_KEY")


def remaining_calls() -> int:
    return max(0, _CAP - _call_count)


def _relay_request(prompt: str) -> str:
    url = os.getenv("DEMO_RELAY_URL", "").strip()
    if not url:
        # Fallback synthetic output (Core keeps zero external deps)
        return f"[demo] synthetic response for: {prompt[:60]}"  # not an LLM call

    payload: Dict[str, Any] = {
        "model": "gpt-4o-mini",  # minimal default; real relay may ignore
        "messages": [
            {"role": "system", "content": "OrbitSuite Core Demo Relay"},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 256,
        "stream": False,
    }
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    secret = os.getenv("DEMO_RELAY_AUTH", "").strip()
    if secret:
        headers["X-Orbit-Demo"] = secret
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
        obj = json.loads(body.decode("utf-8"))
    except urllib.error.HTTPError as e:  # network/relay error -> synthetic fallback
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = str(e)
        return f"[demo relay http {e.code}] {err_body[:120]}"
    except Exception as e:
        return f"[demo relay error] {e!r}"

    # Try to extract text similar to OpenAI shapes
    try:
        return obj["choices"][0]["message"]["content"]
    except Exception:
        return "[demo relay undecodable]"


def process_demo_request(text: str) -> Dict[str, Any]:
    global _call_count
    if not is_demo_active():
        return {"success": False, "error": "NOT_IN_DEMO"}

    if _call_count >= _CAP:
        return {
            "success": False,
            "error": "NEED_API_KEY",
        "detail": "Demo limit reached (2/2). Please add your OPENAI_API_KEY.",
        }

    call_number = _call_count + 1
    started = time.time()
    output = _relay_request(text)
    _call_count += 1

    return {
        "success": True,
        "demo": True,
        "call_number": call_number,
        "remaining": remaining_calls(),
        "processing_time": time.time() - started,
        "output": output,
    }


__all__ = [
    "process_demo_request",
    "is_demo_active",
    "remaining_calls",
]
