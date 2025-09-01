# OrbitS## Why OrbitSuite Core

- **Minimal by design**: single‑shot task execution with a straightforward cont## What's in Core

- **Supervisor**: basic process that starts the server and routes a task through the orchestrator.
- **Orchestrator (Conductor)**: simple routing to agents with **per-task directory isolation**. **No fallbacks** or retries in Core.
- **Agents**: `task_linguist`, `codegen`, `engineer` (Core), `tester`, `patcher`, `memory` (basic), and `llm` glu## Supported touch points (Core)

Core is intentionally minimal. The surface below is stable for basic use:
- **HTTP API**: `POST /process`, `POST /config/openai` (see "Minimal API").
- **Configuration**: `.env` with `OPENAI_API_KEY`, `ORBITSUITE_LLM_SERVER_URL`, `DEMO_MODE_ENABLED`, `DEMO_RELAY_URL`, optional `DEMO_RELAY_AUTH`.
- **LLM Adapters**: OpenAI and basic local server support. Advanced routing, retries/fallbacks, and GPU management are not available in Core.
- **Task Isolation**: Automatic per-task directory creation with organized output structure.

> Core does not include extensibility guidance for premium features. For those capabilities, upgrade to Pro/Enterprise.ask isolation**: each task creates its own directory (`/output/<task_slug>/`) with dedicated subdirectories for each agent (engineering/, codegen/, tests/, patches/, final/).
- **LLM adapters**: OpenAI and basic local server support (Nemo, Ollama). Advanced routing and GPU management in Pro/Enterprise.
- **Lightweight session memory**: short‑lived context for a single request/session.
- **Simple web UI**: submit a task and view results.
- **Stdout only**: no logging subsystem, retries, fallbacks, or rotation in Core.

> Core has **no** logging subsystem, retry logic, log rotation, webhooks, autosync, or advanced local model management. **Composable agents**: Task Linguist → CodeGen → Engineer → Tester → Patcher → Memory (basic).
- **Fast start**: OpenAI‑only or local LLM server; no GPU setup required. Two demo calls via relay, then paste your key or configure local server.
- **Task isolation**: each task gets its own directory structure preventing output conflicts.
- **Clear upgrade path**: when you need advanced memory, logging, retries, advanced routing/fallbacks, or fleet orchestration, Pro/Enterprise unlocks it without changing your workflows.

> Core intentionally omits logging systems, retries, fallbacks, log rotation, webhooks, autosync, and advanced local LLM management. It's a starter experience.e

Open-core agentic runtime for software development automation. Supervisor → Orchestrator → Agents. **OpenAI-only** in Core with a **fixed 2‑call demo** via a small relay, then bring your own OpenAI API key. Lightweight session memory, clean APIs, and a minimal web UI to run tasks end‑to‑end.

> License: Apache 2.0 (see `LICENSE.md`)

---

## Why OrbitSuite Core

- **Minimal by design**: single‑shot task execution with a straightforward control flow.
- **Composable agents**: Task Linguist → CodeGen → Engineer → Tester → Patcher → Memory (basic).
- **Fast start**: OpenAI‑only; no local model or GPU setup. Two demo calls via relay, then paste your key.
- **Clear upgrade path**: when you need advanced memory, logging, retries, advanced routing/fallbacks, or fleet orchestration, Pro/Enterprise unlocks it without changing your workflows.

> Core intentionally omits logging systems, retries, fallbacks, log rotation, webhooks, autosync, and local LLMs. It’s a starter experience.

---

## Quickstart

### Windows (1‑click binary)

1. Download the latest **Windows** release ZIP and extract it. You should see `OrbitSuiteCore.exe` and `.env.example` in the same folder.  
2. Double‑click `OrbitSuiteCore.exe`. The app starts at **http://localhost:8000**.  
3. You get **2 demo calls** if a relay is configured by the maintainer. After the cap, a popup asks for your `OPENAI_API_KEY` or you can configure a local LLM server.  
   - **Option A - OpenAI**: Paste your key in the popup **or** create a file named `.env` **next to the EXE** with:
     ```ini
     OPENAI_API_KEY=sk-...
     ```
   - **Option B - Local LLM**: Configure a local server (e.g., Nemo, Ollama) in `.env`:
     ```ini
     ORBITSUITE_LLM_SERVER_URL=http://127.0.0.1:8080
     ```
   - Restart the app. Calls now go directly to your configured provider.
