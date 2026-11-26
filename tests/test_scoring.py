from hse_app import scoring
from hse_app.checklists import load_library


def _all(sections, status):
    return {i.id: {"status": status} for s in sections for i in s.items}


def test_percent_ignores_not_applicable():
    sc = scoring.Score(conform=3, non_conform=1, not_applicable=5)
    assert sc.percent == 75.0


def test_no_answers_gives_none():
    lib = load_library()
    sections = lib.sections_for("production")
    total = scoring.overall(sections, {})
    assert total.percent is None
    assert total.unanswered == sum(len(s.items) for s in sections)


def test_critical_findings_and_rating():
    lib = load_library()
    sections = lib.sections_for("drilling")
    results = _all(sections, scoring.CONFORM)
    assert scoring.critical_findings(sections, results) == []
    assert scoring.rating(scoring.overall(sections, results).percent, 0) == "green"
    results["DRL-WC-01"] = {"status": scoring.NON_CONFORM}
    found = scoring.critical_findings(sections, results)
    assert [i.id for i in found] == ["DRL-WC-01"]
    assert scoring.rating(scoring.overall(sections, results).percent, len(found)) == "red"
