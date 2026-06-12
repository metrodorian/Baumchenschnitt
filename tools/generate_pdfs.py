#!/usr/bin/env python3
"""
generate_pdfs.py — Erzeugt alle PDFs des Bäumchenschnitt-Ratgebers vollständig lokal.

  * Ein Einzel-PDF pro Kapitel  → pdfs/NN_*.pdf
  * Eine Gesamtdatei            → pdfs/Baeumchenschnitt_komplett.pdf
      - beginnt mit der Einleitung (README.md)
      - die Kapitel-Links im Inhaltsverzeichnis funktionieren als
        interne PDF-Sprungmarken
      - sauber gesetzte Seitenumbrüche (Überschrift bleibt beim Text)

Vorgehen: Markdown -> HTML (python-markdown) -> Chrome headless -> PDF.
Keine Abhängigkeit von der Live-Website, kein Deploy-Warten.
Einfach nach jeder Textänderung neu ausführen:

    python3 tools/generate_pdfs.py
    git add pdfs/ && git commit -m "PDFs aktualisiert"

Voraussetzungen: Google Chrome (macOS), Python 3, pip-Pakete: markdown, pypdf
"""
import subprocess
import sys
import tempfile
from pathlib import Path

import markdown

REPO = Path(__file__).parent.parent
OUT_DIR = REPO / "pdfs"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

CHAPTERS = [
    "01_grundprinzipien",
    "02_japanische_schnittkunst",
    "03_wildkirsche",
    "04_hasel",
    "05_ahorn",
    "06_weissdorn",
    "07_jahreskalender",
]

# ── gemeinsames Stylesheet (Bildschirm + Druck identisch) ─────────────────────
CSS = """
:root { color-scheme: light; }
body {
  font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  font-size: 11pt;
  line-height: 1.55;
  color: #1b1f23;
  max-width: 46rem;
  margin: 0 auto;
  padding: 0 1.2rem;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}
h1 { font-size: 1.9rem; line-height: 1.2; margin: 0 0 .6rem; color: #0f5132; }
h2 { font-size: 1.35rem; margin: 1.8rem 0 .6rem; color: #15592f; }
h3 { font-size: 1.1rem;  margin: 1.3rem 0 .4rem; }
h4 { font-size: 1rem;    margin: 1.1rem 0 .3rem; }
p  { margin: .55rem 0; }
a  { color: #1a7f43; text-decoration: underline; }
strong { color: #111; }
ul, ol { margin: .5rem 0 .8rem; padding-left: 1.5rem; }
li { margin: .25rem 0; }
hr { border: none; border-top: 1px solid #d7dde2; margin: 1.8rem 0; }

/* Bilder mit Bildunterschrift (![..](..) gefolgt von *kursiv*) */
img {
  max-width: 100%;
  border-radius: .35rem;
  display: block;
  margin: 1rem auto .3rem;
}
img + em, p > img ~ em { font-size: .88em; color: #57606a; }

/* Zitate / Merksatz-Kästen */
blockquote {
  margin: 1rem 0;
  padding: .6rem 1.1rem;
  background: #f3f8f4;
  border-left: 4px solid #2da160;
  border-radius: 0 .35rem .35rem 0;
}
blockquote h2 { margin-top: .2rem; font-size: 1.15rem; }
blockquote p:first-child { margin-top: 0; }
blockquote p:last-child  { margin-bottom: 0; }

/* Tabellen (Jahreskalender, Werkzeug, Bildnachweis) */
table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: .95em; }
th, td { border: 1px solid #cfd6dc; padding: .4rem .6rem; text-align: left; vertical-align: top; }
th { background: #eef3f0; }

pre {
  background: #f6f8fa;
  border: 1px solid #e1e4e8;
  border-radius: .35rem;
  padding: .8rem 1rem;
  overflow-x: auto;
  font-size: .85em;
  line-height: 1.35;
}
code { font-family: "SF Mono", Menlo, Consolas, monospace; }

/* Kapitel-Trenner in der Gesamtdatei */
.chapter { display: block; height: 0; }

@media print {
  @page { size: A4; margin: 1.8cm 2cm; }
  body { max-width: none; padding: 0; }

  /* Jedes Kapitel beginnt auf neuer Seite */
  .chapter { break-before: page; page-break-before: always; }

  /* Überschrift nie allein am Seitenende */
  h1, h2, h3, h4 { break-after: avoid; page-break-after: avoid; }
  /* Erstes Element nach Überschrift bleibt bei ihr */
  h1 + p, h2 + p, h3 + p, h4 + p,
  h1 + ul, h2 + ul, h3 + ul, h4 + ul,
  h1 + ol, h2 + ol, h3 + ol, h4 + ol,
  h2 + blockquote, h3 + blockquote {
    break-before: avoid; page-break-before: avoid;
  }
  /* Kästen/Tabellen/Code/Bilder nicht zerreissen */
  blockquote, pre, table, figure, img { break-inside: avoid; page-break-inside: avoid; }
  p { orphans: 3; widows: 3; }
  a { color: #1a7f43; }
}
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="de"><head><meta charset="utf-8">
<title>{title}</title>
<style>{css}</style>
</head><body>
{body}
</body></html>"""

