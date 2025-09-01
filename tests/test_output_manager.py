#!/usr/bin/env python3
"""Tests for output_manager utilities: migration, backfill, retention."""
import os, json, time
from pathlib import Path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from src import output_manager as om  # type: ignore


def _write(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


def test_migrate_legacy_layout(tmp_path: Path) -> None:
    out_root = tmp_path / 'output'
    final_dir = out_root / 'final'
    final_dir.mkdir(parents=True)
    # Legacy final json & exe
    summary = final_dir / 'build_a_tool_abcdef01.json'
    _write(summary, json.dumps({
        'description': 'Build a tool',
        'artifacts': {'generated_files': []}
    }, indent=2))
    exe = final_dir / 'build_a_tool_abcdef01.exe'
    _write(exe, 'MZ')
    created = om.migrate_legacy_layout(out_root)
    assert created, 'Migration should create at least one task dir'
    slug = created[0]
    task_dir = out_root / 'tasks' / slug
    assert task_dir.exists(), 'Task directory missing'
    assert (task_dir / 'summary.json').exists(), 'summary.json not moved'
    # Second run idempotent
    created2 = om.migrate_legacy_layout(out_root)
    assert not created2, 'Second migration pass should be no-op'


def test_backfill_generated_and_planning(tmp_path: Path) -> None:
    out_root = tmp_path / 'output'
    tasks_dir = out_root / 'tasks'
    tdir = tasks_dir / 'example_12345678'
    (tdir / 'generated').mkdir(parents=True, exist_ok=True)
    (tdir / 'planning').mkdir(exist_ok=True)
    codegen_dir = out_root / 'codegen'
    code_file = codegen_dir / 'core_task_1234abcd.py'
    _write(code_file, '# generated code')
    spec_file = out_root / 'spec_example.json'
    _write(spec_file, json.dumps({'spec': {'requirements': []}}))
    summary = tdir / 'summary.json'
    _write(summary, json.dumps({
        'description': 'Example task',
        'artifacts': {
            'generated_files': [str(code_file)],
            'spec_path': str(spec_file)
        }
    }))
    res = om.backfill_generated_and_planning(out_root)
    assert res['examined'] == 1
    assert res['copied'] >= 1
    assert any(p.suffix == '.py' for p in (tdir / 'generated').iterdir())
    assert any(sf.name == spec_file.name for sf in (tdir / 'planning').iterdir())


def test_retention_policy(tmp_path: Path) -> None:
    out_root = tmp_path / 'output'
    tasks_dir = out_root / 'tasks'
    # Create two tasks: one old, one recent
    old_dir = tasks_dir / 'oldtask_aaaaaaaa'
    new_dir = tasks_dir / 'newtask_bbbbbbbb'
    for d in (old_dir, new_dir):
        (d / 'generated').mkdir(parents=True, exist_ok=True)
        _write(d / 'summary.json', json.dumps({'description': d.name, 'artifacts': {'generated_files': []}}))
    # Set old mtime to 10 days ago
    ten_days = 10 * 86400
    past = time.time() - ten_days
    os.utime(old_dir, (past, past))
    res = om.apply_retention_policy(out_root, retention_days=7, max_disk_mb=None)
    assert 'oldtask_aaaaaaaa' in res['deleted']
    assert new_dir.exists()
