"""PDF rendering: the designed plan report and plain table documents."""

import io
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.shapes import Drawing
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from backend.planner.model import LOCAL_TZ
from backend.services.labels import header, local

BRAND = colors.HexColor("#0F3D2E")
BRAND_SOFT = colors.HexColor("#E3EFE9")
MUTED = colors.HexColor("#55645D")
BORDER = colors.HexColor("#DFE5E2")
BASELINE = colors.HexColor("#94A3B8")
ZEBRA = colors.HexColor("#F6F8F7")
PAGE = landscape(A4)
MARGIN = 14 * mm
WIDTH = PAGE[0] - 2 * MARGIN

TITLE = ParagraphStyle("title", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=BRAND)
SUBTITLE = ParagraphStyle("subtitle", fontName="Helvetica", fontSize=9.5, leading=13, textColor=MUTED)
HEADING = ParagraphStyle("heading", fontName="Helvetica-Bold", fontSize=12, leading=16, textColor=BRAND, spaceBefore=10, spaceAfter=6)
BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.HexColor("#142019"))
CELL = ParagraphStyle("cell", parent=BODY, fontSize=7.5, leading=9.5)
HEAD_CELL = ParagraphStyle("head", parent=CELL, fontName="Helvetica-Bold", textColor=colors.white)
NUM_CELL = ParagraphStyle("num", parent=CELL, alignment=TA_RIGHT)
KPI_LABEL = ParagraphStyle("kpil", fontName="Helvetica", fontSize=8, leading=10, textColor=MUTED)
KPI_VALUE = ParagraphStyle("kpiv", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=colors.HexColor("#142019"))
KPI_HINT = ParagraphStyle("kpih", fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=MUTED)


def eur(value: float) -> str:
    """Return a euro amount for print."""
    return f"€{value:,.0f}" if abs(value) >= 100 else f"€{value:,.2f}"


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:,.2f}".rstrip("0").rstrip(".") if abs(value) < 1e9 else str(value)
    return str(value)


def _footer(title: str):
    stamp = datetime.now(LOCAL_TZ).strftime("%d %b %Y, %H:%M")

    def draw(canvas, doc) -> None:
        canvas.saveState()
        canvas.setStrokeColor(BORDER)
        canvas.line(MARGIN, 10 * mm, PAGE[0] - MARGIN, 10 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 6.5 * mm, f"GridShift · {title} · generated {stamp}")
        canvas.drawRightString(PAGE[0] - MARGIN, 6.5 * mm, f"Page {doc.page}")
        canvas.restoreState()

    return draw


def _document(buffer: io.BytesIO, title: str) -> SimpleDocTemplate:
    return SimpleDocTemplate(buffer, pagesize=PAGE, leftMargin=MARGIN, rightMargin=MARGIN, topMargin=MARGIN, bottomMargin=16 * mm, title=title, author="GridShift")


CHAR = 4.3
PAD = 9


def column_widths(titles: list[str], cells: list[list[str]]) -> list[float]:
    """Give each column room for its longest word, then share the rest by typical text length."""
    minimum, extra = [], []
    for title, values in zip(titles, cells):
        title_word = max((len(w) for w in title.split()), default=4)
        value_word = max((len(w) for text in values for w in text.split()), default=1)
        lengths = sorted(len(v) for v in values) or [0]
        typical = lengths[max(0, int(len(lengths) * 0.9) - 1)]
        floor = max(min(title_word, 20) * CHAR * 1.15, min(value_word, 28) * CHAR) + PAD
        minimum.append(floor)
        extra.append(max(0.0, min(typical, 70) * CHAR + PAD - floor))
    spare = WIDTH - sum(minimum)
    if spare <= 0:
        return [WIDTH * m / sum(minimum) for m in minimum]
    wanted = sum(extra)
    if wanted <= spare:
        bonus = (spare - wanted) / len(minimum)
        return [m + e + bonus for m, e in zip(minimum, extra)]
    return [m + spare * e / wanted for m, e in zip(minimum, extra)]


