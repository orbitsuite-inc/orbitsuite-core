#!/usr/bin/env python3
"""
io_runner.py

Processes input prompts from io/input/plain (*.txt) and io/input/json (*.json)
and writes results to io/output/final as JSON files. Uses Supervisor to handle
plain text and structured tasks.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import json
from glob import glob
from typing import Any, Dict

# Ensure relative import works when executed as a module or script
try:
    from .utils import load_dotenv
    load_dotenv()  # load ./src/.env if present
    from .supervisor import Supervisor
except ImportError:  # pragma: no cover
    from utils import load_dotenv
    load_dotenv()
    from supervisor import Supervisor


def ensure_dirs(root: str) -> Dict[str, str]:
    base = os.path.abspath(root)
    dirs = {
        "plain": os.path.join(base, "input", "plain"),
        "json": os.path.join(base, "input", "json"),
        "final": os.path.join(base, "output", "final"),
    }
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
    return dirs


def process_plain_files(sv: Supervisor, in_dir: str, out_dir: str) -> int:
    count = 0
    for path in glob(os.path.join(in_dir, "*.txt")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                prompt = f.read().strip()
            if not prompt:
                continue
            result = sv.process_request(prompt)
            name = os.path.splitext(os.path.basename(path))[0]
            out_path = os.path.join(out_dir, f"{name}.result.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, default=str)
            count += 1
        except Exception as e:
            name = os.path.splitext(os.path.basename(path))[0]
            out_path = os.path.join(out_dir, f"{name}.error.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump({"success": False, "error": str(e)}, f, indent=2)
    return count


def process_json_files(sv: Supervisor, in_dir: str, out_dir: str) -> int:
    count = 0
    for path in glob(os.path.join(in_dir, "*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload: Any = json.load(f)
            # Accept either a single task dict or {"request": "..."}
            result = sv.process_request(payload)
            name = os.path.splitext(os.path.basename(path))[0]
            out_path = os.path.join(out_dir, f"{name}.result.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, default=str)
            count += 1
        except Exception as e:
            name = os.path.splitext(os.path.basename(path))[0]
            out_path = os.path.join(out_dir, f"{name}.error.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump({"success": False, "error": str(e)}, f, indent=2)
    return count


def run_io(root: str) -> Dict[str, int]:
    dirs = ensure_dirs(root)
    sv = Supervisor()
    processed_plain = process_plain_files(sv, dirs["plain"], dirs["final"])
    processed_json = process_json_files(sv, dirs["json"], dirs["final"])
    return {"plain": processed_plain, "json": processed_json, "total": processed_plain + processed_json}


if __name__ == "__main__":
    base = os.path.join(os.path.dirname(os.path.dirname(__file__)), "io")
    stats = run_io(base)
    print(json.dumps({"processed": stats}, indent=2))
