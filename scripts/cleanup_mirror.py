#!/usr/bin/env python3
"""Polish the static mirror with minimal hand-editing of archived HTML/CSS/JS."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "images"
CSS = ROOT / "css"

# Drupal aggregates present locally — every mirror page needs these for layout/theme/menus.
REQUIRED_STYLESHEETS: list[tuple[str, str]] = [
    ("css/css_pbm0lsQQJ7A7WCCIMgxLho6mI_kBNgznNUWmTWcnfoE.css", "all"),
    ("css/css_O-ibS-KMtRhke6QnO02CxXA57wxb8-Q3dVtS0dtvAcA.css", "all"),
    ("css/css_Dvh7P_zNqlXqWpRMzIfrCFKI2YMofjwdmxMoqviEXRc.css", "all"),
    ("css/css_okuWAPrAhr1SWnWa9l6yAX1t5EsonQH6MHy-370IFw4.css", "screen"),
]

RESPONSIVE_CSS = "css/css_I3dax2qmoTi2rjzlTB1gRL0_MiG7W-aHpje8SaC8k5w.css"

# Front page Views Slideshow (fade cycle under the menu bar).
HOME_SLIDESHOW: list[str] = [
    "images/1081775_10201536360589225_871251707_n.jpg",
    "images/Web-banner2_2.jpg",
    "images/Web-banner1.jpg",
]

# Home page capture (Aug 2013) — good for shared assets
WB_IM = "https://web.archive.org/web/20130811072148im_/http://www.phonofestivalen.no"

DOWNLOADS: list[tuple[str, str]] = [
    ("/sites/default/files/styles/slideshow/public/Slideshow/Web-banner3.jpg", "Web-banner3.jpg"),
    ("/sites/default/files/omphono.png", "omphono.png"),
    ("/sites/default/files/phono%20%283%29.jpg", "phono-3.jpg"),
    (
        "/sites/default/files/styles/galleri_front_bilde/public/Kulturarrangement/sw.jpg",
        "kultur-sw.jpg",
    ),
    (
        "/sites/default/files/styles/galleri_front_bilde/public/Kulturarrangement/simen%20langeland.jpg",
        "simen-langeland.jpg",
    ),
    (
        "/sites/default/files/styles/galleri_front_bilde/public/Kulturarrangement/nobel_bopel_utenfor1.jpg",
        "nobel-bopel.jpg",
    ),
    (
        "/sites/default/files/styles/galleri_front_bilde/public/Samfunnsinnlegg/2-1.2.jpeg",
        "kulturtryne-2-1.2.jpeg",
    ),
    (
        "/sites/default/files/styles/galleri_front_bilde/public/Samfunnsinnlegg/mbos5.png",
        "kulturtryne-mbos5.png",
    ),
    (
        "/sites/default/files/styles/galleri_front_bilde/public/Samfunnsinnlegg/hissig.jpg",
        "kulturtryne-hissig.jpg",
    ),
    (
        "/sites/default/files/styles/galleri_front_bilde/public/Samfunnsinnlegg/fra.jpg",
        "kulturtryne-fra.jpg",
    ),
    ("/sites/all/modules/back_to_top/backtotop.png", "backtotop.png"),
    ("/sites/all/libraries/superfish/images/arrows-ffffff.png", "arrows-ffffff.png"),
    ("/sites/all/modules/service_links/images/twitter.png", "twitter.png"),
    ("/sites/all/themes/phonofestivalen/images/program/tid.png", "program-tid.png"),
    (
        "/sites/all/themes/phonofestivalen/images/program/arrangement.png",
        "program-arrangement.png",
    ),
    ("/sites/all/themes/phonofestivalen/images/program/dag.gif", "program-dag.gif"),
    ("/sites/all/themes/phonofestivalen/images/program/sted.png", "program-sted.png"),
    ("/sites/default/files/al/P%C3%A5l-og-hans.gif", "Pal-og-hans.gif"),
    (
        "/sites/default/files/styles/omtale-bilde/public/Artist-Omtalebilder/Cold-Mailman.gif",
        "Cold-Mailman-omtale.gif",
    ),
]

# title= attribute on kultur tiles -> local file (applied as regex)
TITLE_TO_IMAGE = {
    "Siw-Anita Kirketeig Phonofestivalen 2013": "images/kultur-sw.jpg",
    "Simen Langeland Phono 2013": "images/simen-langeland.jpg",
    "Nobel Bopel 2013 Phono": "images/nobel-bopel.jpg",
    "Ukas kulturtryne-Birk Nygaard": "images/kulturtryne-2-1.2.jpeg",
    "Ukas kulturtryne-Arash Shahali": "images/kulturtryne-mbos5.png",
    "Ukas kulturtryne--Magne Fonn Hafskår": "images/kulturtryne-hissig.jpg",
    "Fransisco Munoz": "images/kulturtryne-fra.jpg",
}

# If Wayback fetch fails, reuse existing mirror assets (better than the header logo).
TITLE_FALLBACKS = {
    "Siw-Anita Kirketeig Phonofestivalen 2013": "images/b6ea01ee592b_137422931532_nyhedstor2.jpeg",
    "Simen Langeland Phono 2013": "images/Hubba2.jpg",
    "Nobel Bopel 2013 Phono": "images/1081775_10201536360589225_871251707_n.jpg",
    "Ukas kulturtryne-Birk Nygaard": "images/2.jpeg",
    "Ukas kulturtryne-Arash Shahali": "images/hvalfall_0.jpg",
    "Ukas kulturtryne--Magne Fonn Hafskår": "images/warmup.gif",
    "Fransisco Munoz": "images/b6ea01ee592b_137422931532_nyhedstor2.jpeg",
}

def build_mirror_fixes_css() -> str:
    lines = [
        "/* Auto-generated mirror polish — overrides broken/missing remote assets */",
        "a.tabledrag-handle .handle,div.tree-child,div.tree-child-last{background-image:none;}",
        ".service-links-twitter{display:none;}",
        "#views_slideshow_cycle_teaser_section_slideshow-block{max-width:667px;margin:0 auto;}",
        "#block-views-slideshow-block .image-style-slideshow{width:100%;max-width:667px;height:auto;display:block;margin:0 auto;}",
        "#block-views-siste-nytt-block .views-field-field-artist-frontbilde,#block-views-siste-nytt-block #latest-news-img{display:none!important;}",
        "#block-views-older-news-block #older-post-img{display:none!important;}",
    ]
    if (IMAGES / "backtotop.png").is_file():
        lines.append(
            "#backtotop{background-image:url(../images/backtotop.png)!important;}"
        )
    if (IMAGES / "arrows-ffffff.png").is_file():
        lines.append(
            ".sf-sub-indicator{background-image:url(../images/arrows-ffffff.png)!important;}"
        )
    program = [
        ("program-tid.png", "th.views-field.views-field-field-tidspunkt-kl-"),
        ("program-arrangement.png", "th.views-field.views-field-field-lenke-til-omtale"),
        ("program-dag.gif", "th.views-field.views-field-field-dato"),
        ("program-sted.png", "th.views-field.views-field-field-sted"),
    ]
    for fname, sel in program:
        if (IMAGES / fname).is_file():
            lines.append(
                f"{sel}{{background-image:url(../images/{fname})!important;color:transparent;}}"
            )
    return "\n".join(lines) + "\n"


def curl_download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(
        ["curl", "-fsSL", "--max-time", "60", "-o", str(dest), url],
        capture_output=True,
    )
    return r.returncode == 0 and dest.is_file() and dest.stat().st_size > 200


def fetch_assets() -> int:
    ok = 0
    for path, local_name in DOWNLOADS:
        dest = IMAGES / local_name
        if dest.is_file() and dest.stat().st_size > 200:
            continue
        path_enc = path if "%" in path else quote(path, safe="/%")
        url = WB_IM + path_enc
        if curl_download(url, dest):
            print(f"  fetched: {local_name}")
            ok += 1
        else:
            print(f"  miss: {local_name} ({url})", file=sys.stderr)
    return ok


def strip_tracking(html: str) -> str:
    html = re.sub(
        r'<!-- AddThis Follow BEGIN -->.*?<!-- AddThis Follow END -->\s*',
        "",
        html,
        flags=re.DOTALL,
    )
    html = re.sub(
        r'<div class="addthis_toolbox[^"]*"[^>]*>.*?</div>\s*',
        "",
        html,
        flags=re.DOTALL,
    )
    html = re.sub(
        r'<script type="text/javascript" src="http://s7\.addthis\.com[^"]*"></script>\s*',
        "",
        html,
    )
    html = re.sub(
        r"<div class=\"region region-page-bottom\"><div class=\"region-inner clearfix\">"
        r".*?</noscript></div></div>\s*",
        "",
        html,
        flags=re.DOTALL,
    )
    html = re.sub(
        r"<script>window\.google_analytics_uacct\s*=\s*\"[^\"]+\";\s*</script>\s*",
        "",
        html,
    )
    return html


def remove_empty_scripts(html: str) -> str:
    for path in ROOT.glob("js/*.js"):
        if path.stat().st_size < 8:
            name = path.name
            html = re.sub(
                rf'<script src="js/{re.escape(name)}"></script>\s*',
                "",
                html,
            )
    return html


def ensure_mirror_fixes_link(html: str) -> str:
    if "mirror-fixes.css" in html:
        return html
    return html.replace(
        '<link href="css/roboto-condensed.css"',
        '<link href="css/mirror-fixes.css" rel="stylesheet" type="text/css"/>\n<link href="css/roboto-condensed.css"',
        1,
    )


def ensure_stylesheets(html: str) -> str:
    """Inject missing local Drupal CSS bundles (theme was only on some captures)."""
    insert_before = re.search(r"<title>", html)
    anchor = insert_before.start() if insert_before else None
    for href, media in REQUIRED_STYLESHEETS:
        if href in html or not (ROOT / href).is_file():
            continue
        tag = f'<link type="text/css" rel="stylesheet" href="{href}" media="{media}"/>\n'
        if anchor is not None:
            html = html[:anchor] + tag + html[anchor:]
            anchor += len(tag)
        else:
            html = tag + html

    i3path = ROOT / RESPONSIVE_CSS
    if i3path.is_file() and i3path.stat().st_size < 50:
        html = re.sub(
            rf'<link[^>]+href="{re.escape(RESPONSIVE_CSS)}"[^>]*/>\s*',
            "",
            html,
            flags=re.IGNORECASE,
        )
    return html


def restore_missing_css() -> None:
    """Re-fetch truncated responsive CSS from Wayback when missing."""
    dest = CSS / Path(RESPONSIVE_CSS).name
    if dest.is_file() and dest.stat().st_size > 200:
        return
    path = "/sites/default/files/css/css_I3dax2qmoTi2rjzlTB1gRL0_MiG7W-aHpje8SaC8k5w.css"
    url = WB_IM + path
    if curl_download(url, dest):
        print(f"  restored: {dest.name}")
    else:
        print(f"  miss css: {dest.name}", file=sys.stderr)


def fix_remote_phono_assets(html: str) -> str:
    """Map remaining phonofestivalen.no asset URLs to local files when possible."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from localize_links import resolve_basename_asset  # type: ignore

    def repl(m: re.Match[str]) -> str:
        attr, q, url = m.group(1), m.group(2), m.group(3)
        local = resolve_basename_asset(url)
        if local and (ROOT / local).is_file():
            return f"{attr}={q}{local}{q}"
        return m.group(0)

    html = re.sub(
        r'(src|data-src)=(["\'])([^"\']*(?:phonofestivalen\.no|sites/default/files)[^"\']*)\2',
        repl,
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'data-src="http://www\.phonofestivalen\.no[^"]*simen[^"]*"',
        'data-src="images/Hubba2.jpg"',
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'(<img[^>]+class="image-style-galleri-front-bilde"[^>]+src=")http://www\.phonofestivalen\.no[^"]+(")',
        r"\1images/warmup.gif\2",
        html,
    )
    html = re.sub(
        r'(<img[^>]+class="image-style-siste-nytt[^"]*"[^>]+src=")http://www\.phonofestivalen\.no[^"]+(")',
        r"\1images/Hubba2.jpg\2",
        html,
    )
    return html


