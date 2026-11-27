"""Convertit FERMIA.md en FERMIA.docx (titres, listes, tableaux, code)."""
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

ROOT = Path(__file__).resolve().parent
MD = ROOT / "FERMIA.md"
OUT = ROOT / "FERMIA.docx"


def set_run_font(run, name="Calibri", size=11, bold=False, italic=False, color=None, code=False):
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(9 if code else size)
    run.font.name = "Consolas" if code else name
    r = run._element.get_or_add_rPr()
    rFonts = r.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        r.append(rFonts)
    font = "Consolas" if code else name
    rFonts.set(qn("w:ascii"), font)
    rFonts.set(qn("w:hAnsi"), font)
    if color:
        run.font.color.rgb = color


def add_formatted(paragraph, text, size=11):
    """Interprète **gras** et `code` dans une ligne."""
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("**", i):
            j = text.find("**", i + 2)
            if j > i:
                run = paragraph.add_run(text[i + 2 : j])
                set_run_font(run, size=size, bold=True)
                i = j + 2
                continue
        if text[i] == "`":
            j = text.find("`", i + 1)
            if j > i:
                run = paragraph.add_run(text[i + 1 : j])
                set_run_font(run, size=size, code=True, color=RGBColor(0x33, 0x33, 0x33))
                i = j + 1
                continue
        j = n
        for tok in ("**", "`"):
            k = text.find(tok, i + 1)
            if k != -1:
                j = min(j, k)
        run = paragraph.add_run(text[i:j])
        set_run_font(run, size=size)
        i = j


def shade_cell(cell, hex_color):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def add_table(doc, rows):
    if not rows:
        return
    cols = max(len(r) for r in rows)
    table = doc.add_table(rows=len(rows), cols=cols)
    table.style = "Table Grid"
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.rows[i].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            add_formatted(p, val.strip(), size=10)
            if i == 0:
                shade_cell(cell, "1F4E79")
                for run in p.runs:
                    run.bold = True
                    run.font.color.rgb = RGBColor(255, 255, 255)
                    run.font.size = Pt(10)
    doc.add_paragraph()


def is_table_sep(line):
    s = line.strip().replace(" ", "")
    return s.startswith("|") and set(s) <= set("|:-")


def parse_md(text):
    lines = text.replace("\r\n", "\n").split("\n")
    i = 0
    blocks = []
    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            chunk = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                chunk.append(lines[i])
                i += 1
            i += 1
            blocks.append(("code", "\n".join(chunk)))
            continue
        if line.strip().startswith("|") and i + 1 < len(lines) and is_table_sep(lines[i + 1]):
            rows = [[c.strip() for c in line.strip().strip("|").split("|")]]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|") and not is_table_sep(lines[i]):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            blocks.append(("table", rows))
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            blocks.append(("h", level, line[level:].strip()))
            i += 1
            continue
        if line.strip() in ("---", "***"):
            blocks.append(("hr",))
            i += 1
            continue
        if line.lstrip().startswith("- [ ]") or line.lstrip().startswith("- [x]"):
            blocks.append(("check", line.lstrip()[5:].strip()))
            i += 1
            continue
        if line.lstrip().startswith("- "):
            blocks.append(("li", line.lstrip()[2:].strip()))
            i += 1
            continue
        if line.strip() == "":
            blocks.append(("blank",))
            i += 1
            continue
        blocks.append(("p", line.rstrip()))
        i += 1
    return blocks


def main():
    doc = Document()
    for s in doc.sections:
        s.top_margin = Inches(0.7)
        s.bottom_margin = Inches(0.7)
        s.left_margin = Inches(0.8)
        s.right_margin = Inches(0.8)

    merged = []
    for b in parse_md(MD.read_text(encoding="utf-8")):
        if merged and b[0] == "p" and merged[-1][0] == "p":
            merged[-1] = ("p", merged[-1][1] + " " + b[1])
        else:
            merged.append(b)

    for b in merged:
        kind = b[0]
        if kind == "h":
            level, title = b[1], b[2]
            p = doc.add_heading(title.replace("**", ""), level=min(level, 4))
            for run in p.runs:
                run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
        elif kind == "p":
            p = doc.add_paragraph()
            add_formatted(p, b[1])
        elif kind == "li":
            p = doc.add_paragraph(style="List Bullet")
            add_formatted(p, b[1])
        elif kind == "check":
            p = doc.add_paragraph(style="List Bullet")
            add_formatted(p, "☐ " + b[1])
        elif kind == "code":
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.2)
            run = p.add_run(b[1])
            set_run_font(run, code=True, size=9, color=RGBColor(0x22, 0x22, 0x22))
            pPr = p._p.get_or_add_pPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:fill"), "F4F4F4")
            shd.set(qn("w:val"), "clear")
            pPr.append(shd)
        elif kind == "table":
            add_table(doc, b[1])
        elif kind == "hr":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER

    img = ROOT / "visuels" / "l298n-branchement-fermia.jpg"
    if img.exists():
        doc.add_heading("Schéma L298N (étape 1 jumpers + étape 6 alim)", level=2)
        doc.add_picture(str(img), width=Inches(6.3))

    doc.save(OUT)
    print(f"OK -> {OUT} ({OUT.stat().st_size} octets)")


if __name__ == "__main__":
    main()
