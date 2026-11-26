"""Load and validate the checklist YAML files in ``checklists/``.

Each file describes one production stage (or the common sections shared by
all stages). Editing a checklist only requires editing its YAML file.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

CHECKLIST_DIR = Path(__file__).resolve().parent.parent / "checklists"
CRITICALITIES = ("critical", "major", "minor")
LANGS = ("fr", "en")


@dataclass(frozen=True)
class Item:
    id: str
    text: dict  # {"fr": ..., "en": ...}
    ref: str
    criticality: str

    def label(self, lang: str) -> str:
        return self.text.get(lang) or self.text["fr"]


@dataclass(frozen=True)
class Section:
    id: str
    title: dict
    items: tuple

    def label(self, lang: str) -> str:
        return self.title.get(lang) or self.title["fr"]


@dataclass(frozen=True)
class Stage:
    id: str
    name: dict
    order: int
    sections: tuple
    common: bool = False

    def label(self, lang: str) -> str:
        return self.name.get(lang) or self.name["fr"]

    @property
    def items(self) -> list:
        return [item for section in self.sections for item in section.items]


@dataclass
class Library:
    common: Stage
    stages: list = field(default_factory=list)

    def stage(self, stage_id: str) -> Stage:
        for stage in self.stages:
            if stage.id == stage_id:
                return stage
        raise KeyError(stage_id)

    def sections_for(self, stage_id: str) -> list:
        """Common sections first, then the sections of the chosen stage."""
        return list(self.common.sections) + list(self.stage(stage_id).sections)


class ChecklistError(ValueError):
    pass


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise ChecklistError(msg)


def _parse_stage(raw: dict, source: str) -> Stage:
    _require(isinstance(raw, dict), f"{source}: file must be a mapping")
    for key in ("id", "name", "sections"):
        _require(key in raw, f"{source}: missing '{key}'")
    sections = []
    for s in raw["sections"]:
        _require("id" in s and "title" in s and s.get("items"), f"{source}: section needs id, title and items")
        items = []
        for it in s["items"]:
            where = f"{source} / {s['id']} / {it.get('id', '?')}"
            _require(it.get("id"), f"{where}: missing id")
            for lang in LANGS:
                _require(it.get(lang), f"{where}: missing '{lang}' text")
            _require(it.get("criticality") in CRITICALITIES,
                     f"{where}: criticality must be one of {CRITICALITIES}")
            items.append(Item(id=it["id"], text={l: it[l] for l in LANGS},
                              ref=it.get("ref", ""), criticality=it["criticality"]))
        sections.append(Section(id=s["id"], title=s["title"], items=tuple(items)))
    return Stage(id=raw["id"], name=raw["name"], order=raw.get("order", 99),
                 sections=tuple(sections), common=bool(raw.get("common", False)))


def load_library(directory: Path | str = CHECKLIST_DIR) -> Library:
    directory = Path(directory)
    common = None
    stages = []
    seen_ids: dict = {}
    for path in sorted(directory.glob("*.yaml")):
        with path.open(encoding="utf-8") as fh:
            stage = _parse_stage(yaml.safe_load(fh), path.name)
        for item in stage.items:
            _require(item.id not in seen_ids,
                     f"{path.name}: item id {item.id} already used in {seen_ids.get(item.id)}")
            seen_ids[item.id] = path.name
        if stage.common:
            _require(common is None, f"{path.name}: only one common checklist is allowed")
            common = stage
        else:
            stages.append(stage)
    _require(common is not None, f"no common checklist found in {directory}")
    _require(bool(stages), f"no stage checklist found in {directory}")
    stages.sort(key=lambda s: s.order)
    return Library(common=common, stages=stages)