4. If Windows SmartScreen warns (unsigned binary), choose **More info → Run anyway**.  
   If Windows Firewall prompts, allow `localhost` access.

> Notes  
> • The demo cap is fixed at **2** in Core.  
> • Core supports **OpenAI** and **local LLM servers** (Nemo, Ollama, etc.). Advanced local model management, GPU tuning, and multi-model routing are in Pro/Enterprise editions.

### Maintainers: optional demo relay

Offer two free calls without asking for a user key first. The relay holds **your** OpenAI key server‑side and rate‑limits to 2 calls/IP/day.

```bash
export OPENAI_API_KEY=sk-...   # maintainer key; do not commit this
uvicorn demo_relay:app --host 127.0.0.1 --port 5057
```

Point the app at the relay via `.env` (same folder as the EXE):
```ini
DEMO_MODE_ENABLED=true
DEMO_RELAY_URL=http://127.0.0.1:5057/v1/chat/completions
# optional:
DEMO_RELAY_AUTH=shared-secret
```

### Developer setup (macOS/Linux/Windows)

```bash
git clone <REPO_URL> orbitsuite-core
cd orbitsuite-core
python -m venv .venv && source .venv/bin/activate
pip install -U pip -r requirements.txt
cp .env.example .env
python -m orbitsuite.server.serve   # UI at http://localhost:8000
```

### Optional Environment Flags (Core Engineering / Build)

| Variable | Purpose | Typical Values | Notes |
| -------- | ------- | -------------- | ----- |
| `ORBITSUITE_NL_MODE` | Enables natural-language augmentation in `EngineerCore` (LLM extraction of requirements & file plans) | `0`, `1` | When `1/true`, the engineer attempts an LLM call (OpenAI only in Core) to enrich missing requirements/components. Safe to leave off for offline use. |
| `ORBITSUITE_BUILD_PYTHON` | Path to an external Python interpreter with PyInstaller installed, used when the orchestrator tries to build an `.exe` while running from a frozen core binary | Absolute path to `python.exe` | Only consulted inside a frozen (`OrbitSuiteCore.exe`) run; avoids trying to bundle from inside an already-frozen interpreter. |

Example (PowerShell):
```pwsh
$env:ORBITSUITE_NL_MODE=1
$env:ORBITSUITE_BUILD_PYTHON="C:\\Python311\\python.exe"
```

If you request an executable build in a frozen environment without `ORBITSUITE_BUILD_PYTHON`, the orchestrator will log a note explaining how to supply it.

---

## Demo mode (fixed 2 calls)

If demo mode is enabled and a relay is available, the app can make **up to two** chat calls through an OpenAI‑compatible relay. After the cap is reached, the UI prompts you to paste your `OPENAI_API_KEY` (stored locally in `.env`). **The cap is not configurable in Core.**

Required environment (already in `.env.example`):
```ini
DEMO_MODE_ENABLED=true
DEMO_RELAY_URL=http://127.0.0.1:5057/v1/chat/completions
# optional:
DEMO_RELAY_AUTH=shared-secret
```

If no relay is available, add your `OPENAI_API_KEY` to use the app immediately.

---

## What’s in Core

- **Supervisor**: basic process that starts the server and routes a task through the orchestrator.
- **Orchestrator (Conductor)**: simple routing to agents. **No fallbacks** or retries in Core.
- **Agents**: `task_linguist`, `codegen`, `engineer` (Core), `tester`, `patcher`, `memory` (basic), and `llm` glue.
- **Lightweight session memory**: short‑lived context for a single request/session.
- **Simple web UI**: submit a task and view results.
Stdout only: no logging subsystem, retries, fallbacks, or rotation in Core.
- **OpenAI adapter only**: predictable, easy to operate.

> Core has **no** logging subsystem, retry logic, log rotation, webhooks, autosync, or local model adapters.

---

## What’s in Pro / Enterprise

For teams that need scale, privacy, and control. Highlights include:

