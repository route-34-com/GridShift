"""Daily planning job: run the pipeline, store the result, email it and audit it."""

import sys
from datetime import datetime, timezone

from backend.database import connect
from backend.notify.email import render_plan_email, send_email
from backend.pipeline import RunError, Sources, run_plan
from backend.services.audit import FAILURE, SYSTEM, Origin, record
from backend.settings import Settings, load_settings
from backend.sources.site import ConfigError
from backend.store import Store


def _audit(settings: Settings, actor: dict | None, origin: Origin, result: dict, trigger: str) -> None:
    with connect(settings.db_path) as db:
        if result["status"] == "failed":
            record(db, actor, "plan.run_failed", origin, outcome=FAILURE, entity="run", entity_id=result.get("id"), detail={"trigger": trigger, "error": result["error"]})
            return
        summary = result["summary"]
        record(
            db,
            actor,
            "plan.run",
            origin,
            entity="run",
            entity_id=result["id"],
            summary=f"Ran the planner: €{summary['savings_eur']:,.0f} ({summary['savings_pct']:.1%}) saved",
            detail={
                "trigger": trigger,
                "planned_cost_eur": summary["optimized"]["cost_eur"],
                "baseline_cost_eur": summary["baseline"]["cost_eur"],
                "savings_eur": summary["savings_eur"],
                "sources": result["sources"],
                "alerts": [a["message"] for a in result["alerts"]],
            },
        )
        status = result["email"]["status"]
        if status == "sent":
            record(db, actor, "email.plan_sent", origin, entity="run", entity_id=result["id"], detail={"to": result["email"]["recipients"], "subject": result["email"].get("subject")})
        elif status.startswith("failed"):
            record(db, actor, "email.failed", origin, outcome=FAILURE, entity="run", entity_id=result["id"], detail={"purpose": "daily plan", "to": result["email"]["recipients"], "error": status})


def execute(
    settings: Settings,
    store: Store,
    now: datetime | None = None,
    sources: Sources | None = None,
    email: bool = True,
    actor: dict | None = None,
    origin: Origin = SYSTEM,
) -> dict:
    """Run one planning cycle, record failures, send the plan email and write the audit entry."""
    now = now or datetime.now(timezone.utc)
    trigger = "scheduled" if actor is None else "manual"
    try:
        payload = run_plan(settings, store, now, sources)
    except (RunError, ConfigError, ValueError) as exc:
        failure = {"created_at": now.isoformat(), "horizon_start": "", "status": "failed", "error": str(exc)}
        store.save_run(failure)
        _audit(settings, actor, origin, failure, trigger)
        return failure
    if email:
        subject, html = render_plan_email(payload)
        payload["email"]["status"] = send_email(settings.smtp, payload["email"]["recipients"], subject, html)
        payload["email"]["subject"] = subject
    else:
        payload["email"]["status"] = "skipped"
    payload["triggered_by"] = actor["email"] if actor else "scheduler"
    store.update_run(payload)
    _audit(settings, actor, origin, payload, trigger)
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