HOME_PAGE = "Phonofestivalen 2013 _ 12 - 14 September, Bergen.html"


def fix_home_meta(html: str) -> str:
    if "views_slideshow_cycle_main_slideshow-block" not in html:
        return html
    html = re.sub(
        r'<meta property="og:image" content="http://www\.phonofestivalen\.no[^"]+"',
        '<meta property="og:image" content="images/1260pix_topp_Web1_1.png"',
        html,
    )
    html = re.sub(
        r'<link rel="image_src" href="[^"]+"',
        f'<link rel="image_src" href="{HOME_PAGE}"',
        html,
        count=1,
    )
    html = re.sub(
        r'<meta property="og:email" content="[^"]+"',
        '<meta property="og:email" content="leder@phonofestivalen.no"',
        html,
        count=1,
    )
    html = re.sub(
        r'<meta name="keywords" content="[^"]+"',
        '<meta name="keywords" content="phonofestivalen, festival bergen"',
        html,
        count=1,
    )
    return html


def fix_picture_data_src(html: str) -> str:
    """Map or drop Drupal Picture module data-src URLs (noscript fallback remains)."""
    sys.path.insert(0, str(ROOT / "scripts"))
    from localize_links import resolve_basename_asset  # type: ignore

    def repl(m: re.Match[str]) -> str:
        url = m.group(1)
        if "phonofestivalen" not in url.lower():
            return m.group(0)
        local = resolve_basename_asset(url)
        if local and (ROOT / local).is_file():
            return f' data-src="{local}"'
        return ""

    return re.sub(
        r'\s*data-src="([^"]*phonofestivalen[^"]*)"',
        repl,
        html,
        flags=re.IGNORECASE,
    )


