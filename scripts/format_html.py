#!/usr/bin/env python3
"""Prettify mirror HTML (Phonofestivalen*.html in repo root) with Prettier."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

WAYBACK_FOOTER_RE = re.compile(
    r"/\*\s*\n\s*FILE ARCHIVED ON.*?SECTION 108\(a\)\(3\)\)\.\s*\n\s*\*/\s*"
    r"(?:\s*/\*\s*\n\s*playback timings.*?\*/\s*)?",
    re.DOTALL | re.IGNORECASE,
)
WAYBACK_HTML_COMMENT_RE = re.compile(
    r"<!--\s*\n\s*FILE ARCHIVED ON.*?-->\s*(?:<!--\s*\nplayback timings.*?-->\s*)?",
    re.DOTALL | re.IGNORECASE,
)

PRETTIER_ARGS = [
    "--parser",
    "html",
    "--print-width",
    "120",
    "--tab-width",
    "2",
    "--html-whitespace-sensitivity",
    "strict",
]


def strip_wayback_footer(text: str) -> str:
    text = WAYBACK_FOOTER_RE.sub("\n", text)
    text = WAYBACK_HTML_COMMENT_RE.sub("", text)
    return text


def run_prettier(paths: list[Path]) -> int:
    if not paths:
        return 0
    if shutil.which("npx"):
        cmd = ["npx", "--yes", "prettier@3", "--write", *PRETTIER_ARGS]
        cmd.extend(str(p) for p in paths)
        return subprocess.run(cmd, cwd=ROOT, check=False).returncode
    if shutil.which("prettier"):
        cmd = ["prettier", "--write", *PRETTIER_ARGS]
        cmd.extend(str(p) for p in paths)
        return subprocess.run(cmd, cwd=ROOT, check=False).returncode
    print("Install Node/npm and ensure npx is available, or install prettier globally.", file=sys.stderr)
    return 1


def main() -> int:
    paths = sorted(ROOT.glob("Phonofestivalen*.html"))
    target = ROOT / "index.html"
    if target.is_file():
        paths.append(target)

    if not paths:
        print("No mirror HTML files found.", file=sys.stderr)
        return 1

    changed = 0
    for path in paths:
        raw = path.read_text(encoding="utf-8", errors="replace")
        cleaned = strip_wayback_footer(raw)
        if cleaned != raw:
            path.write_text(cleaned, encoding="utf-8")
            changed += 1
            print(f"stripped archive footer: {path.name}")

    code = run_prettier(paths)
    if code != 0:
        return code

    print(f"Prettified {len(paths)} HTML file(s).")
    if changed:
        print(f"Removed Wayback footers from {changed} file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
