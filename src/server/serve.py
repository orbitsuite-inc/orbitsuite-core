"""Minimal stdlib HTTP server exposing only allowed Core endpoints.

Endpoints:
  POST /process        -> {text: str}
  POST /config/openai  -> {key: sk-...}

All /webhooks/* and /autosync/* paths return 403 (PRO_FEATURE).

Notes:
  • No external dependencies (FastAPI intentionally omitted to keep README claim).
  • Single startup banner (stdout) and then silence.
  • No retries / fallbacks here; just direct supervisor call.
"""
from __future__ import annotations

import json, os, sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.supervisor import Supervisor
from src.core_mode import core_banner, BANNER_PRINTED as _CORE_BANNER_FLAG  # constant style flag
import src.core_mode as _core_mode_mod
from src.demo_mode import process_demo_request, is_demo_active

# Mutable runtime state (lowercase to satisfy linters)
_supervisor_instance: Supervisor | None = None


def _get_supervisor() -> Supervisor:
    global _supervisor_instance
    if _supervisor_instance is None:
        _supervisor_instance = Supervisor(include_llm=False)  # Core: ignore local LLM env
    return _supervisor_instance


class CoreHandler(BaseHTTPRequestHandler):
    server_version = "OrbitSuiteCore/0.1"

    # Disable default logging to keep stdout quiet after banner
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003  # pragma: no cover
        # Override to silence default request logging (Core = stdout minimal)
        return

    def _json(self, status: int, obj: Dict[str, Any]) -> None:
        data = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):  # noqa: N802 - stdlib signature
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        body: Dict[str, Any]
        if raw:
            try:
                parsed = json.loads(raw.decode("utf-8"))
                if isinstance(parsed, dict):
                    # Safe cast for static type checkers (keys coerced to str)
                    body = {}
                    for _k, _v in parsed.items():  # type: ignore[assignment]
                        body[str(_k)] = _v  # type: ignore[index]
                else:
                    body = {}
            except Exception:
                return self._json(400, {"success": False, "error": "INVALID_JSON"})
        else:
            body = {}

        path = self.path or ""
        if path == "/process":
            text = str(body.get("text", "")).strip()
            if not text:
                return self._json(400, {"success": False, "error": "EMPTY_TEXT"})
            # Demo mode first (only active if no OPENAI_API_KEY)
            demo_resp = process_demo_request(text)
            if demo_resp.get("success") or demo_resp.get("error") == "NEED_API_KEY":
                return self._json(200 if demo_resp.get("success") else 403, demo_resp)
            # Not in demo (OPENAI_API_KEY present) -> normal supervisor path
            sup = _get_supervisor()
            result = sup.process_request(text)
            return self._json(200, {"success": bool(result.get("success", False)), "result": result})
        if path == "/config/openai":
            key = str(body.get("key", "")).strip()
            if not key.startswith("sk-"):
                return self._json(400, {"success": False, "error": "INVALID_KEY"})
            # Persist to .env (replace or append)
            lines: list[str] = []
            if os.path.isfile(".env"):
                try:
                    with open(".env", "r", encoding="utf-8") as f:
                        lines = f.readlines()
                except Exception:
                    lines = []
            found = False
            for i, line in enumerate(lines):
                if line.startswith("OPENAI_API_KEY="):
                    lines[i] = f"OPENAI_API_KEY={key}\n"
                    found = True
                    break
            if not found:
                lines.append(f"OPENAI_API_KEY={key}\n")
            try:
                with open(".env", "w", encoding="utf-8") as f:
                    f.writelines(lines)
                os.environ["OPENAI_API_KEY"] = key
            except Exception:
                return self._json(500, {"success": False, "error": "WRITE_FAILED"})
            return self._json(200, {"success": True})
        if path.startswith("/webhooks/") or path.startswith("/autosync/"):
            return self._json(403, {"success": False, "error": "PRO_FEATURE"})
        return self._json(404, {"success": False, "error": "NOT_FOUND"})

    # Basic CORS (optional minimal)
    def do_OPTIONS(self):  # noqa: N802
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


def run(host: str = "0.0.0.0", port: int = 8000) -> None:
    if not _CORE_BANNER_FLAG:
        print(core_banner())
        # mutate module variable (allowed) instead of rebinding imported name
        _core_mode_mod.BANNER_PRINTED = True  # type: ignore[attr-defined]
        # Warn if local LLM env vars present (ignored in Core)
        if any(os.getenv(k) for k in ("ORBITSUITE_LLM_MODEL_PATH", "ORBITSUITE_LLM_SERVER_URL", "ORBITSUITE_LLM_PROVIDER")):
            print("[Core Warning] Local LLM env detected but ignored (upgrade required).")
    httpd = ThreadingHTTPServer((host, port), CoreHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover
        pass
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run()
