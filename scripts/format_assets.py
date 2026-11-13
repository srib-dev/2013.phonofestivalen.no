#!/usr/bin/env python3
"""Beautify css/*.css and js/*.js under the mirror root (Drupal aggregates + mirror-fixes)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    try:
        import cssbeautifier
        import jsbeautifier
    except ImportError:
        print(
            "Install formatters: pip install jsbeautifier cssbeautifier",
            file=sys.stderr,
        )
        return 1

    js_opts = jsbeautifier.default_options()
    js_opts.indent_size = 2
    js_opts.end_with_newline = True
    js_opts.preserve_newlines = True
    js_opts.max_preserve_newlines = 2

    css_opts = cssbeautifier.default_options()
    css_opts.indent_size = 2
    css_opts.end_with_newline = True
    css_opts.newline_between_rules = True

    changed = 0
    for pattern, beautify, label in (
        ("css/*.css", lambda t: cssbeautifier.beautify(t, css_opts), "css"),
        ("js/*.js", lambda t: jsbeautifier.beautify(t, js_opts), "js"),
    ):
        for path in sorted(ROOT.glob(pattern)):
            raw = path.read_text(encoding="utf-8", errors="replace")
            if not raw.strip():
                if not raw.endswith("\n"):
                    path.write_text("\n", encoding="utf-8")
                    changed += 1
                continue
            try:
                new = beautify(raw)
            except Exception as exc:
                print(f"skip {path.name}: {exc}", file=sys.stderr)
                continue
            if not new.endswith("\n"):
                new += "\n"
            if new != raw:
                path.write_text(new, encoding="utf-8")
                print(f"formatted {label}: {path.name}")
                changed += 1

    print(f"Done. {changed} file(s) updated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