- **Mnemonic Token System (MTS)** advanced memory: multi‑tier memory (cache/buffer/pool), MemCube objects, token‑bath hydration, vector index, and retrieval‑augmented recall across tasks.
- **Local LLMs and routing** (upgrade): adapters for local/Ollama/HTTP servers, router, GPU configuration, and cost‑aware fallback.
- **Reliability & observability**: structured logging, retries with backoff, fallbacks, log rotation, traces/metrics.
- **Security & compliance**: Security Guard agent, sandbox enforcement, policy engine, signed adapter/model manifests, audit trails.
- **Orchestration at scale**: on‑prem/offline operation, multi‑node execution, queue/fleet management, job snapshots and revert, **webhook endpoints**, and **external‑store autosync** (Git/Gist, etc.).
- **Operations & governance**: capability/entitlement gating, license validation, role‑based agent access, telemetry, and advanced log pipelines.
- **OrbitCockpit**: IDE/ops surfaces for live runs, traces, and memory inspection.
- **Commercial support**: SLAs, guided onboarding, and long‑term maintenance.

## Tier Comparison & Upgrades

OrbitSuite is offered in three tiers. This repository contains only the Core (open) edition.

| Pillar | Core (this repo) | Pro | Enterprise |
| ------ | ---------------- | --- | ---------- |
| Tagline | Minimal open foundation | Local models + reliability toolkit | Scale, governance & memory intelligence |
| Routing | Direct dispatch (no retries/fallbacks) | Retries + fallback routing | Multi-node orchestration & queues
| Models | OpenAI + basic local server support | Advanced local adapters (llama.cpp / Ollama / HTTP) + router | All Pro + cost / policy enforcement |
| Task Isolation | Per-task directories (/output/task_slug/) | Enhanced with session management | Full isolation + multi-tenant support |
| Memory | Ephemeral in-process | Session extension helpers | Mnemonic Token System (multi-tier + vector recall) |
| Architecture Agent | Basic pattern + few components | Detailed components & roadmap | Full design suite + risk & compliance hooks |
| Logging / Observability | Stdout only (no subsystem) | Structured logs, rotation, basic metrics | Traces, dashboards, telemetry pipelines |
| Security / Compliance | — | Basic hardening | Security Guard / Entropy / Sandbox, audit trails |
| Governance | — | Basic license check | RBAC, entitlement gating, policy engine |
| Orchestration | Single-process with task isolation | Local workflow enhancements | Multi-node fleet, snapshots, webhooks, autosync (Git/Gist) |
| Support | Community | Email support | SLA, onboarding, long-term maintenance |

See `UPGRADE.md` for concise migration steps and `TIERS.md` for a more detailed breakdown.

*Contact us at sales@orbitsuite.cloud for a full feature comparison or a guided demo.*

---

## Core Agents

### BaseAgent
Abstract base class that all agents inherit from. Provides:
- Standard `dispatch()` method for task execution
- Abstract `run()` method that each agent implements
- Basic context and result storage

### TaskLinguistAgent
Converts natural language input into structured tasks:
- Simple keyword-based task type detection
- Basic agent routing logic
- Structured task format output

### CodegenAgent
Basic code generation capabilities:
- Template-based code generation for common patterns
- Support for Python, with basic templates for other languages
- Function, class, API, and test generation templates

### EngineerAgent
System design and architecture planning:
- Basic component identification
- Architecture pattern suggestions
- Technology stack recommendations
- Scalability and security considerations

### MemoryAgent
Simple memory operations:
- Key-value storage and retrieval
- Memory listing and clearing
- Metadata tracking (type, timestamp, size)

### TesterAgent
Code testing and validation:
- Basic syntax checking
- Code validation rules
- Simple test execution via subprocess
- Pass/fail reporting

### PatcherAgent
Code repair and modification:
- Basic syntax error fixes
- Code style improvements
- Automatic issue detection and repair
- Missing import detection

### OrchestratorAgent
Task coordination and workflow management:
- Task routing to appropriate agents
- **Per-task directory isolation** with unique task slugs
- Execution plan creation with task-specific output paths
- Workflow dependency analysis
- Agent registration and delegation
- Automatic directory structure creation (`engineering/`, `codegen/`, `tests/`, `patches/`, `final/`)

### Supervisor
Main coordination layer:
- Agent initialization and management
- Request processing and routing
- Health monitoring
- Task history and logging

## Task Isolation & Output Structure

Each task automatically creates an isolated directory structure to prevent output conflicts:

