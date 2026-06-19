#!/usr/bin/env python3
# Copyright (c) 2026 Lark Technologies Pte. Ltd.
# SPDX-License-Identifier: MIT

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any


SVG_INPUT_DIR = Path("04-svg/prepared")
PREVIEW_OUTPUT_DIR = Path("05-preview")
PREVIEW_HTML_NAME = "preview.html"
PREVIEW_MANIFEST_NAME = "preview-manifest.json"
XML_DECL_RE = re.compile(r"^\s*<\?xml\b[^>]*\?>", re.IGNORECASE)
DOCTYPE_RE = re.compile(r"^\s*<!DOCTYPE\b[^>]*>", re.IGNORECASE)


class SVGlidePreviewError(ValueError):
    pass


def relpath(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def normalize_inline_svg(text: str) -> str:
    out = XML_DECL_RE.sub("", text.strip())
    out = DOCTYPE_RE.sub("", out.strip())
    return out.strip()


def collect_svg_paths(project: Path) -> list[Path]:
    return sorted((project / SVG_INPUT_DIR).glob("*.svg"))


def build_html(project: Path, pages: list[dict[str, Any]]) -> str:
    nav_links = "\n".join(
        f'          <a href="#page-{page["page"]}">{page["page"]}</a>' for page in pages
    )
    sections: list[str] = []
    total = len(pages)
    for page in pages:
        page_no = page["page"]
        previous_link = f'<a href="#page-{page_no - 1}">Previous</a>' if page_no > 1 else "<span>Previous</span>"
        next_link = f'<a href="#page-{page_no + 1}">Next</a>' if page_no < total else "<span>Next</span>"
        source = html.escape(page["source_path"])
        sections.append(
            f"""      <section class="slide-page" id="page-{page_no}">
        <header class="slide-header">
          <div>
            <strong>Page {page_no} of {total}</strong>
            <span>Source path: {source}</span>
          </div>
          <div class="pager">{previous_link}{next_link}</div>
        </header>
        <div class="slide-frame">
{page["svg"]}
        </div>
      </section>"""
        )

    body = "\n".join(sections)
    project_label = html.escape(relpath(project, project.parent))
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>SVGlide Preview</title>
    <style>
      :root {{
        color-scheme: light;
        --bg: #f3f5f7;
        --panel: #ffffff;
        --text: #17202a;
        --muted: #627183;
        --line: #d7dde5;
        --accent: #2364aa;
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: var(--bg);
        color: var(--text);
        font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }}
      .topbar {{
        position: sticky;
        top: 0;
        z-index: 10;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        padding: 12px 20px;
        background: rgba(255, 255, 255, 0.96);
        border-bottom: 1px solid var(--line);
      }}
      .topbar h1 {{
        margin: 0;
        font-size: 16px;
        font-weight: 700;
      }}
      .topbar nav {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }}
      a {{
        color: var(--accent);
        text-decoration: none;
      }}
      a:hover {{ text-decoration: underline; }}
      main {{
        width: min(1120px, calc(100vw - 32px));
        margin: 24px auto 48px;
      }}
      .slide-page {{
        margin: 0 0 28px;
      }}
      .slide-header {{
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 16px;
        margin: 0 0 10px;
      }}
      .slide-header strong {{
        display: block;
        font-size: 15px;
      }}
      .slide-header span {{
        color: var(--muted);
        word-break: break-word;
      }}
      .pager {{
        display: flex;
        gap: 12px;
        white-space: nowrap;
      }}
      .slide-frame {{
        overflow: auto;
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 6px;
        padding: 16px;
        box-shadow: 0 8px 22px rgba(23, 32, 42, 0.08);
      }}
      .slide-frame svg {{
        display: block;
        width: min(100%, 960px);
        height: auto;
        margin: 0 auto;
      }}
    </style>
  </head>
  <body>
    <header class="topbar">
      <h1>SVGlide Preview: {project_label}</h1>
      <nav aria-label="Pages">
{nav_links}
      </nav>
    </header>
    <main>
{body}
    </main>
  </body>
</html>
"""


def build_preview(project: Path) -> dict[str, Any]:
    project = project.resolve()
    svg_paths = collect_svg_paths(project)
    if not svg_paths:
        raise SVGlidePreviewError(f"no SVG files found under {project / SVG_INPUT_DIR}")

    pages: list[dict[str, Any]] = []
    for index, path in enumerate(svg_paths, 1):
        svg_text = normalize_inline_svg(path.read_text(encoding="utf-8"))
        pages.append(
            {
                "page": index,
                "source_path": relpath(path, project),
                "source_bytes": path.stat().st_size,
                "svg": svg_text,
            }
        )

    output_dir = project / PREVIEW_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    html_path = output_dir / PREVIEW_HTML_NAME
    manifest_path = output_dir / PREVIEW_MANIFEST_NAME
    html_path.write_text(build_html(project, pages), encoding="utf-8")

    manifest = {
        "project": str(project),
        "source_dir": relpath(project / SVG_INPUT_DIR, project),
        "html_path": relpath(html_path, project),
        "manifest_path": relpath(manifest_path, project),
        "page_count": len(pages),
        "pages": [
            {
                "page": page["page"],
                "source_path": page["source_path"],
                "source_bytes": page["source_bytes"],
            }
            for page in pages
        ],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a static SVGlide HTML preview from prepared SVG pages.")
    parser.add_argument("project", help="SVGlide project directory containing 04-svg/prepared/*.svg")
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    args = parser.parse_args(argv)

    try:
        result = build_preview(Path(args.project))
    except (OSError, SVGlidePreviewError) as error:
        print(f"svglide_preview: {error}", file=sys.stderr)
        return 2

    print(json.dumps(result, ensure_ascii=False, indent=2 if args.pretty else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