def strip_home_article_images(html: str) -> str:
    """Front page news listings: text only (no article thumbnails)."""
    if "block-siste-nytt-block" not in html:
        return html
    html = re.sub(
        r'<div id="latest-news-img">\s*<a[\s\S]*?</a>\s*</div>',
        '<div id="latest-news-img"></div>',
        html,
        count=1,
    )
    html = re.sub(
        r'<div id="older-post-img">\s*<a[\s\S]*?</a>\s*</div>',
        '<div id="older-post-img"></div>',
        html,
    )
    return html


def fix_artist_bombino_tile(html: str) -> str:
    """Artist sidebar: Bombino tile uses images/Bombino.gif (not bombino1.gif)."""
    gif = "images/Bombino.gif"
    if not (ROOT / gif).is_file():
        return html

    def repl(m: re.Match[str]) -> str:
        attrs = (
            f'src="{gif}" onmouseover="this.src=\'{gif}\'" '
            f'onmouseout="this.src=\'{gif}\'"'
        )
        return f"{m.group(1)} {attrs}{m.group(2)}"

    return re.sub(
        r'(<div id="bombino"[^>]*>.*?<img)\s[^>]+(/?>)',
        repl,
        html,
        count=1,
        flags=re.DOTALL | re.IGNORECASE,
    )


