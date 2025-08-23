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
from src.utils import load_dotenv, is_verbose, truncate_string
load_dotenv()
from src.supervisor import Supervisor


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
            if self.path == '/process':
                content_length = int(self.headers['Content-Length'])
                post_data = self.rfile.read(content_length)
                
                try:
                    start = time.time()
                    data = json.loads(post_data.decode())
                    request_text = data.get('request', '')
                    
                    if not request_text:
                        self.send_response(400)
                        self.send_header('Content-Type', CONTENT_TYPE_JSON)
                        self.end_headers()
                        error = {"error": "Missing 'request' field"}
                        self.wfile.write(json.dumps(error).encode())
                        return
                    
                    if is_verbose():
                        print(f"[HTTP] /process request: {truncate_string(request_text, 160)}")
                    result = supervisor.process_request(request_text)
                    if is_verbose():
                        took = time.time() - start
                        ok = result.get('success', False)
                        print(f"[HTTP] /process response: success={ok} in {took:.2f}s")
                    
                    self.send_response(200)
                    self.send_header('Content-Type', CONTENT_TYPE_JSON)
                    self.end_headers()
                    self.wfile.write(json.dumps(result, indent=2, default=str).encode())
                
                except Exception as e:
                    self.send_response(500)
                    self.send_header('Content-Type', CONTENT_TYPE_JSON)
                    self.end_headers()
                    error = {"error": str(e)}
                    self.wfile.write(json.dumps(error).encode())
            else:
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
    while i < len(args):
        a = args[i]
        if a in ("-v", "--verbose"):
            os.environ["ORBITSUITE_VERBOSE"] = "1"
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


if __name__ == "__main__":
    main()