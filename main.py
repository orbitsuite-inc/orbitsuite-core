#!/usr/bin/env python3
# core/main.py
"""OrbitSuite Core – OpenAI-only minimal runtime (no local model / GPU hooks).

Provides:
    • Interactive REPL (default when run from source).
    • Minimal HTTP API server (api / ui / serve modes or frozen binary default).

Removed in Core: any spawning of llama.cpp / local model servers, GPU tuning flags,
and related environment variable handling. Upgrade editions reintroduce those.
"""
import sys
import json
import time
import os
from typing import Any, Dict, TypeGuard
from src.utils import load_dotenv, is_verbose, truncate_string
load_dotenv()
"""Hardcoded local LLM stub switch (temporary debug aid).

Set ENABLE_LOCAL_LLM_STUB = True to force the offline LocalStubProvider
without needing to export environment variables manually. This only
applies when ORBITSUITE_LLM_PROVIDER is not already set externally.
"""
ENABLE_LOCAL_LLM_STUB = False  # flip to False to disable the local stub quickly
_EXE_SUFFIX_PROMPT = ' and produce an executable exe'

if ENABLE_LOCAL_LLM_STUB and not os.getenv("ORBITSUITE_LLM_PROVIDER"):
    os.environ["ORBITSUITE_LLM_PROVIDER"] = "local"
    # Optionally enable lightweight natural-language augmentation for engineer planning
    os.environ.setdefault("ORBITSUITE_NL_MODE", "1")
    # Provide a clear console notice (only once)
    print("[main] LocalStubProvider enabled (set ORBITSUITE_LLM_PROVIDER or toggle ENABLE_LOCAL_LLM_STUB to change).")

# Configure connection to local Nemo server
if not os.getenv("ORBITSUITE_LLM_SERVER_URL"):
    os.environ["ORBITSUITE_LLM_SERVER_URL"] = "http://172.23.80.1:8080"
    print("[main] Connecting to local Nemo server at http://172.23.80.1:8080")

from src.supervisor import Supervisor


# --- Helper Utilities (extracted from duplicated inline logic) ---
def _make_secondary_prompt(original: str) -> str:
    """Ensure the secondary prompt requests an executable build.

    Idempotent: if user already asked for an exe, returns original unchanged.
    """
    lower = original.lower()
    if 'exe' in lower or 'executable' in lower:
        return original
    return original.rstrip('.') + _EXE_SUFFIX_PROMPT


