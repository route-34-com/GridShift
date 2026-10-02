"""Build CSV and Excel downloads from plan runs, users and the audit trail."""

import csv
import io
from collections.abc import Callable
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from backend.planner.model import LOCAL_TZ
from backend.services.errors import AppError

FORMATS = ("csv", "xlsx")
RISKY = ("=", "+", "-", "@", "\t", "\r")
MIME = {"csv": "text/csv; charset=utf-8", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
Table = list[dict]


def local(stamp: str) -> str:
    """Return an ISO timestamp as Berlin local time text."""
    return datetime.fromisoformat(stamp).astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M")


def safe_cell(value: object) -> object:
    """Neutralise text a spreadsheet would run as a formula."""
    if isinstance(value, str) and value.startswith(RISKY):
        return "'" + value
    return value


def hourly_table(run: dict, key: str = "hourly") -> Table:
    """Return hourly flows in local time."""
    return [
        {
            "time_local": local(h["ts"]),
            "price_eur_mwh": h["price"],
            "price_source": h["price_source"],
            "solar_kw": h["solar"],
            "wind_kw": h["wind"],
            "base_load_kw": h["demand"],
            "flexible_load_kw": h["flexible"],
            "battery_charge_kw": h["charge"],
            "battery_discharge_kw": h["discharge"],
            "battery_soc_kwh": h["soc"],
            "grid_import_kw": h["grid_import"],
            "grid_export_kw": h["grid_export"],
            "curtailed_kw": h["curtail"],
            "unmet_kw": h["unmet"],
        }
        for h in run[key]
    ]


def schedule_table(run: dict, key: str = "blocks") -> Table:
    """Return machine run blocks with their reasons."""
    return [
        {
            "machine": b["machine_name"],
            "start_local": local(b["start"]),
            "end_local": local(b["end"]),
            "hours": b["hours"],
            "energy_kwh": b["energy_kwh"],
            "avg_price_eur_mwh": b["avg_price"],
            "renewable_share": b["renewable_share"],
            "reason": b["reason"].split(": ", 1)[-1],
        }
        for b in run[key]
    ]


def daily_table(run: dict) -> Table:
    """Return the per-day cost, savings and outlook."""
    return [
        {
            "date": d["date"],
            "day": d["label"],
            "planned_cost_eur": d["cost_eur"],
            "baseline_cost_eur": d["baseline_cost_eur"],
            "difference_eur": d["savings_eur"],
            "avg_price_eur_mwh": d["avg_price"],
            "price_estimated": "yes" if d["price_estimated"] else "no",
            "renewable_kwh": d["renewable_kwh"],
            "renewable_share": d["renewable_share"],
            "flexible_kwh": d["flexible_kwh"],
            "outlook": d["outlook"],
            "battery": d["battery_note"],
        }
        for d in run["daily"]
    ]


def machines_table(run: dict) -> Table:
    """Return each machine's hours and average price compared with the baseline."""
    return [
        {
            "machine": m["name"],
            "type": m["type"],
            "power_kw": m["power_kw"],
            "scheduled_hours": m.get("scheduled_hours", ""),
            "required_hours": m.get("required_hours", ""),
            "avg_price_eur_mwh": m.get("avg_price") if m.get("avg_price") is not None else "",
            "baseline_avg_price_eur_mwh": m.get("baseline_avg_price") if m.get("baseline_avg_price") is not None else "",
        }
        for m in run["machines"]
    ]


def summary_table(run: dict) -> Table:
    """Return the run's headline figures as label and value rows."""
    s = run["summary"]
    o, b = s["optimized"], s["baseline"]
    return [
        {"item": "Site", "value": run["site_name"]},
        {"item": "Plan id", "value": run["id"]},
        {"item": "Generated (local)", "value": local(run["created_at"])},
        {"item": "Horizon start (local)", "value": local(run["horizon_start"])},
        {"item": "Horizon end (local)", "value": local(run["horizon_end"])},
        {"item": "Planned cost (EUR)", "value": o["cost_eur"]},
        {"item": "Run-as-needed cost (EUR)", "value": b["cost_eur"]},
        {"item": "Savings (EUR)", "value": s["savings_eur"]},
        {"item": "Savings (%)", "value": round(s["savings_pct"] * 100, 2)},
        {"item": "Grid import (kWh)", "value": o["import_kwh"]},
        {"item": "On-site renewable used (kWh)", "value": o["renewable_used_kwh"]},
        {"item": "Renewable share (%)", "value": round(o["renewable_share"] * 100, 2)},
        {"item": "CO2 avoided (kg)", "value": o["co2_avoided_kg"]},
        {"item": "Peak grid import (kW)", "value": o["peak_import_kw"]},
        {"item": "Solver", "value": f"{run['solver']['status']} (gap {run['solver']['gap']:.2%})"},
        *({"item": f"Source: {k}", "value": v} for k, v in run["sources"].items()),
        *({"item": f"Alert ({a['level']})", "value": a["message"]} for a in run["alerts"]),
        *({"item": "Note", "value": w} for w in run["warnings"]),
    ]


RUN_TABLES: dict[str, tuple[str, Callable[[dict], Table]]] = {
    "summary": ("Summary", summary_table),
    "daily": ("Daily", daily_table),
    "schedule": ("Schedule", schedule_table),
    "baseline-schedule": ("Baseline schedule", lambda r: schedule_table(r, "baseline_blocks")),
    "hourly": ("Hourly", hourly_table),
    "baseline-hourly": ("Baseline hourly", lambda r: hourly_table(r, "baseline_hourly")),
    "machines": ("Machines", machines_table),
}
REPORT_SHEETS = ("summary", "daily", "schedule", "machines", "hourly")


def to_csv(table: Table) -> bytes:
    """Render rows as UTF-8 CSV with a BOM so Excel opens umlauts and euro signs correctly."""
    buffer = io.StringIO()
    if table:
        writer = csv.DictWriter(buffer, fieldnames=list(table[0]), lineterminator="\r\n")
        writer.writeheader()
        writer.writerows({k: safe_cell(v) for k, v in row.items()} for row in table)
    return ("﻿" + buffer.getvalue()).encode("utf-8")


UNITS = {"eur_mwh": "(€/MWh)", "eur": "(€)", "kwh": "(kWh)", "kw": "(kW)", "utc": "(UTC)", "local": "(local time)"}


def header(column: str) -> str:
    """Return a readable column title with its unit, e.g. planned_cost_eur -> Planned cost (€)."""
    for suffix, unit in UNITS.items():
        if column.endswith(f"_{suffix}"):
            return f"{column[: -len(suffix) - 1].replace('_', ' ').capitalize()} {unit}"
    return column.replace("_", " ").capitalize()


def _sheet(book: Workbook, title: str, table: Table) -> None:
    sheet = book.create_sheet(title[:31])
    if not table:
        sheet.append(["No rows"])
        return
    columns = list(table[0])
    sheet.append([header(c) for c in columns])
    for row in table:
        sheet.append([safe_cell(row.get(c)) for c in columns])
    header_fill = PatternFill("solid", fgColor="0F3D2E")
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(vertical="center")
    sheet.freeze_panes = "A2"
    for index, column in enumerate(columns, start=1):
        longest = max([len(str(column))] + [len(str(r.get(column) or "")) for r in table[:500]])
        sheet.column_dimensions[get_column_letter(index)].width = min(60, max(10, longest + 2))
    sheet.auto_filter.ref = sheet.dimensions


def to_xlsx(sheets: list[tuple[str, Table]]) -> bytes:
    """Render one or more tables as an Excel workbook."""
    book = Workbook()
    book.remove(book.active)
    for title, table in sheets:
        _sheet(book, title, table)
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()


def check_format(fmt: str) -> str:
    """Return a supported format or refuse it."""
    if fmt not in FORMATS:
        raise AppError(400, "Choose csv or xlsx.")
    return fmt


def render(sheets: list[tuple[str, Table]], fmt: str) -> bytes:
    """Return file bytes for one table as CSV or any tables as Excel."""
    if check_format(fmt) == "csv":
        if len(sheets) != 1:
            raise AppError(400, "CSV holds one table. Download the full report as Excel.")
        return to_csv(sheets[0][1])
    return to_xlsx(sheets)


def run_sheets(run: dict, name: str) -> list[tuple[str, Table]]:
    """Return the sheets for a named run export."""
    if name == "report":
        return [(RUN_TABLES[k][0], RUN_TABLES[k][1](run)) for k in REPORT_SHEETS]
    if name not in RUN_TABLES:
        raise AppError(404, f"Unknown export: {name}.")
    title, build = RUN_TABLES[name]
    return [(title, build(run))]


def filename(stem: str, fmt: str) -> str:
    """Return a dated download filename."""
    return f"gridshift-{stem}-{datetime.now(LOCAL_TZ).strftime('%Y%m%d-%H%M')}.{fmt}"
