"""PDF report generation (fpdf2).

The built-in Helvetica font only supports Latin-1, so every string goes
through ``clean()`` first. That keeps French accents and replaces symbols
such as curly quotes or check boxes that crashed the first version.
"""

from __future__ import annotations

import io
from datetime import datetime

from fpdf import FPDF
from fpdf.fonts import FontFace

from . import scoring
from .i18n import t

_REPLACEMENTS = {
    "’": "'", "‘": "'", "“": '"', "”": '"', "–": "-",
    "—": "-", "…": "...", "œ": "oe", "Œ": "OE", "≥": ">=",
    "≤": "<=", "☐": "[ ]", "☑": "[x]", "•": "-", " ": " ",
    " ": " ", "€": "EUR",
}

RATING_COLOURS = {"green": (46, 160, 67), "amber": (230, 150, 0), "red": (200, 30, 30), "none": (120, 120, 120)}
STATUS_COLOURS = {scoring.CONFORM: (220, 245, 225), scoring.NON_CONFORM: (255, 220, 220),
                  scoring.NOT_APPLICABLE: (235, 235, 235)}


def clean(text) -> str:
    text = "" if text is None else str(text)
    for src, dst in _REPLACEMENTS.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", "replace").decode("latin-1")


class HSEReportPDF(FPDF):
    def __init__(self, title: str):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.report_title = clean(title)
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.cell(0, 10, self.report_title, align="C", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 8, f"Page {self.page_no()}/{{nb}}", align="C")


def _status_label(lang, status):
    return t(lang, f"status_{status}") if status in scoring.STATUSES else t(lang, "none")


def _fmt_date(iso):
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return iso or ""


def _pct(score):
    return "-" if score.percent is None else f"{score.percent:.0f} %"


def build_pdf(inspection: dict, sections: list, stage_label: str) -> bytes:
    lang = inspection.get("lang", "fr")
    results = inspection.get("results", {})
    pdf = HSEReportPDF(t(lang, "app_title"))
    pdf.alias_nb_pages()
    pdf.add_page()
    heading = FontFace(emphasis="BOLD", fill_color=(200, 220, 255))

    # Header information
    pdf.set_font("Helvetica", size=10)
    rows = [
        (t(lang, "date"), inspection.get("date", "")),
        (t(lang, "site"), inspection.get("site", "")),
        (t(lang, "installation"), inspection.get("installation", "")),
        (t(lang, "inspectors"), inspection.get("inspectors", "")),
        (t(lang, "department"), inspection.get("department", "")),
        (t(lang, "stage"), stage_label),
    ]
    with pdf.table(col_widths=(45, 145), first_row_as_headings=False) as table:
        for label, value in rows:
            row = table.row()
            row.cell(clean(label), style=FontFace(emphasis="BOLD"))
            row.cell(clean(value))
    pdf.ln(4)

    # Summary
    total = scoring.overall(sections, results)
    critical = scoring.critical_findings(sections, results)
    rate = scoring.rating(total.percent, len(critical))
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*RATING_COLOURS[rate])
    pdf.cell(0, 8, clean(f"{t(lang, 'score')} : {_pct(total)}   |   "
                         f"{t(lang, 'critical_nc')} : {len(critical)}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", size=9)
    with pdf.table(col_widths=(90, 25, 25, 25, 25), headings_style=heading, text_align="CENTER") as table:
        head = table.row()
        for h in ("", t(lang, "status_C"), t(lang, "status_NC"), t(lang, "status_NA"), t(lang, "score")):
            head.cell(clean(h))
        for section, sc in scoring.score_sections(sections, results):
            row = table.row()
            row.cell(clean(section.label(lang)), align="LEFT")
            row.cell(str(sc.conform))
            row.cell(str(sc.non_conform))
            row.cell(str(sc.not_applicable))
            row.cell(_pct(sc))
    pdf.ln(3)

    if critical:
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*RATING_COLOURS["red"])
        pdf.cell(0, 7, clean(t(lang, "critical_nc")), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.set_font("Helvetica", size=9)
        for item in critical:
            pdf.multi_cell(0, 5, clean(f"- {item.id} : {item.label(lang)}"), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    # Detailed checklist
    for section in sections:
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, clean(section.label(lang)), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=8)
        with pdf.table(col_widths=(18, 80, 18, 22, 52), headings_style=heading, text_align="LEFT") as table:
            head = table.row()
            for h in ("ID", t(lang, "item"), t(lang, "criticality"), t(lang, "status"), t(lang, "observation")):
                head.cell(clean(h))
            for item in section.items:
                res = results.get(item.id) or {}
                status = res.get("status")
                row = table.row()
                row.cell(clean(item.id))
                row.cell(clean(f"{item.label(lang)}\n{t(lang, 'ref')} {item.ref}"))
                row.cell(clean(t(lang, f"crit_{item.criticality}")))
                row.cell(clean(_status_label(lang, status)),
                         style=FontFace(fill_color=STATUS_COLOURS.get(status, (255, 255, 255))))
                row.cell(clean(res.get("observation", "")))
        pdf.ln(3)

    # Action plan
    actions = [(item, results[item.id]) for s in sections for item in s.items
               if (results.get(item.id) or {}).get("status") == scoring.NON_CONFORM]
    if actions:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, clean(t(lang, "action_plan")), new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=8)
        with pdf.table(col_widths=(18, 55, 55, 25, 20, 17), headings_style=heading, text_align="LEFT") as table:
            head = table.row()
            for h in ("ID", t(lang, "item"), t(lang, "action"), t(lang, "owner"), t(lang, "due"), t(lang, "priority")):
                head.cell(clean(h))
            for item, res in actions:
                row = table.row()
                row.cell(clean(item.id))
                row.cell(clean(item.label(lang)))
                row.cell(clean(res.get("action", "")))
                row.cell(clean(res.get("owner", "")))
                row.cell(clean(_fmt_date(res.get("due"))))
                prio = res.get("priority")
                row.cell(clean(t(lang, f"prio_{prio}") if prio else ""))

    # Photo evidence
    photos = [(item, results[item.id]["photo"]) for s in sections for item in s.items
              if (results.get(item.id) or {}).get("photo")]
    if photos:
        pdf.add_page()
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, clean("Photos"), new_x="LMARGIN", new_y="NEXT")
        for item, data in photos:
            pdf.set_font("Helvetica", size=9)
            pdf.multi_cell(0, 5, clean(f"{item.id} : {item.label(lang)}"), new_x="LMARGIN", new_y="NEXT")
            try:
                pdf.image(io.BytesIO(data), w=90)
            except Exception:  # unreadable image: note it rather than fail the report
                pdf.cell(0, 5, clean("(image illisible / unreadable image)"), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

    # Comments and signatures
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, clean(t(lang, "comments")), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 6, clean(inspection.get("comments", "")) or "-", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(12)
    pdf.cell(95, 8, clean(f"{t(lang, 'sig_inspector')} : ____________________"))
    pdf.cell(0, 8, clean(f"{t(lang, 'sig_manager')} : ____________________"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 7)
    pdf.cell(0, 6, clean(t(lang, "generated_on", when=f"{datetime.now():%d/%m/%Y %H:%M}")), new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())
