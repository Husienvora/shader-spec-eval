"""Render the Markdown research paper to PDF with headless Chromium."""

from __future__ import annotations

import argparse
from pathlib import Path

import markdown
from playwright.sync_api import sync_playwright

STYLE = """
@page { size: A4; margin: 19mm 18mm 20mm; }
* { box-sizing: border-box; }
body {
  color: #171717;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 10.2pt;
  line-height: 1.48;
  margin: 0 auto;
  max-width: 178mm;
}
h1, h2, h3 { color: #111827; font-family: Arial, Helvetica, sans-serif; }
h1 { font-size: 23pt; line-height: 1.15; margin: 0 0 10mm; }
h2 {
  border-bottom: 0.5pt solid #cbd5e1;
  font-size: 15pt;
  margin: 8mm 0 3mm;
  padding-bottom: 1.2mm;
  break-after: avoid;
}
h3 { font-size: 11.5pt; margin: 5mm 0 2mm; break-after: avoid; }
p { margin: 0 0 3mm; text-align: justify; }
blockquote {
  background: #f8fafc;
  border-left: 3px solid #64748b;
  color: #334155;
  margin: 4mm 0 6mm;
  padding: 3mm 4mm;
}
blockquote p { margin: 0; text-align: left; }
table { border-collapse: collapse; font-size: 8.6pt; margin: 4mm 0 6mm; width: 100%; }
th, td { border: 0.5pt solid #cbd5e1; padding: 1.6mm 2mm; vertical-align: top; }
th { background: #eef2ff; font-family: Arial, Helvetica, sans-serif; text-align: left; }
tr { break-inside: avoid; }
code { background: #f1f5f9; border-radius: 2px; font-size: 0.9em; padding: 0.2mm 0.7mm; }
a { color: #1d4ed8; text-decoration: none; }
ol, ul { margin: 2mm 0 4mm; padding-left: 6mm; }
li { margin-bottom: 1mm; }
strong { color: #111827; }
"""


def render(source: Path, output: Path) -> None:
    body = markdown.markdown(
        source.read_text(encoding="utf-8"),
        extensions=["tables", "fenced_code", "sane_lists"],
    )
    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{STYLE}</style></head><body>{body}</body></html>"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_content(html, wait_until="load")
        page.pdf(
            path=str(output),
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template="<span></span>",
            footer_template=(
                "<div style='font:8px Arial;color:#64748b;width:100%;"
                "text-align:center'><span class='pageNumber'></span></div>"
            ),
            margin={"top": "19mm", "right": "18mm", "bottom": "20mm", "left": "18mm"},
        )
        browser.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, nargs="?", default=Path("paper/paper.md"))
    parser.add_argument("output", type=Path, nargs="?", default=Path("paper/paper.pdf"))
    args = parser.parse_args()
    render(args.source.resolve(), args.output.resolve())
    print(args.output.resolve())


if __name__ == "__main__":
    main()
