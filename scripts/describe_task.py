#!/usr/bin/env python3
"""Describe a task directory under output/tasks.

Usage:
  python scripts/describe_task.py <slug_or_prefix> [--json]

Adds stronger typing and safer list handling to avoid "partially unknown" warnings.
"""
from __future__ import annotations
import sys, os, json
from pathlib import Path
from typing import Any, Dict, List, Optional, TypeGuard, cast

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'output'


def _is_str_list(val: Any) -> TypeGuard[List[str]]:
    if not isinstance(val, list):
        return False
    for x in val:  # type: ignore[assignment]
        if not isinstance(x, str):  # runtime guard ensures all elements str
            return False
    return True


def find_task(slug: str) -> Optional[Path]:
    tasks_dir = OUT / 'tasks'
    if not tasks_dir.exists():
        return None
    exact = tasks_dir / slug
    if exact.exists():
        return exact
    matches = [p for p in tasks_dir.iterdir() if p.is_dir() and p.name.startswith(slug)]
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]
    print(f"Multiple matches: {[m.name for m in matches]}")
    return None


def _load_summary(task_dir: Path) -> Dict[str, Any] | None:
    summary = task_dir / 'summary.json'
    if not summary.exists():
        print("No summary.json in task directory")
        return None
    try:
        data_raw = json.loads(summary.read_text(encoding='utf-8'))
    except Exception as e:
        print(f"Error reading summary: {e}")
        return None
    if not isinstance(data_raw, dict):
        print("Summary JSON not an object")
        return None
    return cast(Dict[str, Any], data_raw)


def _gather_view(data: Dict[str, Any], task_dir: Path) -> Dict[str, Any]:
    artifacts_raw = data.get('artifacts')
    artifacts: Dict[str, Any]
    if isinstance(artifacts_raw, dict):
        artifacts = cast(Dict[str, Any], artifacts_raw)
    else:
        artifacts = {}
    gen_raw = artifacts.get('generated_files')
    generated: List[str] = gen_raw[:25] if _is_str_list(gen_raw) else []
    note = artifacts.get('executable_note_text') or artifacts.get('executable_note')
    return {
        'task': task_dir.name,
        'description': str(data.get('description',''))[:160],
        'executable': artifacts.get('executable_artifact'),
        'generated_files': generated,
        'generated_count': len(generated),
        'build_log': artifacts.get('executable_build_log'),
        'build_note': note,
        'summary_path': str(task_dir / 'summary.json'),
    }


def _print_human(view: Dict[str, Any]) -> None:
    print(f"Task: {view['task']}")
    print(f"Description: {view['description']}")
    exe = view.get('executable')
    print(f"Executable: {exe if exe else '—'}")
    print("Generated files:")
    gen_any = view.get('generated_files', [])
    if isinstance(gen_any, list):
        for gf in gen_any:  # type: ignore[assignment]
            if isinstance(gf, str):
                print(f"  - {gf}")
    build_log = view.get('build_log')
    if isinstance(build_log, str) and os.path.isfile(build_log):
        print(f"Build log: {build_log}")
    note = view.get('build_note')
    if isinstance(note, str) and note:
        print("Build note:")
        print(note if '\n' in note else f"  {note}")


def main(argv: List[str]) -> int:
    if len(argv) < 2:
        print("Provide a task slug or prefix.")
        return 1
    want_json = '--json' in argv
    args = [a for a in argv[1:] if not a.startswith('--')]
    if not args:
        print("Provide a task slug or prefix.")
        return 1
    slug = args[0]
    task_dir = find_task(slug)
    if not task_dir:
        print("Task not found")
        return 2
    data = _load_summary(task_dir)
    if data is None:
        return 3
    view = _gather_view(data, task_dir)
    if want_json:
        print(json.dumps(view, indent=2))
    else:
        _print_human(view)
    return 0


if __name__ == '__main__':  # pragma: no cover
    raise SystemExit(main(sys.argv))