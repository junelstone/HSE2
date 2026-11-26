"""Rules for corrective actions raised by non-conformities."""

from __future__ import annotations

from datetime import date, timedelta

from . import scoring

# Days given to close an action when the inspector leaves the due date empty.
DEFAULT_DAYS = {"high": 7, "medium": 30, "low": 90}


def default_due(priority: str | None, today: date | None = None) -> str:
    days = DEFAULT_DAYS.get(priority or "medium", DEFAULT_DAYS["medium"])
    return ((today or date.today()) + timedelta(days=days)).isoformat()


def missing_action_fields(sections, results: dict) -> list:
    """Non-conform items whose corrective action or owner is empty, in checklist order."""
    missing = []
    for item in (i for s in sections for i in s.items):
        res = results.get(item.id) or {}
        if res.get("status") != scoring.NON_CONFORM:
            continue
        if not (res.get("action") or "").strip() or not (res.get("owner") or "").strip():
            missing.append(item)
    return missing


def fill_default_dues(sections, results: dict, today: date | None = None) -> None:
    """Give every non-conformity without a due date one based on its priority."""
    for item in (i for s in sections for i in s.items):
        res = results.get(item.id) or {}
        if res.get("status") == scoring.NON_CONFORM and not res.get("due"):
            res["due"] = default_due(res.get("priority"), today)