def _extract_pipeline_artifacts(result_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Navigate the nested supervisor -> orchestrator -> pipeline structure safely.

    Expected nesting (when present):
        { result: { result: { pipeline_artifacts: {...} } } }
    Returns empty dict if any layer absent / malformed.
    """
    try:
        lvl1 = result_dict.get('result')
        if not isinstance(lvl1, dict):
            return {}
        from typing import cast
        lvl1_dict = cast(Dict[str, Any], lvl1)
        lvl2 = lvl1_dict.get('result')
        if not isinstance(lvl2, dict):
            return {}
        lvl2_dict = cast(Dict[str, Any], lvl2)
        pipe = lvl2_dict.get('pipeline_artifacts')
        return cast(Dict[str, Any], pipe) if isinstance(pipe, dict) else {}
    except Exception:  # pragma: no cover
        return {}

def _is_str_list(val: Any) -> TypeGuard[list[str]]:
    if not isinstance(val, list):
        return False
    from typing import cast
    val_list = cast(list[Any], val)
    return all(isinstance(x, str) for x in val_list)


def _build_autobuild_info(secondary_result: Dict[str, Any], secondary_prompt: str) -> Dict[str, Any]:
    """Assemble the autobuild section for /process endpoint response."""
    sec_pipe = _extract_pipeline_artifacts(secondary_result)
    raw_gen = sec_pipe.get('generated_files')
    if _is_str_list(raw_gen):
        gen_preview = raw_gen[:10]
    else:
        gen_preview: list[str] = []
    return {
        'prompt_used': secondary_prompt,
        'success': bool(secondary_result.get('success')),
        'generated_files': gen_preview,
        'executable': sec_pipe.get('executable_artifact'),
        'final_output': sec_pipe.get('final_output'),
        'task_slug': sec_pipe.get('task_slug'),
        'task_dir': sec_pipe.get('task_dir'),
        'build_log': sec_pipe.get('executable_build_log'),
        'build_note': sec_pipe.get('executable_note') or sec_pipe.get('executable_note_text'),
    }


## _as_str_list helper removed (unused after refactor)


def interactive_mode() -> None:
    """Run interactive REPL mode."""
    supervisor = Supervisor()
    help_text = (
        "Available commands:\n"
        "- help: Show this help message\n"
        "- status: Show supervisor status\n"
        "- agents: List available agents\n"
        "- health: Run health check\n"
        "- quit/exit/q: Exit the program\n\n"
        "Or type any natural language request to process it through the agents.\n\n"
        "Examples:\n"
        "- Generate a Python function to calculate prime numbers\n"
        "- Test this code for syntax errors\n"
        "- Design a web API architecture\n"
        "- Save this data to memory\n"
    )
    while True:
        try:
            user_input = input("\n> ").strip()
            if user_input.lower() in {"quit", "exit", "q"}:
                print("Goodbye!")
                break
            if user_input.lower() == "help":
                print(help_text)
                continue
            if user_input.lower() == "status":
                status = supervisor.get_status()
                print(f"Status: {status['status']}")
                print(f"Agents: {', '.join(status['agents'])}")
                print(f"Tasks processed: {status['total_tasks_processed']}")
                continue
            if user_input.lower() == "agents":
                agent_info = supervisor.get_agent_info()
                for name, info in agent_info.items():
                    print(f"  {name}: {info['version']}")
                continue
            if user_input.lower() == "health":
                health = supervisor.health_check()
                print(f"Overall status: {health['overall_status']}")
                for agent, st in health['agent_checks'].items():
                    print(f"  {agent}: {st['status']}")
                continue
            if user_input:
                result = supervisor.process_request(user_input)
                if result.get("success"):
                    print(f"✅ Success (took {result['processing_time']:.2f}s)")
                    inner_raw_obj = result.get("result")
                    if isinstance(inner_raw_obj, dict):
                        inner_raw = inner_raw_obj  # type: ignore[assignment]
                        raw_code_obj = inner_raw.get("code")  # type: ignore[index]
                        code_val = raw_code_obj if isinstance(raw_code_obj, str) else None
                        if isinstance(code_val, str) and code_val:
                            print("📝 Generated code:")
                            snippet = code_val[:200] + "..." if len(code_val) > 200 else code_val
                            print(snippet)
                else:
                    print(f"❌ Error: {result.get('error', 'Unknown error')}")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            # Handle piped input gracefully
            print("\nGoodbye!")
            break
        except Exception as e:  # pragma: no cover
            print(f"Error: {e}")


def api_mode(port: int = 8000) -> None:
    """Run a minimal API server with a simple text UI at /."""
    print(f"OrbitSuite Core API server starting on port {port}")
    print("Open http://localhost:%d in your browser for the simple UI" % port)
    
    supervisor = Supervisor()
    
    # Simple HTTP server implementation
    from http.server import HTTPServer, BaseHTTPRequestHandler

    CONTENT_TYPE_JSON = 'application/json'

    class CoreHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ('/', '/index.html'):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers()
                html = f"""
<!doctype html>
<html lang=\"en\">
<head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>OrbitSuite Core · Simple UI</title>
    <style>
        :root {{
            --bg: #0f172a; --fg: #e2e8f0; --muted: #94a3b8; --accent: #38bdf8; --btn: #1e293b; --ok: #22c55e; --err: #ef4444;
        }}
        body {{ background: var(--bg); color: var(--fg); font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, Noto Sans, sans-serif; margin: 0; }}
        header {{ padding: 20px; border-bottom: 1px solid #1f2937; }}
        .wrap {{ max-width: 900px; margin: 0 auto; padding: 24px; }}
        h1 {{ margin: 0; font-size: 20px; letter-spacing: .3px; }}
        .card {{ background: #111827; border: 1px solid #1f2937; border-radius: 10px; padding: 16px; }}
        textarea {{ width: 100%; min-height: 140px; resize: vertical; background: #0b1220; color: var(--fg); border: 1px solid #1f2937; border-radius: 8px; padding: 10px; font-size: 14px; }}
        .row {{ display: flex; gap: 12px; align-items: center; margin-top: 10px; }}
        button {{ background: var(--btn); color: var(--fg); border: 1px solid #334155; padding: 10px 14px; border-radius: 8px; cursor: pointer; }}
        button:hover {{ border-color: var(--accent); }}
        .muted {{ color: var(--muted); font-size: 12px; }}
        .status {{ font-size: 12px; margin-left: auto; }}
        .status.ok {{ color: var(--ok); }}
        .status.err {{ color: var(--err); }}
        pre {{ white-space: pre-wrap; word-break: break-word; background: #0b1220; padding: 12px; border-radius: 8px; border: 1px solid #1f2937; }}
        .out {{ margin-top: 16px; }}
    </style>
    <script>
        async function sendRequest() {{
            const ta = document.getElementById('prompt');
            const btn = document.getElementById('sendBtn');
            const pre = document.getElementById('output');
            const status = document.getElementById('status');
            const text = ta.value.trim();
            if (!text) {{ return; }}
            btn.disabled = true; status.textContent = 'Working…'; status.className = 'status';
            try {{
                const resp = await fetch('/process', {{
                    method: 'POST', headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ request: text }})
                }});
                const data = await resp.json();
                let out = '';
                if (data && data.result) {{
                    const r = data.result;
                    if (typeof r === 'string') out = r;
                    else if (r.output) out = r.output;
                    else if (r.code) out = r.code;
                    else out = JSON.stringify(data, null, 2);
                }} else {{
                    out = JSON.stringify(data, null, 2);
                }}
                pre.textContent = out;
                status.textContent = data && data.success ? 'Done' : 'Error';
                status.className = 'status ' + (data && data.success ? 'ok' : 'err');
            }} catch (e) {{
                pre.textContent = String(e);
                status.textContent = 'Error';
                status.className = 'status err';
            }} finally {{ btn.disabled = false; }}
        }}
    </script>
    </head>
    <body>
        <header><div class=\"wrap\"><h1>OrbitSuite Core · Simple UI</h1></div></header>
        <main class=\"wrap\">
            <div class=\"card\">
                <label for=\"prompt\" class=\"muted\">Enter your request (natural language):</label>
                <textarea id=\"prompt\" placeholder=\"e.g., Build a FastAPI endpoint to create a user\"></textarea>
                <div class=\"row\">
                    <button id=\"sendBtn\" onclick=\"sendRequest()\">Send</button>
                    <span class=\"muted\">POST /process · port {port}</span>
                    <span id=\"status\" class=\"status\"></span>
                </div>
                <div class=\"out\">
                    <label class=\"muted\">Output:</label>
                    <pre id=\"output\"></pre>
                </div>
            </div>
        </main>
    </body>
</html>
"""
                self.wfile.write(html.encode('utf-8'))
            elif self.path == '/status':
                self.send_response(200)
                self.send_header('Content-Type', CONTENT_TYPE_JSON)
                self.end_headers()
                status = supervisor.get_status()
                self.wfile.write(json.dumps(status, indent=2).encode())
            elif self.path == '/health':
                self.send_response(200)
                self.send_header('Content-Type', CONTENT_TYPE_JSON)
                self.end_headers()
                health = supervisor.health_check()
                self.wfile.write(json.dumps(health, indent=2).encode())
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b'Not Found')
        
        def do_POST(self):
            # Streaming endpoint
            if self.path == '/process_stream':
                try:
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    data = json.loads(post_data.decode())
                    request_text = data.get('request', '')
                    if not request_text:
                        self.send_response(400)
                        self.send_header('Content-Type', 'text/plain')
                        self.end_headers()
                        self.wfile.write(b'Missing request')
                        return
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/event-stream')
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    def sse(event: str, data_str: str):
                        try:
                            self.wfile.write(f"event: {event}\n".encode())
                            self.wfile.write(f"data: {data_str}\n\n".encode())
                            self.wfile.flush()
                        except Exception:
                            pass
                    sse('progress', json.dumps({'stage':'primary_start'}))
                    step_events: list[dict[str, object]] = []
                    def _progress(ev: dict[str, object]):
                        # Forward immediately as SSE
                        evt = {
                            'event': ev.get('event'),
                            'step': ev.get('step'),
                            'action': ev.get('action'),
                            'status': ev.get('status')
                        }
                        step_events.append(evt)
                        try:
                            sse('step', json.dumps(evt))
                        except Exception:
                            pass
                    # Inject callback by wrapping request into dict for orchestrator path
                    primary = supervisor.process_request({'description': request_text, '_progress_cb': _progress})
                    sse('progress', json.dumps({'stage':'primary_done','success':primary.get('success', False)}))
                    secondary_prompt = _make_secondary_prompt(request_text)
                    sse('progress', json.dumps({'stage':'secondary_start','prompt':secondary_prompt[:80]}))
                    secondary = supervisor.process_request({'description': secondary_prompt, '_progress_cb': _progress})
                    sse('progress', json.dumps({'stage':'secondary_done','success':secondary.get('success', False)}))
                    sec_pipe: Dict[str, Any] = _extract_pipeline_artifacts(secondary)
                    final_payload: Dict[str, Any] = {
                        'primary': primary.get('success'),
                        'secondary': secondary.get('success'),
                        'autobuild': {
                            'prompt_used': secondary_prompt,
                            'executable': sec_pipe.get('executable_artifact'),
                            'final_output': sec_pipe.get('final_output'),
                            'task_slug': sec_pipe.get('task_slug'),
                            'task_dir': sec_pipe.get('task_dir'),
                            'build_log': sec_pipe.get('executable_build_log'),
                            'build_note': sec_pipe.get('executable_note') or sec_pipe.get('executable_note_text'),
                        },
                        'steps': step_events[-200:]
                    }
                    sse('result', json.dumps(final_payload))
                except Exception as e:
                    try:
                        self.wfile.write(f"event: error\ndata: {json.dumps({'error':str(e)})}\n\n".encode())
                    except Exception:
                        pass
                return
            # Standard /process endpoint
            if self.path == '/process':
                content_length = int(self.headers.get('Content-Length','0'))
                post_data = self.rfile.read(content_length) if content_length else b''
                try:
                    start = time.time()
                    data = json.loads(post_data.decode() or '{}')
                    request_text = data.get('request', '')
                    if not request_text:
                        self.send_response(400)
                        self.send_header('Content-Type', CONTENT_TYPE_JSON)
                        self.end_headers()
                        self.wfile.write(json.dumps({'error':'Missing "request" field'}).encode())
                        return
                    if is_verbose():
                        print(f"[HTTP] /process request: {truncate_string(request_text,160)}")
                    progress: list[dict[str, str]] = []
                    def _prog(stage: str, detail: str = ""):
                        entry = {"stage": stage}
                        if detail:
                            entry["detail"] = detail[:160]
                        progress.append(entry)
                    # Run primary request synchronously and record its status
                    result = supervisor.process_request(request_text)
                    _prog('primary_done', 'success' if result.get('success') else 'error')
                    secondary_prompt = _make_secondary_prompt(request_text)
                    _prog('secondary_start', secondary_prompt[:80])
                    secondary_result = supervisor.process_request(secondary_prompt)
                    _prog('secondary_done', 'success' if secondary_result.get('success') else 'error')
                    sec_pipe: Dict[str, Any] = _extract_pipeline_artifacts(secondary_result)
                    autobuild_info = _build_autobuild_info(secondary_result, secondary_prompt)
                    result.setdefault('autobuild', autobuild_info)
                    result['progress'] = progress
                    if is_verbose():
                        took = time.time() - start
                        print(f"[HTTP] /process response in {took:.2f}s success={result.get('success')}")
                    self.send_response(200)
                    self.send_header('Content-Type', CONTENT_TYPE_JSON)
                    self.end_headers()
                    self.wfile.write(json.dumps(result, indent=2, default=str).encode())
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-Type', CONTENT_TYPE_JSON)
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': str(e)}).encode())
                return
            # Unknown path
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    server = HTTPServer(('127.0.0.1', port), CoreHandler)
    print(f"Server running at http://localhost:{port}")
    print("Press Ctrl+C to stop")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.shutdown()


## _http_get removed (local server spawning removed in Core)


def main():
    """Main entry point."""
    # Parse debug/verbosity flags first
    args = sys.argv[1:]
    mode_args: list[str] = []
    wait_seconds: int | None = None
    i = 0
    autobuild = False
    autobuild_prompt: str | None = None
    while i < len(args):
        a = args[i]
        if a in ("-v", "--verbose"):
            os.environ["ORBITSUITE_VERBOSE"] = "1"
        elif a == "--autobuild":
            autobuild = True
        elif a.startswith("--autobuild-prompt="):
            autobuild = True
            autobuild_prompt = a.split("=",1)[1].strip() or None
        elif a.startswith("--wait="):
            val = a.split("=", 1)[1]
            try:
                wait_seconds = int(val)
            except ValueError:
                wait_seconds = -1
        elif a == "--wait":
            wait_seconds = -1
        elif a == "--wait-seconds" and i + 1 < len(args):
            try:
                wait_seconds = int(args[i + 1])
            except ValueError:
                wait_seconds = -1
            i += 1
        else:
            mode_args.append(a)
        i += 1

    if os.getenv("ORBITSUITE_VERBOSE") == "1":
        print("[startup] Verbose mode enabled")
        try:
            import platform
            print(f"[startup] Python {platform.python_version()} on {platform.platform()}")
            print(f"[startup] CWD={os.getcwd()}")
            print(f"[startup] Mode args={mode_args}")
        except Exception:
            pass

    if wait_seconds is not None:
        if wait_seconds < 0:
            try:
                input("[startup] Waiting (--wait). Press Enter to continue...")
            except EOFError:
                pass
        else:
            print(f"[startup] Waiting {wait_seconds}s before continuing (debug flag).")
            try:
                time.sleep(wait_seconds)
            except Exception:
                pass

    if mode_args:
        first = mode_args[0]
        if first in ("api", "ui"):
            port = int(mode_args[1]) if len(mode_args) > 1 else 8000
            api_mode(port)
            return
        if first in ("serve", "start"):
            ui_port = int(mode_args[1]) if len(mode_args) > 1 else 8000
            api_mode(ui_port)
            return
    # No mode args: if frozen default to api (UI); else interactive
    if getattr(sys, 'frozen', False):
        ui_port = int(os.getenv('ORBITSUITE_UI_PORT', '8000'))
        api_mode(ui_port)
    else:
        interactive_mode()

    # Optional post-run auto build (runs after interactive session exits or server mode returns)
    if (autobuild or os.getenv('ORBITSUITE_AUTOBUILD') == '1') and not os.getenv('ORBITSUITE_AUTOBUILD_DONE'):
        try:
            os.environ['ORBITSUITE_AUTOBUILD_DONE'] = '1'  # prevent recursion if main re-entered
            from src.supervisor import Supervisor as _Sup
            sup = _Sup()
            prompt = (autobuild_prompt or os.getenv('ORBITSUITE_AUTOBUILD_PROMPT') or
                      'Create a simple Python calculator that prints results and produce an executable exe')
            print(f"[autobuild] Processing request: {prompt[:120]}...")
            res = sup.process_request(prompt)
            pipe: Dict[str, Any] = _extract_pipeline_artifacts(res)
            gen_files_raw: Any = pipe.get('generated_files')
            gen_files: list[str] = []
            if isinstance(gen_files_raw, list):
                for _g in gen_files_raw:  # type: ignore[assignment]
                    if isinstance(_g, (str, bytes)):
                        gen_files.append(str(_g))
            exe_path = pipe.get('executable_artifact') or pipe.get('final_output')
            print('[autobuild] Generated files:', len(gen_files))
            if isinstance(exe_path, str) and exe_path:
                print('[autobuild] Executable:', exe_path)
            else:
                print('[autobuild] No executable produced in pipeline.')
        except Exception as e:  # pragma: no cover
            print(f"[autobuild] Error: {e}")


if __name__ == "__main__":
    main()