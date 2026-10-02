import io

from pypdf import PdfReader

from backend.services.pdf import tables_pdf
from tests.conftest import add_user, sign_in


def pdf_text(content: bytes) -> tuple[int, str]:
    reader = PdfReader(io.BytesIO(content))
    return len(reader.pages), "\n".join(page.extract_text() for page in reader.pages)


def test_plan_report_pdf_has_figures_chart_and_tables(admin):
    run = admin.post("/api/runs").json()
    response = admin.get("/api/exports/run/report?format=pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].endswith('.pdf"')
    pages, text = pdf_text(response.content)
    assert pages >= 2
    assert run["site_name"] in text
    assert "Saved this week" in text and "Daily energy cost" in text and "Machine schedule" in text
    assert f"€{run['summary']['savings_eur']:,.0f}" in text
    assert "Run-as-needed" in text and "GridShift plan" in text


def test_every_run_export_works_as_pdf(admin):
    admin.post("/api/runs")
    for name in ("summary", "daily", "schedule", "baseline-schedule", "hourly", "baseline-hourly", "machines"):
        response = admin.get(f"/api/exports/run/{name}?format=pdf")
        assert response.status_code == 200, name
        assert response.content.startswith(b"%PDF")


def test_hourly_pdf_lists_all_hours(admin):
    admin.post("/api/runs")
    pages, text = pdf_text(admin.get("/api/exports/run/hourly?format=pdf").content)
    assert pages >= 4
    assert text.count(":00") >= 168


def test_audit_and_users_pdf(admin, settings):
    add_user(settings, "op@example.com", "viewer")
    sign_in(settings, "op@example.com")
    _, audit = pdf_text(admin.get("/api/exports/audit?format=pdf&category=auth").content)
    assert "GridShift audit trail" in audit and "Filters: category=auth" in audit and "op@example.com" in audit
    _, users = pdf_text(admin.get("/api/exports/users?format=pdf").content)
    assert "op@example.com" in users and "admin@example.com" in users


def test_pdf_escapes_markup_and_handles_empty_tables():
    content = tables_pdf("Edge <cases> & more", [("Rows", [{"note": "<b>not bold</b> & <script>", "value": 1.5}]), ("Empty", [])])
    _, text = pdf_text(content)
    assert "<b>not bold</b> & <script>" in text
    assert "No rows." in text


def test_pdf_export_is_audited(admin):
    admin.post("/api/runs")
    admin.get("/api/exports/run/report?format=pdf")
    entry = admin.get("/api/audit", params={"action": "export.download"}).json()["entries"][0]
    assert entry["detail"]["format"] == "pdf" and entry["detail"]["export"] == "report"
