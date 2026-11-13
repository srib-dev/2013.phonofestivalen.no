#!/usr/bin/env python3
"""Point site references at local files under the mirror root where possible."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent

HOME = "Phonofestivalen 2013 _ 12 - 14 September, Bergen.html"
DENIED = "Phonofestivalen - Tilgang nektet.html"
FALLBACK_IMAGE = "images/1260pix_topp_Web1_1.png"

# Drupal path (no host) -> local HTML
PAGE_BY_PATH: dict[str, str] = {
    "/nb": HOME,
    "/nb/nyheter": HOME,
    "/en": HOME,
    "/nb/om-phonofestivalen": "Phonofestivalen - Om Phonofestivalen.html",
    "/en/about-phonofestivalen": "Phonofestivalen - Om Phonofestivalen.html",
    "/nb/artister-2013/cold-mailman": "Phonofestivalen - Cold Mailman.html",
    "/artister-2013/cold-mailman": "Phonofestivalen - Cold Mailman.html",
}

PHONO_HOSTS = (
    "www.phonofestivalen.no",
    "phonofestivalen.no",
    "phonofestivalen",
)

SKIP_EXTERNAL_PREFIXES = (
    "http://s7.addthis.com/",
    "https://www.statcounter.com/",
    "https://c.statcounter.com/",
    "http://statcounter.com/",
    "http://twitter.com/",
    "https://w.soundcloud.com/",
    "http://vimeo.com/",
    "https://vimeo.com/",
    "mailto:",
    "tel:",
)

LOCAL_DIRS = {"images": ROOT / "images", "css": ROOT / "css", "js": ROOT / "js"}


def build_file_index() -> dict[str, str]:
    """Lowercase basename -> relative path like images/foo.png."""
    index: dict[str, str] = {}
    for folder, directory in LOCAL_DIRS.items():
        if not directory.is_dir():
            continue
        for path in sorted(directory.iterdir(), key=lambda p: p.name.lower()):
            if not path.is_file():
                continue
            rel = f"{folder}/{path.name}"
            key = path.name.lower()
            if key == "bombino.gif" and path.name == "bombino1.gif":
                index["bombino1.gif"] = rel
                continue
            if key == "bombino.gif" and path.name == "Bombino.gif":
                index[key] = rel
                continue
            if key == "bombino.gif" and path.name == "bombino.gif":
                if index.get(key, "").endswith("Bombino.gif"):
                    continue
                index[key] = rel
                continue
            if key not in index:
                index[key] = rel
    return index


FILE_INDEX = build_file_index()


def strip_query(url: str) -> str:
    return url.split("?", 1)[0].split("#", 1)[0]


def resolve_basename_asset(url: str) -> str | None:
    """If URL points at a file we have by basename, return local relative path."""
    path = unquote(strip_query(url))
    if "://" in path:
        path = urlparse(path).path or path
    parts = [p for p in Path(path).parts if p not in (".", "..")]
    for part in reversed(parts):
        hit = FILE_INDEX.get(part.lower())
        if hit:
            return hit
    base = Path(path).name
    if not base:
        return None
    hit = FILE_INDEX.get(base.lower())
    if hit and base.lower() in ("bombino.gif", "bombino1.gif"):
        canonical = ROOT / "images" / "Bombino.gif"
        if canonical.is_file():
            return "images/Bombino.gif"
    return hit


def normalize_site_path(path: str) -> str:
    path = unquote(path.split("?", 1)[0].split("#", 1)[0])
    if not path.startswith("/"):
        path = "/" + path
    if path.endswith("/") and path != "/":
        path = path.rstrip("/")
    return path


def resolve_phono_page(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.netloc and parsed.netloc not in PHONO_HOSTS:
        return None
    path = normalize_site_path(parsed.path or "/")
    if path.startswith("/sites/") or path.startswith("/misc/"):
        return None
    if path in PAGE_BY_PATH:
        return PAGE_BY_PATH[path]
    if path.startswith("/nb/artister-2013/"):
        slug = path.rsplit("/", 1)[-1]
        key = f"/nb/artister-2013/{slug}"
        if key in PAGE_BY_PATH:
            return PAGE_BY_PATH[key]
    if path.startswith("/artister-2013/"):
        slug = path.rsplit("/", 1)[-1]
        key = f"/artister-2013/{slug}"
        if key in PAGE_BY_PATH:
            return PAGE_BY_PATH[key]
        key = f"/nb/artister-2013/{slug}"
        if key in PAGE_BY_PATH:
            return PAGE_BY_PATH[key]
    if path in ("/nb", "/en", "/nb/nyheter"):
        return HOME
    if path.startswith("/nb/") or path.startswith("/en/"):
        return DENIED
    return DENIED


def resolve_phono_asset(url: str) -> str | None:
    """Map phonofestivalen.no file URLs to css/, js/, or images/."""
    parsed = urlparse(url)
    host = parsed.netloc
    if host and host not in PHONO_HOSTS:
        return None

    path = unquote(parsed.path or "")
    local = resolve_basename_asset(path)
    if local:
        return local

    if "/sites/default/files/css/" in path:
        base = Path(path).name
        if (ROOT / "css" / base).is_file():
            return f"css/{base}"
    if "/sites/default/files/js/" in path:
        base = Path(path).name
        if (ROOT / "js" / base).is_file():
            return f"js/{base}"

    return None


def is_skip_external(url: str) -> bool:
    return url.startswith(SKIP_EXTERNAL_PREFIXES)


def localize_url(url: str) -> str:
    url = url.strip()
    if not url or url.startswith("#"):
        return url
    if url.startswith("data:") or url.startswith("javascript:"):
        return url

    # Already local relative paths
    if re.match(r"^(?:\./)?(?:css|js|images)/", url):
        base = resolve_basename_asset(url)
        return base or url

    if "fonts.googleapis.com" in url and "Roboto" in url:
        return "css/roboto-condensed.css"

    if is_skip_external(url):
        return url

    if url.startswith("sites/default/files/"):
        local = resolve_basename_asset(url)
        return local or f"images/{Path(unquote(url)).name}"

    if "phonofestivalen" in url or urlparse(url).netloc in PHONO_HOSTS:
        asset = resolve_phono_asset(url)
        if asset:
            return asset
        page = resolve_phono_page(url)
        if page is not None:
            return page

    if url.startswith("/sites/default/files/") or url.startswith("/misc/"):
        asset = resolve_phono_asset("http://www.phonofestivalen.no" + url)
        if asset:
            return asset

    return url


def cleanup_unresolved_phono_urls(text: str, *, css_mode: bool = False) -> str:
    """Remove or neutralize phonofestivalen URLs we cannot map to a local file."""

    def repl_attr(m: re.Match[str]) -> str:
        name, quote, value = m.group(1), m.group(2), m.group(3)
        if "phonofestivalen.no" not in value and "phonofestivalen" not in value:
            return m.group(0)
        if name == "href" and "twitter.com/share" in value:
            value = value.replace(
                "http%3A//www.phonofestivalen.no/nb/artister-2013/cold-mailman",
                "Phonofestivalen%20-%20Cold%20Mailman.html",
            ).replace(
                "http://www.phonofestivalen.no/nb/artister-2013/cold-mailman",
                "Phonofestivalen%20-%20Cold%20Mailman.html",
            )
            return f"{name}={quote}{value}{quote}"
        if name in ("href", "action"):
            return f"{name}={quote}{DENIED}{quote}"
        # Leave unmatched images as-is rather than swapping in the site logo everywhere.
        return m.group(0)

    if css_mode:
        return re.sub(
            r"url\(http://www\.phonofestivalen\.no[^)]+\)",
            "url(none)",
            text,
            flags=re.IGNORECASE,
        )

    text = re.sub(
        r"(href|src|action|content|data-src)=(['\"])([^'\"]*phonofestivalen[^'\"]*)\2",
        repl_attr,
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"url\((['\"]?)(http://www\.phonofestivalen\.no[^)'\"]+)\1\)",
        r"url(none)",
        text,
        flags=re.IGNORECASE,
    )
    return text


def replace_urls_in_text(text: str, *, css_mode: bool = False) -> str:
    attr_pattern = re.compile(
        r"(href|src|action|content|data-src)=(['\"])((?:https?://)?[^'\"]+)\2",
        re.IGNORECASE,
    )
    url_pattern = re.compile(r"url\((['\"]?)([^)'\"]+)\1\)", re.IGNORECASE)

    def sub_attr_full(m: re.Match[str]) -> str:
        attr, quote, value = m.group(1), m.group(2), m.group(3)
        if attr.lower() == "content" and (
            value.startswith("mailto:")
            or ("@" in value and not value.startswith(("http://", "https://", "/")))
        ):
            return m.group(0)
        return f"{attr}={quote}{localize_url(value)}{quote}"

    out = attr_pattern.sub(sub_attr_full, text)
    out = url_pattern.sub(
        lambda m: f"url({m.group(1) or ''}{localize_url(m.group(2))}{m.group(1) or ''})",
        out,
    )

    # onmouseover/out paths
    def sub_inline(m: re.Match[str]) -> str:
        return localize_url(m.group(0))

    out = re.sub(
        r"(?:sites/default/files/|http://www\.phonofestivalen\.no/sites/default/files/)[^\s\"']+",
        sub_inline,
        out,
    )
    return cleanup_unresolved_phono_urls(out, css_mode=css_mode)


def local_page_path(href: str) -> Path | None:
    """If href is a same-directory HTML page, return its path under ROOT."""
    href = unquote(href.strip())
    if not href or href.startswith("#"):
        return None
    if re.match(r"^[a-z][a-z0-9+.-]*:", href, re.IGNORECASE):
        if not href.lower().startswith(("http://", "https://")):
            return None
        if "phonofestivalen" in href.lower():
            localized = localize_url(href)
            if localized != href:
                return local_page_path(localized)
        return None
    if href.startswith(("/", "css/", "js/", "images/")):
        return None
    if not href.lower().endswith(".html"):
        return None
    return ROOT / href


def is_local_page_href(href: str) -> bool:
    path = local_page_path(href)
    return path is not None and path.is_file()


def demote_spurious_home_hrefs(html: str) -> str:
    """Use home only for logo, language switcher, and explicit Hjem menu items."""
    esc_home = re.escape(HOME)
    anchor_home = re.compile(
        rf"(<a\s[^>]*\bhref=(['\"])){esc_home}\2",
        re.IGNORECASE,
    )
    html = anchor_home.sub(rf"\1{DENIED}\2", html)

    esc_denied = re.escape(DENIED)
    for pattern, repl in (
        (
            rf'(id="logo"[^>]*>\s*<a\s[^>]*\bhref=(["\'])){esc_denied}\2',
            rf"\1{HOME}\2",
        ),
        (
            rf'(id="site-name"[^>]*>\s*<a\s[^>]*\bhref=(["\'])){esc_denied}\2',
            rf"\1{HOME}\2",
        ),
        (
            rf'(<a\s[^>]*class="[^"]*language-link[^"]*"[^>]*\bhref=(["\'])){esc_denied}\2',
            rf"\1{HOME}\2",
        ),
        (
            rf'(<a\s[^>]*\bhref=(["\'])){esc_denied}\2([^>]*class="[^"]*language-link)',
            rf"\1{HOME}\2\3",
        ),
        (
            rf'(id="menu-951-1"[^>]*>[\s\S]*?<a\s[^>]*\bhref=(["\'])){esc_denied}\2',
            rf"\1{HOME}\2",
        ),
        (
            rf'(id="menu-2438-2"[^>]*>[\s\S]*?<a\s[^>]*\bhref=(["\'])){esc_denied}\2',
            rf"\1{HOME}\2",
        ),
    ):
        html = re.sub(pattern, repl, html, flags=re.IGNORECASE)
    return html


def resolve_anchor_href(href: str) -> str | None:
    """Return normalized href for an <a> tag, or None to leave unchanged."""
    if href.startswith("#") or href.lower().startswith(
        ("mailto:", "tel:", "javascript:", "data:")
    ):
        return None
    if re.match(r"^https?://", href, re.IGNORECASE):
        if "phonofestivalen" in href.lower():
            mapped = localize_url(href)
            if mapped != href and is_local_page_href(mapped):
                return mapped
            if mapped != href and local_page_path(mapped) is not None:
                return DENIED
        return None
    path = local_page_path(href)
    if path is None:
        return None
    if path.is_file():
        return None
    return DENIED


def ensure_local_page_hrefs(html: str) -> str:
    """Point <a> hrefs at local pages; missing targets -> access-denied page."""

    def repl(m: re.Match[str]) -> str:
        quote, href = m.group(2), m.group(3)
        resolved = resolve_anchor_href(href)
        if resolved is None:
            return m.group(0)
        return (
            f"<a {m.group(1)}href={quote}{resolved}{quote}{m.group(4)}"
        )

    html = re.sub(
        r"<a\s+([^>]*?\b)href=(['\"])([^'\"]*)\2([^>]*>)",
        repl,
        html,
        flags=re.IGNORECASE,
    )
    return demote_spurious_home_hrefs(html)


def prune_missing_asset_tags(html: str) -> str:
    """Drop link/script tags that point at missing local css/js bundles."""

    def missing_href(m: re.Match[str]) -> str:
        href = m.group(1)
        if href.startswith("css/") and not (ROOT / href).is_file():
            return ""
        if href.startswith("http://www.phonofestivalen.no/sites/default/files/css/"):
            return ""
        return m.group(0)

    def missing_script(m: re.Match[str]) -> str:
        src = m.group(1)
        if src.startswith("js/") and not (ROOT / src).is_file():
            return ""
        if src.startswith("http://www.phonofestivalen.no/sites/default/files/js/"):
            return ""
        return m.group(0)

    html = re.sub(
        r'<link[^>]+href="([^"]+)"[^>]*/>\s*',
        missing_href,
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'<script[^>]+src="([^"]+)"[^>]*>\s*</script>\s*',
        missing_script,
        html,
        flags=re.IGNORECASE,
    )
    # IE conditional stylesheet block
    html = re.sub(
        r"<!--\[if lt IE 8\]>.*?<!\[endif\]-->\s*",
        "",
        html,
        flags=re.DOTALL,
    )
    html = re.sub(
        r"<!--\[if lt IE 9\]>.*?<!\[endif\]-->\s*",
        "",
        html,
        flags=re.DOTALL,
    )
    # Legacy GA loader via dead host
    html = re.sub(
        r'<script>var _gaq = _gaq.*?googleanalytics/dc\.js.*?</script>\s*',
        "",
        html,
        flags=re.DOTALL,
    )
    html = re.sub(
        r'<script src="http://www\.phonofestivalen\.no/sites/all/themes/[^"]+"></script>\s*',
        "",
        html,
    )
    return html


def process_file(path: Path) -> bool:
    raw = path.read_text(encoding="utf-8", errors="replace")
    new = replace_urls_in_text(raw, css_mode=(path.suffix == ".css"))
    if path.suffix == ".html":
        new = prune_missing_asset_tags(new)
        new = ensure_local_page_hrefs(new)
        # canonical/shortlink to home or self
        if "Phonofestivalen - Cold Mailman" in path.name:
            new = re.sub(
                r'<link rel="(?:canonical|shortlink)" href="[^"]*"',
                lambda m: m.group(0).split("href=")[0] + 'href="Phonofestivalen - Cold Mailman.html"',
                new,
            )
        elif "Phonofestivalen - Om" in path.name:
            new = re.sub(
                r'<link rel="(?:canonical|shortlink)" href="[^"]*"',
                lambda m: m.group(0).split("href=")[0] + 'href="Phonofestivalen - Om Phonofestivalen.html"',
                new,
            )
        elif HOME in path.name:
            new = re.sub(
                r'<link rel="(?:canonical|shortlink)" href="[^"]*"',
                lambda m: m.group(0).split("href=")[0] + f'href="{HOME}"',
                new,
            )
    if new != raw:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def report_remaining() -> None:
    patterns = [
        (r"http://www\.phonofestivalen\.no", "remote phonofestivalen asset/page"),
        (r"http://phonofestivalen", "remote phonofestivalen (typo host)"),
        (r'src="css/[^"]+\.css"', "css link"),
        (r'src="js/[^"]+\.js"', "js script"),
    ]
    for glob in ("Phonofestivalen*.html", "css/*.css", "js/*.js"):
        for path in ROOT.glob(glob):
            text = path.read_text(encoding="utf-8", errors="replace")
            if "phonofestivalen.no" in text or "sites/default/files" in text:
                count = len(re.findall(r"phonofestivalen\.no|sites/default/files", text))
                print(f"  {path.name}: {count} remaining phonofestivalen path refs")


def main() -> int:
    changed = 0
    for pattern in ("Phonofestivalen*.html", "index.html", "css/*.css", "js/*.js"):
        for path in sorted(ROOT.glob(pattern)):
            if process_file(path):
                print(f"updated: {path.name}")
                changed += 1

    print(f"\nDone. {changed} file(s) modified.")
    print("\nRemaining references:")
    report_remaining()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
