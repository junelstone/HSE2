import io

from PIL import Image

from hse_app import scoring, storage
from hse_app.checklists import load_library
from hse_app.pdf_report import build_pdf, clean


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), (200, 0, 0)).save(buf, format="PNG")
    return buf.getvalue()


def _inspection(lang, sections):
    results = {}
    for n, item in enumerate(i for s in sections for i in s.items):
        results[item.id] = {"status": scoring.STATUSES[n % 3], "observation": "Fuite d'huile ’test’ ☑ œ"}
    first = sections[-1].items[0].id
    results[first] = {"status": scoring.NON_CONFORM, "observation": "x", "action": "Réparer",
                      "owner": "Chef de quart", "due": "2020-01-01", "priority": "high", "photo": _png()}
    return {"date": "26/11/2026", "site": "Site A", "installation": "FPSO", "inspectors": "J. Doe",
            "department": "HSE", "stage_id": "drilling", "lang": lang, "comments": "RAS – ok",
            "results": results}


def test_clean_handles_symbols_that_crashed_v1():
    assert clean("☐ ☑ ’ œ") == "[ ] [x] ' oe"
    assert clean("éàç") == "éàç"


def test_pdf_builds_for_every_stage_and_language():
    lib = load_library()
    for stage in lib.stages:
        sections = lib.sections_for(stage.id)
        for lang in ("fr", "en"):
            pdf = build_pdf(_inspection(lang, sections), sections, stage.label(lang))
            assert pdf.startswith(b"%PDF")


def test_empty_inspection_pdf():
    lib = load_library()
    sections = lib.sections_for("production")
    pdf = build_pdf({"lang": "fr", "results": {}}, sections, "Production")
    assert pdf.startswith(b"%PDF")


def test_save_and_actions_roundtrip(tmp_path):
    db = tmp_path / "t.db"
    lib = load_library()
    sections = lib.sections_for("drilling")
    insp = _inspection("fr", sections)
    pdf = build_pdf(insp, sections, "Forage")
    iid = storage.save_inspection(insp, sections, pdf, path=db)
    assert storage.list_inspections(path=db)[0]["id"] == iid
    assert storage.get_pdf(iid, path=db) == pdf
    actions = storage.open_actions(path=db)
    n_nc = sum(1 for r in insp["results"].values() if r["status"] == scoring.NON_CONFORM)
    assert len(actions) == n_nc
    assert actions[0]["overdue"] == 1  # due 2020-01-01 sorts first
    storage.close_action(actions[0]["id"], path=db)
    assert len(storage.open_actions(path=db)) == n_nc - 1
