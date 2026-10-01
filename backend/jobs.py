"""Daily planning job: run the pipeline, store the result and email it."""

import sys
from datetime import datetime, timezone

from backend.notify.email import render_plan_email, send_email
from backend.pipeline import RunError, Sources, run_plan
from backend.settings import Settings, load_settings
from backend.sources.site import ConfigError
from backend.store import Store


def execute(settings: Settings, store: Store, now: datetime | None = None, sources: Sources | None = None, email: bool = True) -> dict:
    """Run one planning cycle, record failures and send the plan email."""
    now = now or datetime.now(timezone.utc)
    try:
        payload = run_plan(settings, store, now, sources)
    except (RunError, ConfigError, ValueError) as exc:
        failure = {"created_at": now.isoformat(), "horizon_start": "", "status": "failed", "error": str(exc)}
        store.save_run(failure)
        return failure
    if email:
        subject, html = render_plan_email(payload)
        payload["email"]["status"] = send_email(settings.smtp, payload["email"]["recipients"], subject, html)
        payload["email"]["subject"] = subject
    else:
        payload["email"]["status"] = "skipped"
    store.update_run(payload)
    return payload


def main() -> int:
    """Run the job from the command line."""
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    settings = load_settings()
    result = execute(settings, Store(settings.db_path))
    if result["status"] == "failed":
        print(f"Run failed: {result['error']}", file=sys.stderr)
        return 1
    summary = result["summary"]
    print(f"Run {result['id']} for {result['site_name']}: €{summary['optimized']['cost_eur']:,.2f} planned, "
          f"€{summary['savings_eur']:,.2f} ({summary['savings_pct']:.1%}) saved vs baseline. Email: {result['email']['status']}")
    for alert in result["alerts"]:
        print(f"[{alert['level']}] {alert['message']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
