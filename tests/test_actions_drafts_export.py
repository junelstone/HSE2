import io
import sqlite3
from datetime import date

from openpyxl import load_workbook

from hse_app import actions, scoring, storage
from hse_app.checklists import load_library
from hse_app.export import build_excel
from hse_app.pdf_report import build_pdf


def _sections():
    return load_library().sections_for("drilling")


def test_missing_action_fields_lists_only_incomplete_nc():
    sections = _sections()
    a, b, c = [i for s in sections for i in s.items][:3]
    results = {
        a.id: {"status": scoring.NON_CONFORM, "action": "Fix", "owner": "Bob"},
        b.id: {"status": scoring.NON_CONFORM, "action": "  ", "owner": "Bob"},
        c.id: {"status": scoring.CONFORM},
    }
    assert actions.missing_action_fields(sections, results) == [b]


def test_default_due_from_priority():
    today = date(2026, 1, 1)
    assert actions.default_due("high", today) == "2026-01-08"
    assert actions.default_due("medium", today) == "2026-01-31"
    assert actions.default_due("low", today) == "2026-04-01"
    sections = _sections()
    item = sections[0].items[0]
    results = {item.id: {"status": scoring.NON_CONFORM, "priority": "high", "due": ""}}
    actions.fill_default_dues(sections, results, today)
    assert results[item.id]["due"] == "2026-01-08"


def test_draft_roundtrip(tmp_path):
    db = tmp_path / "d.db"
    storage.save_draft("abc", {"hdr_site": "A", "item_X_status": "C"}, path=db)
    storage.save_draft("abc", {"hdr_site": "B"}, path=db)
    assert storage.load_draft("abc", path=db) == {"hdr_site": "B"}
    storage.delete_draft("abc", path=db)
    assert storage.load_draft("abc", path=db) is None


def test_close_action_records_who_and_old_db_is_migrated(tmp_path):
    db = tmp_path / "old.db"
    # a database created by the first release, without the closing columns
    conn = sqlite3.connect(db)
    conn.executescript(storage.SCHEMA.replace("    closed_at TEXT,\n    closed_by TEXT,\n    closing_note TEXT",
                                              "    closed_at TEXT"))
    conn.close()
    sections = _sections()
    item = sections[0].items[0]
    insp = {"lang": "fr", "site": "S", "results": {item.id: {
        "status": scoring.NON_CONFORM, "action": "Fix", "owner": "Bob", "due": "2026-01-01"}}}
    storage.save_inspection(insp, sections, build_pdf(insp, sections, "Forage"), path=db)
    open_ = storage.open_actions(path=db)
    storage.close_action(open_[0]["id"], path=db, closed_by="Ann", note="Done")
    closed = storage.closed_actions(path=db)
    assert closed[0]["closed_by"] == "Ann" and closed[0]["closing_note"] == "Done"
    assert storage.known_sites(path=db) == (["S"], [])


def test_excel_export_has_three_translated_sheets(tmp_path):
    db = tmp_path / "x.db"
    sections = _sections()
    item = sections[0].items[0]
    insp = {"lang": "en", "site": "S", "stage_id": "drilling", "results": {item.id: {
        "status": scoring.NON_CONFORM, "action": "Fix", "owner": "Bob", "priority": "high"}}}
    storage.save_inspection(insp, sections, b"%PDF", path=db)
    for lang in ("fr", "en"):
        data = build_excel(storage.list_inspections(path=db), storage.all_results(path=db),
                           storage.open_actions(path=db), lang, {"drilling": "Drilling"})
        wb = load_workbook(io.BytesIO(data))
        assert len(wb.sheetnames) == 3
    ws = wb.worksheets[2]
    assert [c.value for c in ws[1]][:3] == ["No.", "Location / Site", "Item ref."]
