"""Output management utilities: migration, manifest, retention.

Phase 1+ enhancements centralised here to keep orchestrator lean.
"""
from __future__ import annotations
from pathlib import Path
import json, time, shutil
from typing import Any, Dict, List, cast

MANIFEST_NAME = 'manifest.json'
MIGRATION_MARKER = '.migrated_v1'
GLOBAL_DIR = 'global'

def _slug_from_filename(name: str) -> str:
    base = name.rsplit('.',1)[0]
    return base[:56]

def migrate_legacy_layout(root: Path) -> List[str]:
    """Migrate legacy flat final artifacts into tasks/<slug> structure.
    Returns list of created task dirs.
    """
    created: List[str] = []
    tasks_dir = root / 'tasks'
    final_dir = root / 'final'
    marker = root / MIGRATION_MARKER
    if marker.exists():
        return created
    if not final_dir.exists():
        marker.write_text('no-final')
        return created
    for jf in final_dir.glob('*.json'):
        if jf.name == 'traceability.json':
            continue
        slug = _slug_from_filename(jf.name)
        task_dir = tasks_dir / slug
        if task_dir.exists():
            continue
        (task_dir / 'generated').mkdir(parents=True, exist_ok=True)
        (task_dir / 'planning').mkdir(exist_ok=True)
        (task_dir / 'build').mkdir(exist_ok=True)
        (task_dir / 'patches').mkdir(exist_ok=True)
        # Move json -> summary.json
        target_summary = task_dir / 'summary.json'
        try:
            shutil.move(str(jf), target_summary)
        except Exception:
            continue
        # Move matching exe / note / build dir
        prefix = jf.name.rsplit('.',1)[0]
        exe = final_dir / f"{prefix}.exe"
        if exe.exists():
            try:
                shutil.move(str(exe), task_dir / 'build' / exe.name.replace(prefix, slug))
            except Exception:
                pass
        note = final_dir / f"{prefix}_exe_build.txt"
        if note.exists():
            try:
                shutil.move(str(note), task_dir / 'build' / 'note.txt')
            except Exception:
                pass
        build_dir = final_dir / f"_build_{prefix}"
        if build_dir.exists():
            try:
                shutil.move(str(build_dir), task_dir / 'build' / build_dir.name)
            except Exception:
                pass
        created.append(slug)
    try:
        marker.write_text('done')
    except Exception:
        pass
    return created

def load_manifest(root: Path) -> Dict[str, Any]:
    mpath = root / MANIFEST_NAME
    if mpath.exists():
        try:
            return json.loads(mpath.read_text(encoding='utf-8'))  # type: ignore[return-value]
        except Exception:
            return {}
    return {}

def save_manifest(root: Path, manifest: Dict[str, Any]) -> None:
    mpath = root / MANIFEST_NAME
    try:
        mpath.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    except Exception:
        pass

def update_manifest_entry(root: Path, slug: str, description: str, summary_path: Path, exe_path: str | None, generated_count: int) -> None:
    manifest = load_manifest(root)
    raw_tasks = manifest.get('tasks')
    tasks = cast(List[Dict[str, Any]], raw_tasks if isinstance(raw_tasks, list) else [])
    # filter out existing
    tasks = [t for t in tasks if t.get('slug') != slug]
    entry: Dict[str, Any] = {
        'slug': slug,
        'description': description[:240],
        'created_at': time.time(),
        'summary': str(summary_path),
        'generated_count': generated_count,
    }
    if exe_path:
        entry['exe'] = exe_path
    tasks.append(entry)
    manifest['tasks'] = tasks
    manifest['total_tasks'] = len(tasks)
    save_manifest(root, manifest)

def _dir_size_bytes(p: Path) -> int:
    total = 0
    try:
        for f in p.rglob('*'):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except Exception:
                    pass
    except Exception:
        pass
    return total