MD_EXTENSIONS = ["extra", "sane_lists", "attr_list", "md_in_html"]


def md_to_html(text):
    return markdown.markdown(text, extensions=MD_EXTENSIONS, output_format="html5")


def chrome_print(html_path, pdf_path, budget=4000):
    subprocess.run(
        [
            CHROME,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            "--run-all-compositor-stages-before-draw",
            f"--virtual-time-budget={budget}",
            f"file://{html_path}",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def render_to_pdf(body_html, title, pdf_path, budget=4000):
    full = HTML_TEMPLATE.format(title=title, css=CSS, body=body_html)
    # Temp-HTML liegt im Repo-Wurzelverzeichnis, damit relative
    # Bildpfade (images/…) im file://-Kontext funktionieren.
    with tempfile.NamedTemporaryFile(
        "w", suffix=".html", dir=REPO, delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(full)
        tmp_path = tmp.name
    try:
        chrome_print(tmp_path, pdf_path, budget)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def main():
    if not Path(CHROME).exists():
        sys.exit(f"Fehler: Google Chrome nicht gefunden: {CHROME}")
    OUT_DIR.mkdir(exist_ok=True)

    # Datei-Links → Anker-Links für die Gesamtdatei
    link_map = {}
    for i, slug in enumerate(CHAPTERS, 1):
        link_map[f"({slug}.md)"] = f"(#kapitel-{i})"

    print(f"Ausgabe: {OUT_DIR}\n")

    # ── Einzel-PDFs ───────────────────────────────────────────────────────────
    for slug in CHAPTERS:
        text = (REPO / f"{slug}.md").read_text(encoding="utf-8")
        html = md_to_html(text)
        print(f"  → {slug}.pdf")
        render_to_pdf(html, slug, str(OUT_DIR / f"{slug}.pdf"))

    # ── Gesamtdatei ───────────────────────────────────────────────────────────
    print("\nErstelle Gesamtdatei …")
    parts = []

    readme = (REPO / "README.md").read_text(encoding="utf-8")
    for old, new in link_map.items():
        readme = readme.replace(old, new)
    parts.append(md_to_html(readme))

    for i, slug in enumerate(CHAPTERS, 1):
        chapter = (REPO / f"{slug}.md").read_text(encoding="utf-8")
        for old, new in link_map.items():
            chapter = chapter.replace(old, new)
        parts.append(f'<div class="chapter" id="kapitel-{i}"></div>')
        parts.append(md_to_html(chapter))

    combined = "\n".join(parts)
    combined_pdf = OUT_DIR / "Baeumchenschnitt_komplett.pdf"
    render_to_pdf(combined, "Bäumchenschnitt — Vollständige Ausgabe", str(combined_pdf), budget=10000)

    # Seitenzahl
    try:
        from pypdf import PdfReader

        n = len(PdfReader(str(combined_pdf)).pages)
        print(f"  → Baeumchenschnitt_komplett.pdf ({n} Seiten)")
    except Exception:
        print("  → Baeumchenschnitt_komplett.pdf")

    print("\nFertig. Jetzt committen:")
    print("  git add pdfs/ && git commit -m 'PDFs aktualisiert'")


if __name__ == "__main__":
    main()