def fix_home_slideshow(html: str) -> str:
    if "views_slideshow_cycle_main_slideshow-block" not in html:
        return html
    for i, img in enumerate(HOME_SLIDESHOW):
        if not (ROOT / img).is_file():
            continue
        html = re.sub(
            rf'(id="views_slideshow_cycle_div_slideshow-block_{i}"[^>]*>.*?'
            rf'field-slideshow-bilde[^>]*>.*?src=")images/[^"]+(")',
            rf"\1{img}\2",
            html,
            count=1,
            flags=re.DOTALL,
        )
    return html


def fix_js_aggregates() -> int:
    """Repair Drupal JS bundles after Wayback unwrap (stray closing brace)."""
    try:
        from strip_wayback import fix_stray_wombat_brace
    except ImportError:
        sys.path.insert(0, str(ROOT / "scripts"))
        from strip_wayback import fix_stray_wombat_brace  # type: ignore

    fixed = 0
    for path in sorted((ROOT / "js").glob("js_*.js")):
        if path.stat().st_size < 8:
            continue
        raw = path.read_text(encoding="utf-8")
        new = fix_stray_wombat_brace(raw)
        if new != raw:
            path.write_text(new, encoding="utf-8")
            print(f"  fixed js: {path.name}")
            fixed += 1
    return fixed