def apply_retention_policy(root: Path, retention_days: int, max_disk_mb: int | None = None) -> Dict[str, Any]:
    """Delete old task dirs beyond retention or to satisfy disk cap.
    Returns summary dict.
    """
    now = time.time()
    tasks_dir = root / 'tasks'
    global_dir = root / GLOBAL_DIR
    global_dir.mkdir(parents=True, exist_ok=True)
    log_path = global_dir / 'cleanup.log'
    deleted: List[str] = []
    kept: List[str] = []
    cutoff = now - retention_days * 86400 if retention_days > 0 else None
    task_dirs = [d for d in tasks_dir.glob('*') if d.is_dir()]
    # First pass: delete by age
    for d in task_dirs:
        if (d / '.keep').exists():
            kept.append(d.name)
            continue
        try:
            mtime = d.stat().st_mtime
        except Exception:
            mtime = now
        if cutoff and mtime < cutoff:
            try:
                shutil.rmtree(d, ignore_errors=True)
                deleted.append(d.name)
            except Exception:
                pass
    # Recompute remaining and disk usage
    remaining = [d for d in tasks_dir.glob('*') if d.is_dir()]
    disk_bytes = sum(_dir_size_bytes(d) for d in remaining)
    if max_disk_mb and max_disk_mb > 0:
        cap_bytes = max_disk_mb * 1024 * 1024
        if disk_bytes > cap_bytes:
            # Sort by mtime ascending (oldest first)
            rem_sorted = sorted(remaining, key=lambda p: p.stat().st_mtime)
            for d in rem_sorted:
                if disk_bytes <= cap_bytes:
                    break
                if (d / '.keep').exists():
                    continue
                try:
                    sz = _dir_size_bytes(d)
                    shutil.rmtree(d, ignore_errors=True)
                    deleted.append(d.name)
                    disk_bytes -= sz
                except Exception:
                    pass
    summary: Dict[str, Any] = {'deleted': deleted, 'kept': kept, 'disk_bytes': disk_bytes}
    try:
        with open(log_path, 'a', encoding='utf-8') as lf:
            lf.write(json.dumps({'ts': now, **summary}) + '\n')
    except Exception:
        pass
    return summary

def backfill_generated_and_planning(root: Path) -> Dict[str, Any]:
    """Ensure each task directory has local copies of generated code and planning artifacts.
    Idempotent; copies only missing files. Returns summary counts.
    """
    tasks_root = root / 'tasks'
    codegen_root = root / 'codegen'
    copied: int = 0
    planned: int = 0
    examined: int = 0
    if not tasks_root.exists():
        return {'examined': 0, 'copied': 0, 'planned': 0}
    for sdir in tasks_root.glob('*'):
        if not sdir.is_dir():
            continue
        summary_file = sdir / 'summary.json'
        if not summary_file.exists():
            continue
        examined += 1
        try:
            data = json.loads(summary_file.read_text(encoding='utf-8'))
            data_dict = cast(Dict[str, Any], data) if isinstance(data, dict) else {}
            artifacts = cast(Dict[str, Any], data_dict.get('artifacts', {}))
            gen_files = cast(List[str], artifacts.get('generated_files') or [])
            tgt_dir = sdir / 'generated'
            tgt_dir.mkdir(exist_ok=True)
            for gf in gen_files:
                src_p = Path(gf)
                # If relative, interpret relative to original codegen root
                if not src_p.is_absolute():
                    rel_name = src_p.name
                    alt = codegen_root / rel_name
                    if alt.exists():
                        src_p = alt
                if src_p.exists() and src_p.is_file():
                    dest = tgt_dir / src_p.name
                    if not dest.exists():
                        try:
                            shutil.copy2(src_p, dest)
                            copied += 1
                        except Exception:
                            pass
            # Planning artifacts
            planning_dir = sdir / 'planning'
            planning_dir.mkdir(exist_ok=True)
            for key in ('spec_path','design_path','plan_path','traceability_path'):
                pval = cast(str, artifacts.get(key))
                if pval:
                    src = Path(pval)
                    if src.exists() and src.is_file():
                        dest = planning_dir / src.name
                        if not dest.exists():
                            try:
                                shutil.copy2(src, dest)
                                planned += 1
                            except Exception:
                                pass
        except Exception:
            continue
    return {'examined': examined, 'copied': copied, 'planned': planned}