```
output/
├── task-description-words_hash123/
│   ├── engineering/     # Engineer agent analysis & planning
│   ├── codegen/         # Generated source code files
│   ├── tests/           # Test results and validation
│   ├── patches/         # Code fixes and improvements
│   ├── final/           # Final artifacts and traceability
│   └── tmpdist/         # Build artifacts (if applicable)
└── another-task-name_hash456/
    ├── engineering/
    └── ...
```

**Benefits:**
- **No conflicts**: Multiple tasks can run without overwriting each other's outputs
- **Clean organization**: Each task's artifacts are self-contained
- **Easy cleanup**: Remove entire task directories when no longer needed
- **Traceability**: Clear mapping from task description to output location

**Task Slug Generation:**
- Uses description keywords + SHA1 hash for uniqueness
- Example: `"create a calculator"` → `create-a-calculator_a1b2c3d4/`

## Features Removed (Minimal Version)

To achieve bare minimum functionality, the following features were removed:
- Advanced local model integrations and multi-model routing (basic local server support included)
- Database connections and persistence
- Advanced memory systems
- Complex workflow engines
- Extensive error handling and recovery (retries, fallback routing)
- Advanced monitoring and metrics
- Complex configuration systems
- Authentication and security layers
- Advanced logging and telemetry
- Multi-tenant task isolation (Core provides basic per-task directories)

# OrbitSuite Tiers Detail

This document expands the feature matrix to clarify value differentiation.

## Summary Taglines
- **Core**: Minimal open foundation.
- **Pro**: Local models + reliability toolkit.
- **Enterprise**: Scale, governance & memory intelligence.

## Pillars & Features

### 1. Model & Execution Control
| Feature | Core | Pro | Enterprise |
| ------- | ---- | --- | ---------- |
| OpenAI adapter | ✓ | ✓ | ✓ |
| Local model adapters (llama.cpp/Ollama/HTTP) | — | ✓ | ✓ |
| Model routing / cost-aware selection | — | ✓ | ✓ |
| GPU configuration helpers | — | ✓ | ✓ |
| Multi-node execution | — | — | ✓ |

### 2. Memory & Context
| Feature | Core | Pro | Enterprise |
| ------- | ---- | --- | ---------- |
| Ephemeral in-process context | ✓ | ✓ | ✓ |
| Session extension helpers | — | ✓ | ✓ |
| Mnemonic Token System (multi-tier) | — | — | ✓ |
| Vector index + RAG recall | — | — | ✓ |

### 3. Reliability & Observability
| Feature | Core | Pro | Enterprise |
| ------- | ---- | --- | ---------- |
| Stdout logging | ✓ | ✓ | ✓ |
| Structured JSON logging | — | ✓ | ✓ |
| Retries with backoff | — | ✓ | ✓ |
| Fallback routing | — | ✓ | ✓ |
| Log rotation | — | ✓ | ✓ |
| Traces / metrics dashboards | — | — | ✓ |

### 4. Architecture & Planning
| Feature | Core | Pro | Enterprise |
| ------- | ---- | --- | ---------- |
| Basic pattern recommendation | ✓ | ✓ | ✓ |
| Component synthesis (detailed) | — | ✓ | ✓ |
| Risk assessment & roadmap | — | ✓ | ✓ |
| Compliance & security hooks | — | — | ✓ |

### 5. Security & Compliance
| Feature | Core | Pro | Enterprise |
| ------- | ---- | --- | ---------- |
| Basic safe defaults | ✓ | ✓ | ✓ |
| Security Guard agent | — | — | ✓ |
| Entropy Monitor agent | — | — | ✓ |
| Sandbox Enforcement agent | — | — | ✓ |
| Policy engine / signed manifests | — | — | ✓ |
| Audit trails | — | — | ✓ |

### 6. Orchestration & Integration
| Feature | Core | Pro | Enterprise |
| ------- | ---- | --- | ---------- |
| Single-process orchestrator | ✓ | ✓ | ✓ |
| Enhanced local workflow features | — | ✓ | ✓ |
| Queue / fleet management | — | — | ✓ |
| Job snapshots & revert | — | — | ✓ |
| Webhook endpoints | — | — | ✓ |
| External-store autosync (Git/Gist) | — | — | ✓ |
| Offline / on-prem mode | — | — | ✓ |