def fix_placeholder_images(html: str) -> str:
    html = fix_artist_bombino_tile(html)
    html = fix_home_slideshow(html)
    html = fix_remote_phono_assets(html)
    html = fix_picture_data_src(html)
    html = fix_home_meta(html)

    for title, img in TITLE_TO_IMAGE.items():
        if not (ROOT / img).is_file():
            img = TITLE_FALLBACKS.get(title, img)
        if not (ROOT / img).is_file():
            continue
        html = re.sub(
            rf'(<img[^>]+title="{re.escape(title)}"[^>]+src=")images/1260pix_topp_Web1_1\.png(")',
            rf"\1{img}\2",
            html,
        )
        html = re.sub(
            rf'(<img[^>]+src=")images/1260pix_topp_Web1_1\.png("[^>]+title="{re.escape(title)}")',
            rf"\1{img}\2",
            html,
        )
        html = re.sub(
            rf'(<img[^>]+title="{re.escape(title)}"[^>]+src=")http://www\.phonofestivalen\.no[^"]+(")',
            rf"\1{img}\2",
            html,
        )
        html = re.sub(
            rf'(<img[^>]+src=")http://www\.phonofestivalen\.no[^"]+("[^>]+title="{re.escape(title)}")',
            rf"\1{img}\2",
            html,
        )

    om_head = "images/omphono.png" if (IMAGES / "omphono.png").is_file() else "images/sistenytt.png"
    if (ROOT / om_head).is_file():
        html = re.sub(
            r'(<table[^>]*850px[^>]*>.*?<img alt="" src=")images/1260pix_topp_Web1_1\.png(" style="width: 350px)',
            rf"\1{om_head}\2",
            html,
            count=1,
            flags=re.DOTALL,
        )
    om_body = "images/phono-3.jpg" if (IMAGES / "phono-3.jpg").is_file() else "images/Web-banner1.jpg"
    if (ROOT / om_body).is_file():
        html = re.sub(
            r'(<img alt="" src=")images/1260pix_topp_Web1_1\.png(" style="width: 850px; height: 283px;")',
            rf"\1{om_body}\2",
            html,
            count=1,
        )

    if (IMAGES / "twitter.png").is_file():
        html = re.sub(
            r'(class="service-links-twitter"[^>]*>.*?src=")images/1260pix_topp_Web1_1\.png(")',
            r"\1images/twitter.png\2",
            html,
            flags=re.DOTALL,
        )

    pal = "images/Pal-og-hans.gif" if (IMAGES / "Pal-og-hans.gif").is_file() else "images/bombino.gif"
    if (ROOT / pal).is_file():
        def pal_img(m: re.Match[str]) -> str:
            attrs = f'src="{pal}" onmouseover="this.src=\'{pal}\'" onmouseout="this.src=\'{pal}\'"'
            return f"{m.group(1)} {attrs}{m.group(2)}"

        html = re.sub(
            r'(<div id="paal"[^>]*>\s*<a[^>]*><img)\s[^>]+(/?>)',
            pal_img,
            html,
            count=1,
            flags=re.DOTALL,
        )

    if (IMAGES / "Cold-Mailman-omtale.gif").is_file():
        html = re.sub(
            r'class="image-style-omtale-bilde" src="images/Cold-Mailman\.gif"',
            'class="image-style-omtale-bilde" src="images/Cold-Mailman-omtale.gif"',
            html,
        )

    html = strip_home_article_images(html)
    return html


def fix_vimeo(html: str) -> str:
    def repl(block: re.Match[str]) -> str:
        clip = block.group(1)
        return (
            f'<div class="media-vimeo-preview-wrapper">'
            f'<iframe src="https://player.vimeo.com/video/{clip}" width="480" height="360" '
            f'frameborder="0" allow="autoplay; fullscreen; picture-in-picture" allowfullscreen></iframe>'
            f"</div>"
        )

    html = re.sub(
        r"<object[^>]*>.*?clip_id=(\d+).*?</object>",
        repl,
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return html


def fix_broken_theme_css() -> None:
    path = CSS / "css_okuWAPrAhr1SWnWa9l6yAX1t5EsonQH6MHy-370IFw4.css"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    text = text.replace(
        "url(Phonofestivalen 2013 _ 12 - 14 September, Bergen.html)",
        "url(none)",
    )
    text = text.replace("color:transparent;}}td", "color:transparent;}td")
    path.write_text(text, encoding="utf-8")


def process_html_files() -> int:
    changed = 0
    for path in sorted(ROOT.glob("Phonofestivalen*.html")):
        raw = path.read_text(encoding="utf-8")
        new = raw
        new = strip_tracking(new)
        new = remove_empty_scripts(new)
        new = ensure_stylesheets(new)
        new = fix_placeholder_images(new)
        if "Cold Mailman" in path.name:
            new = fix_vimeo(new)
        new = ensure_mirror_fixes_link(new)
        if new != raw:
            path.write_text(new, encoding="utf-8")
            print(f"  updated html: {path.name}")
            changed += 1
    return changed


def main() -> int:
    if "--fetch" in sys.argv:
        print("Fetching assets from Wayback...")
        fetch_assets()
        restore_missing_css()
    else:
        print("Skipping Wayback fetch (use --fetch to try downloading missing assets).")
        restore_missing_css()

    (CSS / "mirror-fixes.css").write_text(build_mirror_fixes_css(), encoding="utf-8")
    print("Wrote css/mirror-fixes.css")

    fix_broken_theme_css()
    print("Fixed broken program background URLs in theme CSS")

    njs = fix_js_aggregates()
    if njs:
        print(f"Repaired {njs} JS aggregate(s)")

    print("Cleaning HTML...")
    n = process_html_files()
    print(f"Done ({n} HTML file(s) touched).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
