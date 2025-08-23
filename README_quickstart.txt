OrbitSuite Core – Windows Quickstart (EXE First)
=================================================

Scope: OpenAI-only. Fixed 2-call demo via optional maintainer relay. No local LLMs, webhooks, autosync, retries, fallbacks, or logging subsystem (stdout only).

Files in ZIP:
  OrbitSuiteCore.exe
  .env.example
  README_quickstart.txt (this file)

Steps
-----
1. Extract the ZIP so OrbitSuiteCore.exe and .env.example sit in the same folder.
2. Double-click OrbitSuiteCore.exe. The local UI starts on http://localhost:8000
3. (Optional demo) You have up to 2 relay-backed calls if a maintainer relay is configured. After the cap you will see a modal requesting your OPENAI_API_KEY.
4. Provide your key:
   Option A: Paste into the modal (writes to .env).
   Option B: Manually create a .env file beside the EXE with a single line:
       OPENAI_API_KEY=sk-...
   Restart the EXE after creating/editing .env.

Environment (optional demo mode)
--------------------------------
To use a maintainer relay for the two demo calls, add these lines to .env (already present in .env.example):
    DEMO_MODE_ENABLED=true
    DEMO_RELAY_URL=http://127.0.0.1:5057/v1/chat/completions
    # Optional shared secret header value
    DEMO_RELAY_AUTH=

Behavior & Limits
-----------------
• Demo cap is hard-coded at 2 calls in Core (not configurable).
• After 2 calls without a local OPENAI_API_KEY, responses return an error prompting for a key.
• Keys are never embedded client-side; your key is read from .env at runtime.
• Core ships without retries, fallbacks, logging subsystem, webhooks, autosync, or local model adapters.

Uninstallation
--------------
Delete the extracted folder. The .env file (if created) contains your key—remove it if you no longer need local storage of the key.

Upgrade Path
------------
Need local LLMs, routing, advanced memory (MTS), reliability (retries/fallbacks/log rotation), webhooks, autosync, or multi-node orchestration? Upgrade to Pro / Enterprise.

Contact
-------
For upgrades or questions: sales@orbitsuite.cloud