### 7. Governance & Operations
| Feature | Core | Pro | Enterprise |
| ------- | ---- | --- | ---------- |
| Basic license check | — | ✓ | ✓ |
| Capability / entitlement gating | — | — | ✓ |
| Role-based agent access (RBAC) | — | — | ✓ |
| Telemetry export | — | — | ✓ |
| Advanced log pipelines | — | — | ✓ |

### 8. User & Support Experience
| Feature | Core | Pro | Enterprise |
| ------- | ---- | --- | ---------- |
| Community support | ✓ | ✓ | ✓ |
| Email support | — | ✓ | ✓ |
| SLA & guided onboarding | — | — | ✓ |
| OrbitCockpit (basic surfaces) | — | ✓ | ✓ |
| Live fleet dashboards / hardware panel | — | — | ✓ |

## Upgrade Hints
Core responses may include a single `upgrade_hint` key (optional) to signal available enhancements. This can be removed programmatically if undesired.

## Migration Philosophy
- Additive: higher tiers are supersets; no breaking schema changes.
- Deterministic Core: ensures trust & auditability.
- Seam continuity: identical method names enable drop-in replacement.

## When to Upgrade
| Symptom | Recommended Tier |
| ------- | ---------------- |
| Need offline / local-only inference | Pro |
| Latency & cost optimization across models | Pro |
| Cross-task long-term memory & semantic recall | Enterprise |
| Governance / audit mandates | Enterprise |
| Multi-team scaling & queue orchestration | Enterprise |
| Production SLAs & support | Enterprise |

## Contact
Reach out at sales@orbitsuite.cloud to obtain Pro / Enterprise pricing, licensing and distribution packages.


## Usage Examples

### Direct Agent Usage
```python
from core.src.codegen_agent import CodegenAgent

agent = CodegenAgent()
result = agent.run({
    "prompt": "Create a hello world function",
    "language": "python"
})
```

### Memory Operations
```python
from core.src.memory_agent import MemoryAgent

memory = MemoryAgent()
memory.run({"action": "save", "key": "test", "value": "data"})
result = memory.run({"action": "recall", "key": "test"})
```

### Task Processing
```python
from core.src.task_linguist import TaskLinguistAgent

linguist = TaskLinguistAgent()
task = linguist.run("Generate code for a calculator")
```

### Workflow Execution
```python
supervisor = create_supervisor()
workflow = [
    {"type": "codegen", "description": "Create function"},
    {"type": "testing", "description": "Test the function"}
]
result = supervisor.execute_workflow(workflow)
```

## Running the Demo

```bash
cd core/src
python demo.py
```

The demo script showcases all core functionality and validates that the minimal system is working correctly.

## Dependencies

The minimal core has **no external dependencies** beyond Python standard library. This ensures maximum compatibility and reduces complexity.

## Limitations

This minimal version:
- Uses simple template-based code generation instead of LLM (unless OpenAI API Key or local server provided)
- Has basic keyword-based task parsing instead of advanced NLP
- Stores memory in-process only (not persistent)
- Has simplified error handling
- Limited workflow capabilities
- No external integrations
- Basic local LLM server support (advanced routing and GPU management in Pro/Enterprise)

## Automatic Executable Artifact (Experimental)

When a task description includes intent keywords requesting an executable (e.g. phrases containing "executable", "exe", "build an executable", "make an exe", "windows binary"), the orchestrator will attempt to produce a Windows `.exe` artifact **after** code generation, testing, and patching complete.

How it works:
- Trigger: Keyword detection on the original task description (case‑insensitive).
- Prerequisite: `PyInstaller` must be importable in the current environment (Core does **not** bundle it inside the distributed binary). Install via: `pip install pyinstaller` during development.
- Build Mode: One‑file build (`--onefile`) inside an isolated staging directory under `output/final/_build_<task_hash>/`.
- Output Artifacts:
  - `<stem>.json` – final pipeline JSON artifact (existing behavior).
  - `<stem>.exe` – copied executable (if build succeeds).
  - `<stem>_exe_build.txt` – note file summarizing build outcome / errors.
  - `executable_artifact` & `executable_note` paths are added to the pipeline artifacts section of the orchestrator result.

