"""Compliance scoring for an inspection."""

from __future__ import annotations

from dataclasses import dataclass

CONFORM = "C"
NON_CONFORM = "NC"
NOT_APPLICABLE = "NA"
STATUSES = (CONFORM, NON_CONFORM, NOT_APPLICABLE)


@dataclass
class Score:
    conform: int = 0
    non_conform: int = 0
    not_applicable: int = 0
    unanswered: int = 0

    @property
    def assessed(self) -> int:
        return self.conform + self.non_conform

    @property
    def percent(self) -> float | None:
        """Share of conform items among those that apply. None if nothing assessed."""
        if not self.assessed:
            return None
        return round(100.0 * self.conform / self.assessed, 1)

    def add(self, status: str | None) -> None:
        if status == CONFORM:
            self.conform += 1
        elif status == NON_CONFORM:
            self.non_conform += 1
        elif status == NOT_APPLICABLE:
            self.not_applicable += 1
        else:
            self.unanswered += 1


def score_items(items, results: dict) -> Score:
    """``results`` maps item id -> dict with at least a ``status`` key."""
    score = Score()
    for item in items:
        score.add((results.get(item.id) or {}).get("status"))
    return score


def score_sections(sections, results: dict) -> list:
    return [(section, score_items(section.items, results)) for section in sections]


def overall(sections, results: dict) -> Score:
    return score_items([i for s in sections for i in s.items], results)


def critical_findings(sections, results: dict) -> list:
    """Critical items marked non conform, in checklist order."""
    return [item for s in sections for item in s.items
            if item.criticality == "critical"
            and (results.get(item.id) or {}).get("status") == NON_CONFORM]


def rating(percent: float | None, n_critical: int) -> str:
    """Simple traffic-light rating: any critical finding is red."""
    if percent is None:
        return "none"
    if n_critical or percent < 70:
        return "red"
    if percent < 90:
        return "amber"
    return "green"
