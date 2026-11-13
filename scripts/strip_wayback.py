#!/usr/bin/env python3
"""Remove Internet Archive / Wayback Machine traces from mirrored site files."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent

WAYBACK_FOOTER_RE = re.compile(
    r"\n*/\*\s*\n\s*FILE ARCHIVED ON.*?SECTION 108\(a\)\(3\)\)\.\s*\n\s*\*/\s*\n(?:\s*/\*\s*\n\s*playback timings.*?\*/\s*)?",
    re.DOTALL | re.IGNORECASE,
)
WAYBACK_HTML_COMMENT_RE = re.compile(
    r"<!--\s*\n\s*FILE ARCHIVED ON.*?-->\s*(?:<!--\s*\nplayback timings.*?-->\s*)?",
    re.DOTALL | re.IGNORECASE,
)

WOMBAT_HEADER = "var _____WB$wombat$assign$function_____"

LOCAL_PAGE_MAP = {
    "/nb": "Phonofestivalen 2013 _ 12 - 14 September, Bergen.html",
    "/nb/artister-2013/cold-mailman": "Phonofestivalen - Cold Mailman.html",
    "/nb/om-phonofestivalen": "Phonofestivalen - Om Phonofestivalen.html",
}


def list_image_basenames() -> set[str]:
    names: set[str] = set()
    img_dir = ROOT / "images"
    if img_dir.is_dir():
        for p in img_dir.iterdir():
            if p.is_file():
                names.add(p.name)
                names.add(p.name.lower())
    return names


IMAGE_BASENAMES = list_image_basenames()


def remove_wayback_footer(text: str) -> str:
    text = WAYBACK_FOOTER_RE.sub("\n", text)
    text = WAYBACK_HTML_COMMENT_RE.sub("", text)
    return text


def unwrap_wombat_js(text: str) -> str:
    text = remove_wayback_footer(text)
    if WOMBAT_HEADER not in text:
        return fix_stray_wombat_brace(text.rstrip() + "\n")

    # Drop preamble through opener= line (line 9)
    lines = text.splitlines(keepends=True)
    start = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("let opener"):
            start = i + 1
            break
    else:
        return text

    # Remove closing wrapper `    }` immediately before footer (already stripped) or at end
    body_lines = lines[start:]
    while body_lines and body_lines[-1].strip() == "":
        body_lines.pop()
    if body_lines and body_lines[-1].rstrip() == "}" and body_lines[-1].startswith("    "):
        body_lines.pop()
    while body_lines and body_lines[-1].strip() == "":
        body_lines.pop()

    out: list[str] = []
    for line in body_lines:
        if line.startswith("    "):
            out.append(line[4:])
        else:
            out.append(line)

    result = "".join(out).rstrip() + "\n"
    return fix_stray_wombat_brace(result)


def fix_stray_wombat_brace(text: str) -> str:
    """Drop a trailing lone `}` left from an incomplete wombat unwrap."""
    lines = text.rstrip().splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines or lines[-1].strip() != "}":
        return text.rstrip() + "\n"
    j = len(lines) - 2
    while j >= 0 and not lines[j].strip():
        j -= 1
    if j >= 0:
        prev = lines[j].rstrip()
        if prev.endswith(";") or prev.endswith(");"):
            lines.pop()
    return "\n".join(lines).rstrip() + "\n"


def strip_css_wayback_urls(text: str) -> str:
    text = remove_wayback_footer(text)

    def repl_absolute(m: re.Match[str]) -> str:
        return m.group(1)

    text = re.sub(
        r"https?://web\.archive\.org/web/\d+im_/https?://([^)\s\"']+)",
        repl_absolute,
        text,
    )
    text = re.sub(
        r"url\(/web/\d+im_/https?://([^)]+)\)",
        r"url(http://\1)",
        text,
    )
    text = re.sub(
        r"/web/\d+im_/https?://([^)\s\"']+)",
        r"http://\1",
        text,
    )
    text = re.sub(
        r"https?://web\.archive\.org/web/\d+im_/http://([^)\s\"']+)",
        r"http://\1",
        text,
    )
    return text.rstrip() + "\n"


def phonofestivalen_image_local(path: str) -> str | None:
    """Map original site file path to local images/ if we have the file."""
    path = unquote(path.split("?")[0])
    base = os.path.basename(path)
    if base in IMAGE_BASENAMES or base.lower() in IMAGE_BASENAMES:
        return f"images/{base}"
    return None


def rewrite_archived_url(url: str) -> str:
    """Rewrite a single URL that may still contain wayback wrapping."""
    if "web.archive.org" not in url and "/web/" not in url:
        return url

    m = re.match(
        r"https?://web\.archive\.org/web/\d+(?P<mod>[a-z]{2})_/http://www\.phonofestivalen\.no/(?P<path>[^\"']+)",
        url,
    )
    if m:
        path = unquote(m.group("path"))
        mod = m.group("mod")
        if mod == "cs" and path.startswith("sites/default/files/css/"):
            return "css/" + os.path.basename(path)
        if mod == "js" and path.startswith("sites/default/files/js/"):
            return "js/" + os.path.basename(path)
        if mod == "im":
            local = phonofestivalen_image_local(path)
            if local:
                return local
            return f"http://www.phonofestivalen.no/{path}"

    m = re.match(
        r"https?://web\.archive\.org/web/\d+cs_/http://fonts\.googleapis\.com/(?P<path>[^\"']+)",
        url,
    )
    if m:
        return "https://fonts.googleapis.com/" + m.group("path")

    m = re.match(r"https?://web\.archive\.org/web/\d+/http://(?P<rest>[^\"']+)", url)
    if m:
        return "http://" + unquote(m.group("rest"))

    m = re.match(r"https?://web\.archive\.org/web/\d+/https://(?P<rest>[^\"']+)", url)
    if m:
        return "https://" + unquote(m.group("rest"))

    m = re.match(r"https?://web\.archive\.org/web/\d+[a-z]{2}_/https?://(?P<rest>[^\"']+)", url)
    if m:
        return "https://" + unquote(m.group("rest"))

    m = re.match(r"//web\.archive\.org/web/\d+js_/http://(?P<rest>[^\"']+)", url)
    if m:
        return "http://" + unquote(m.group("rest"))

    m = re.match(r"/web/\d+\*?/http://www\.phonofestivalen\.no(?P<path>[^\"'#]*)", url)
    if m:
        path = unquote(m.group("path"))
        if path in LOCAL_PAGE_MAP:
            return LOCAL_PAGE_MAP[path]
        return f"http://www.phonofestivalen.no{path}"

    m = re.match(r"/web/\d+\*?/http://web\.archive\.org/.*", url)
    if m:
        return "#"

    m = re.match(
        r"/web/\d+im_/http://www\.phonofestivalen\.no/(?P<path>[^\"'?]+)",
        url,
    )
    if m:
        path = unquote(m.group("path"))
        local = phonofestivalen_image_local(path)
        if local:
            return local
        return f"http://www.phonofestivalen.no/{path}"

    m = re.match(
        r"/web/\d+im_/http://phonofestivalen\.no/(?P<path>[^\"'?]+)",
        url,
    )
    if m:
        path = unquote(m.group("path"))
        local = phonofestivalen_image_local(path)
        if local:
            return local
        return f"http://www.phonofestivalen.no/{path}"

    if "archive.org" in url or "web-static.archive" in url:
        return "#"

    return url


def rewrite_all_urls(text: str) -> str:
    patterns = [
        r"https?://web\.archive\.org/web/\d+(?:[a-z]{2})?_/https?://[^\"'\s<>]+",
        r"https?://web\.archive\.org/web/\d+/http://[^\"'\s<>]+",
        r"https?://web\.archive\.org/web/\d+/https://[^\"'\s<>]+",
        r"//web\.archive\.org/web/\d+js_/http://[^\"'\s<>]+",
        r"/web/\d+im_/http://[^\"'\s<>]+",
        r"/web/\d+\*?/http://[^\"'\s<>]+",
        r"https?://web-static\.archive\.org[^\"'\s<>]+",
        r"https?://archive\.org[^\"'\s<>]*",
    ]

    for pat in patterns:
        text = re.sub(pat, lambda m: rewrite_archived_url(m.group(0)), text)

    return text


def strip_html_wayback(text: str) -> str:
    text = remove_wayback_footer(text)

    # Normalize <head> if Wayback scripts were glued to <head>
    text = re.sub(r"<head>\s*<script[^>]*web-static\.archive[^>]*>.*?</script>\s*", "<head>\n", text, flags=re.DOTALL)

    # Remove Wayback head injection block
    text = re.sub(
        r"<script[^>]*web-static\.archive\.org[^>]*>.*?</script>\s*",
        "",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"<script type=\"text/javascript\">window\.addEventListener\('DOMContentLoaded',function\(\)\{var v=archive_analytics.*?</script>\s*",
        "",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"<script>\s*window\.RufflePlayer=.*?</script>\s*",
        "",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"<script type=\"text/javascript\">\s*__wm\.init.*?</script>\s*",
        "",
        text,
        flags=re.DOTALL,
    )
    text = re.sub(
        r"<link rel=\"stylesheet\"[^>]*web-static\.archive\.org[^>]*/>\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"<!-- End Wayback Rewrite JS Include -->\s*",
        "",
        text,
    )

    # Remove toolbar block
    text = re.sub(
        r"<!-- BEGIN WAYBACK TOOLBAR INSERT -->.*?<!-- END WAYBACK TOOLBAR INSERT -->\s*",
        "",
        text,
        flags=re.DOTALL,
    )

    # Stray toolbar init on body
    text = re.sub(r"<script>__wm\.rw\(0\);\s*</script>\s*", "", text)
    text = re.sub(
        r"<script type=\"text/javascript\">//<!\[CDATA\[\s*__wm\.bt\(.*?</script>\s*",
        "",
        text,
        flags=re.DOTALL,
    )

    # Remove Google Analytics loaded only via wayback wrapper (optional unwrap left as http URL)
    text = rewrite_all_urls(text)

    return text.rstrip() + "\n"


def process_file(path: Path) -> bool:
    raw = path.read_text(encoding="utf-8", errors="replace")
    if path.suffix == ".html":
        new = strip_html_wayback(raw)
    elif path.suffix == ".js":
        new = unwrap_wombat_js(raw)
        new = rewrite_all_urls(new)
        new = fix_stray_wombat_brace(new)
    elif path.suffix == ".css":
        new = strip_css_wayback_urls(raw)
    else:
        return False

    if new != raw:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def main() -> int:
    changed = 0
    for pattern in ("*.html", "js/*.js", "css/*.css"):
        for path in ROOT.glob(pattern):
            if process_file(path):
                print(f"updated: {path.relative_to(ROOT)}")
                changed += 1

    # Verify no obvious traces remain in those trees
    leftovers: list[str] = []
    for pattern in ("*.html", "js/*.js", "css/*.css"):
        for path in ROOT.glob(pattern):
            content = path.read_text(encoding="utf-8", errors="replace")
            for needle in (
                "web.archive.org",
                "web-static.archive.org",
                "archive.org",
                "WAYBACK",
                "_____WB$wombat",
                "__wm.",
                "/web/20",
                "INTERNET ARCHIVE",
            ):
                if needle.lower() in content.lower():
                    leftovers.append(f"{path.relative_to(ROOT)}: {needle}")
                    break

    if leftovers:
        print("\nRemaining traces (may need manual follow-up):", file=sys.stderr)
        for line in leftovers:
            print(f"  {line}", file=sys.stderr)

    print(f"\nDone. {changed} file(s) modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