Verbose Logging:
- Enable `ORBITSUITE_VERBOSE=1` to see `[Orchestrator][exe]` log lines indicating when a build is requested and the outcome note.

Failure / Skip Scenarios:
- If `PyInstaller` isn't installed, build is skipped with a note.
- Non‑zero exit codes, missing produced binary, or copy failures are captured in the note file.

Security Note:
- Generated code is packaged as‑is; review before distributing. Core does not perform hardening, sandboxing, or signing.

Size Expectations:
- Typical one‑file PyInstaller output for a small script ranges ~8–12 MB on Windows with default settings.

This feature is experimental and intentionally minimal—no custom spec merging, icon embedding, UPX compression toggles, or multi‑platform packaging. For advanced distribution workflows, inquire about Pro/Enterprise. 

# Upgrade to Pro / Enterprise

## Need reliability, governance, or privacy features? Pro/Enterprise adds:
- **Advanced memory (MTS)** with multi-tier recall.
- **Local LLM adapters + router** and cost/latency fallbacks.
- **Reliability & observability**: structured logs, retries with backoff, fallbacks, rotation, traces/metrics.
- **Security & compliance**: policy engine, sandbox enforcement, signed manifests, audit trails.
- **Orchestration at scale**: multi-node, queues, snapshots/revert, webhook endpoints, external-store autosync.
- **OrbitCockpit**: live runs, traces, memory inspection.
- **Support**: SLAs and guided onboarding.

Contact: **sales@orbitsuite.cloud** for a full comparison or demo.

## Supported touch points (Core)

Core is intentionally minimal. The surface below is stable for basic use:
- **HTTP API**: `POST /process`, `POST /config/openai` (see “Minimal API”).
- **Configuration**: `.env` with `OPENAI_API_KEY`, `DEMO_MODE_ENABLED`, `DEMO_RELAY_URL`, optional `DEMO_RELAY_AUTH`.
- **Adapter**: OpenAI only. Local models, webhooks, autosync, retries/fallbacks are not available in Core.

> Core does not include extensibility guidance for premium features. For those capabilities, upgrade to Pro/Enterprise.

---

## Configuration

All configuration is via environment variables (see `.env.example`).

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | empty | Your OpenAI key. When set, Core uses it and bypasses demo. |
| `ORBITSUITE_LLM_SERVER_URL` | empty | Local LLM server URL (e.g., `http://127.0.0.1:8080`). When set, routes to local server instead of OpenAI. |
| `DEMO_MODE_ENABLED` | `true` | Enable the demo path via relay. |
| `DEMO_RELAY_URL` | `http://127.0.0.1:5057/v1/chat/completions` | OpenAI‑compatible relay endpoint (maintainer‑hosted). |
| `DEMO_RELAY_AUTH` | empty | Optional shared secret header `X‑Orbit‑Demo` for relay. |
| `ORBITSUITE_VERBOSE` | `0` | Set to `1` to enable verbose logging output. |

---

## Minimal API

- `POST /process`  
  Request:
  ```json
  { "text": "Generate a simple calculator app..." }
  ```
  Response:
  ```json
  { "success": true, "result": { ... } }
  ```
  If the demo cap is exhausted or no key is present:
  ```json
  { "success": false, "error": "NEED_API_KEY", "detail": "Demo limit reached (2/2). Please add your OPENAI_API_KEY." }
  ```

- `POST /config/openai`  
  Saves a pasted OpenAI key to `.env`.
  ```json
  { "key": "sk-..." }
  ```

The simple web UI calls these endpoints for you.

---

## Security & Privacy

- Keys are never embedded in the client or committed to git.
- The demo relay keeps the maintainer key server‑side. Default rate‑limit: 2 calls per IP per 24h.
- Avoid submitting confidential data in demo mode.

---

## Limitations

- Core is **OpenAI‑only**. Local models and adapters are not included.
- The demo relay uses in‑memory rate limits; use Redis and an auth header (`DEMO_RELAY_AUTH`) for production.

---

## Contributing

Issues and pull requests are welcome. Please avoid committing `.env`, `.venv`, or model files. Keep diffs small and documented.

---

## Legal

Copyright © 2025 OrbitSuite, Inc.  
Apache License 2.0. See `LICENSE.md`.

See `UPGRADE.md` for concise migration steps and `TIERS.md` for a more detailed breakdown.
