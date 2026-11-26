import pytest

from hse_app.checklists import CRITICALITIES, ChecklistError, load_library

EXPECTED_STAGES = {
    "exploration_seismic", "drilling", "completion", "production", "processing",
    "transport_pipelines", "maintenance_shutdown", "decommissioning",
}


def test_library_loads_all_stages():
    lib = load_library()
    assert {s.id for s in lib.stages} == EXPECTED_STAGES
    assert lib.common.common


def test_every_item_is_complete():
    lib = load_library()
    for stage in [lib.common, *lib.stages]:
        for item in stage.items:
            assert item.text["fr"] and item.text["en"], item.id
            assert item.ref, item.id
            assert item.criticality in CRITICALITIES


def test_common_has_original_items_and_life_saving_rules():
    lib = load_library()
    ids = {i.id for i in lib.common.items}
    assert {"GEN-01", "FIR-01", "EQP-01", "ENV-01", "BEH-01", "TRN-01"} <= ids
    assert sum(1 for i in ids if i.startswith("LSR-")) == 9


def test_sections_for_puts_common_first():
    lib = load_library()
    sections = lib.sections_for("drilling")
    assert sections[0].id == lib.common.sections[0].id
    assert sections[-1] == lib.stage("drilling").sections[-1]


def test_duplicate_ids_rejected(tmp_path):
    common = "id: c\ncommon: true\nname: {fr: c, en: c}\nsections:\n  - id: s\n    title: {fr: s, en: s}\n    items:\n" \
             "      - {id: X-1, fr: a, en: a, ref: r, criticality: major}\n"
    (tmp_path / "00.yaml").write_text(common, encoding="utf-8")
    (tmp_path / "01.yaml").write_text(common.replace("common: true", "common: false").replace("id: c", "id: d"),
                                      encoding="utf-8")
    with pytest.raises(ChecklistError, match="already used"):
        load_library(tmp_path)


def test_bad_criticality_rejected(tmp_path):
    (tmp_path / "00.yaml").write_text(
        "id: c\ncommon: true\nname: {fr: c, en: c}\nsections:\n  - id: s\n    title: {fr: s, en: s}\n"
        "    items:\n      - {id: X-1, fr: a, en: a, ref: r, criticality: huge}\n", encoding="utf-8")
    with pytest.raises(ChecklistError, match="criticality"):
        load_library(tmp_path)
