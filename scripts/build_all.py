#!/usr/bin/env python3
"""Build helper: produces onefile & onedir PyInstaller distributions using local venv.

Usage (inside repo root):
    poetry run orbit-build
    # or
    poetry run python scripts/build_all.py

Outputs:
    dist/OrbitSuiteCore.exe                (onefile)
    dist/OrbitSuiteCore_onedir/            (onedir folder)
    dist/OrbitSuiteCore_onedir.exe         (launcher exe for onedir)
    dist/SHASUMS.txt                       (sha256 checksums of produced artifacts)

Environment:
    Uses existing *.spec files: OrbitSuiteCore.spec & OrbitSuiteCore_onedir.spec
    Requires PyInstaller present in the Poetry environment.
"""
from __future__ import annotations
import subprocess
import shutil
import hashlib
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
SPEC_ONEFILE = ROOT / "OrbitSuiteCore.spec"
SPEC_ONEDIR = ROOT / "OrbitSuiteCore_onedir.spec"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build"


def run(cmd: list[str]) -> int:
    print("→", " ".join(cmd))
    try:
        return subprocess.call(cmd)
    except KeyboardInterrupt:
        print("Interrupted")
        return 130
    except Exception as e:  # pragma: no cover
        print(f"Command error: {e}")
        return 1


def clean():
    for p in (BUILD_DIR,):
        if p.exists():
            print(f"Cleaning {p}…")
            shutil.rmtree(p, ignore_errors=True)
    # Keep dist between passes to compare sizes, but remove stale exe variants
    DIST_DIR.mkdir(exist_ok=True)


def build_onefile() -> Path | None:
    if not SPEC_ONEFILE.exists():
        print("Missing onefile spec")
        return None
    print("== Building onefile ==")
    code = run([sys.executable, "-m", "PyInstaller", str(SPEC_ONEFILE)])
    if code != 0:
        print("Onefile build failed")
        return None
    exe = DIST_DIR / "OrbitSuiteCore.exe"
    return exe if exe.exists() else None


def build_onedir() -> tuple[Path | None, Path | None]:
    if not SPEC_ONEDIR.exists():
        print("Missing onedir spec")
        return None, None
    print("== Building onedir ==")
    code = run([sys.executable, "-m", "PyInstaller", str(SPEC_ONEDIR)])
    if code != 0:
        print("Onedir build failed")
        return None, None
    exe = DIST_DIR / "OrbitSuiteCore_onedir.exe"
    folder = DIST_DIR / "OrbitSuiteCore_onedir"
    return (exe if exe.exists() else None, folder if folder.exists() else None)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def write_checksums(files: list[Path]):
    if not files:
        return
    out = DIST_DIR / "SHASUMS.txt"
    lines: list[str] = []
    for f in files:
        try:
            lines.append(f"{sha256_file(f)}  {f.name}")
        except Exception as e:  # pragma: no cover
            lines.append(f"ERROR  {f.name}  {e}")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


def main():  # pragma: no cover (external invocation)
    start = time.time()
    print("OrbitSuite Core build helper")
    print(f"Python: {sys.executable}")
    clean()
    produced: list[Path] = []
    onefile = build_onefile()
    if onefile:
        produced.append(onefile)
    onedir_exe, _ = build_onedir()
    if onedir_exe:
        produced.append(onedir_exe)
    # collect additional top-level DLLs or pyds in onedir folder for checksum clarity (optional)
    write_checksums([p for p in produced if p.is_file()])
    elapsed = time.time() - start
    print(f"Builds complete in {elapsed:.1f}s")
    for p in produced:
        size = p.stat().st_size if p.exists() else 0
        print(f" - {p.name}  {size/1_048_576:.2f} MB")
    if not produced:
        print("No artifacts produced (see errors above)")

if __name__ == "__main__":
    main()