def data_table(rows: list[dict]) -> Table:
    """Return a styled, page-breaking table for a list of rows."""
    if not rows:
        return Table([[Paragraph("No rows.", BODY)]], colWidths=[WIDTH])
    columns = list(rows[0])
    numeric = {c for c in columns if all(isinstance(r.get(c), (int, float)) or r.get(c) in (None, "") for r in rows)}
    col_widths = column_widths([header(c) for c in columns], [[_text(r.get(c)) for r in rows[:300]] for c in columns])
    body = [[Paragraph(escape(header(c)), HEAD_CELL) for c in columns]]
    for row in rows:
        body.append([Paragraph(escape(_text(row.get(c))), NUM_CELL if c in numeric else CELL) for c in columns])
    table = Table(body, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ZEBRA]),
                ("LINEBELOW", (0, 0), (-1, -1), 0.25, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table


def tables_pdf(title: str, sheets: list[tuple[str, list[dict]]], subtitle: str = "") -> bytes:
    """Return a PDF with one titled table per sheet."""
    buffer = io.BytesIO()
    story = [Paragraph(escape(title), TITLE)]
    if subtitle:
        story.append(Paragraph(escape(subtitle), SUBTITLE))
    for name, rows in sheets:
        if len(sheets) > 1:
            story.append(Paragraph(escape(name), HEADING))
        else:
            story.append(Spacer(1, 6 * mm))
        story.append(data_table(rows))
    _document(buffer, title).build(story, onFirstPage=_footer(title), onLaterPages=_footer(title))
    return buffer.getvalue()


def _kpis(run: dict) -> Table:
    s = run["summary"]
    o, b = s["optimized"], s["baseline"]
    cards = [
        ("Saved this week", eur(s["savings_eur"]), f"{s['savings_pct']:.1%} below run-as-needed ({eur(b['cost_eur'])})"),
        ("Planned energy cost", eur(o["cost_eur"]), f"Tomorrow {eur(run['daily'][0]['cost_eur'])}"),
        ("On-site renewable share", f"{o['renewable_share']:.0%}", f"{o['renewable_used_kwh'] / 1000:,.1f} MWh solar and wind used"),
        ("CO2 avoided", f"{o['co2_avoided_kg'] / 1000:,.1f} t", "vs. buying the same energy from the grid"),
    ]
    cells = [[[Paragraph(label, KPI_LABEL), Paragraph(value, KPI_VALUE), Paragraph(escape(hint), KPI_HINT)] for label, value, hint in cards]]
    table = Table(cells, colWidths=[WIDTH / 4] * 4)
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, BORDER),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("BACKGROUND", (0, 0), (0, 0), BRAND_SOFT),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return table


def _cost_chart(run: dict) -> Drawing:
    days = run["daily"]
    drawing = Drawing(WIDTH, 62 * mm)
    chart = VerticalBarChart()
    chart.x, chart.y = 14 * mm, 12 * mm
    chart.width, chart.height = WIDTH - 60 * mm, 46 * mm
    chart.data = [[d["baseline_cost_eur"] for d in days], [d["cost_eur"] for d in days]]
    chart.categoryAxis.categoryNames = [d["label"] for d in days]
    chart.categoryAxis.labels.fontName = "Helvetica"
    chart.categoryAxis.labels.fontSize = 7.5
    chart.valueAxis.valueMin = 0
    chart.valueAxis.labels.fontName = "Helvetica"
    chart.valueAxis.labels.fontSize = 7
    chart.valueAxis.labelTextFormat = lambda v: f"€{v:,.0f}"
    chart.valueAxis.gridStrokeColor = BORDER
    chart.valueAxis.visibleGrid = True
    chart.bars[0].fillColor = BASELINE
    chart.bars[1].fillColor = BRAND
    chart.bars.strokeColor = None
    chart.barSpacing = 1.5
    chart.groupSpacing = 8
    drawing.add(chart)
    legend = Legend()
    legend.x, legend.y = WIDTH - 40 * mm, 50 * mm
    legend.fontName, legend.fontSize = "Helvetica", 8
    legend.colorNamePairs = [(BASELINE, "Run-as-needed"), (BRAND, "GridShift plan")]
    legend.alignment = "right"
    drawing.add(legend)
    return drawing


def outlook_rows(run: dict) -> list[dict]:
    """Return the 7-day outlook formatted for print."""
    return [
        {
            "day": d["label"],
            "planned": eur(d["cost_eur"]),
            "run_as_needed": eur(d["baseline_cost_eur"]),
            "avg_price": f"€{d['avg_price']:,.0f}/MWh" + ("*" if d["price_estimated"] else ""),
            "renewable": f"{d['renewable_share']:.0%}",
            "outlook": d["outlook"],
            "battery": d["battery_note"],
        }
        for d in run["daily"]
    ]


def report_pdf(run: dict, tables: dict[str, list[dict]]) -> bytes:
    """Return the designed plan report: headline figures, daily cost chart, notes, outlook, machines and schedule."""
    buffer = io.BytesIO()
    title = f"Energy plan · {run['site_name']}"
    story = [
        Paragraph(escape(title), TITLE),
        Paragraph(
            escape(f"Plan #{run['id']} · {local(run['horizon_start'])} to {local(run['horizon_end'])} (Europe/Berlin) · generated {local(run['created_at'])}"),
            SUBTITLE,
        ),
        Spacer(1, 5 * mm),
        _kpis(run),
        Paragraph("Daily energy cost", HEADING),
        _cost_chart(run),
    ]
    notes = [a["message"] for a in run["alerts"]] + run["warnings"]
    sources = ", ".join(f"{k.replace('_', ' ')}: {v}" for k, v in run["sources"].items())
    story.append(Paragraph("Notes and data sources", HEADING))
    for note in notes:
        story.append(Paragraph(f"• {escape(note)}", BODY))
    story.append(Paragraph(f"Sources — {escape(sources)}. Prices after the first published day are estimated from the weather forecast.", BODY))
    story.append(Paragraph("7-day outlook (* price estimated from the weather forecast)", HEADING))
    story.append(data_table(outlook_rows(run)))
    story.append(KeepTogether([Paragraph("Price paid per machine", HEADING), data_table(tables["machines"])]))
    story.append(Paragraph("Machine schedule", HEADING))
    story.append(data_table(tables["schedule"]))
    _document(buffer, title).build(story, onFirstPage=_footer(title), onLaterPages=_footer(title))
    return buffer.getvalue()
