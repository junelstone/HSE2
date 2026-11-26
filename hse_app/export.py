"""Excel export of inspections, answers and corrective actions."""

from __future__ import annotations

import io

import pandas as pd

from .i18n import t

STATUS_KEYS = {"C": "status_C", "NC": "status_NC", "NA": "status_NA"}


def build_excel(inspections: list, results: list, actions: list, lang: str, stage_names: dict) -> bytes:
    """Return an .xlsx file with three sheets: inspections, answers and open actions."""
    cols = column_names(lang)
    insp = pd.DataFrame(inspections, columns=["id", "inspection_date", "site", "installation", "inspectors",
                                              "stage_id", "score", "critical_nc"])
    res = pd.DataFrame(results)
    act = pd.DataFrame(actions)
    for df in (insp, res):
        if "stage_id" in df:
            df["stage_id"] = df["stage_id"].map(stage_names).fillna(df["stage_id"])
    if "status" in res:
        res["status"] = res["status"].map(lambda s: t(lang, STATUS_KEYS[s]) if s in STATUS_KEYS else "")
    for df in (res, act):
        if "criticality" in df:
            df["criticality"] = df["criticality"].map(lambda c: t(lang, f"crit_{c}") if isinstance(c, str) and c else "")
        if "priority" in df:
            df["priority"] = df["priority"].map(lambda p: t(lang, f"prio_{p}") if isinstance(p, str) and p else "")
    if "action_closed" in res:
        res["action_closed"] = res["action_closed"].map({1: t(lang, "yes"), 0: ""})
    if "overdue" in act:
        act["overdue"] = act["overdue"].map({1: t(lang, "yes"), 0: ""})
    act = act.drop(columns=["id"], errors="ignore")

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for df, sheet in ((insp, t(lang, "inspections")), (res, t(lang, "sheet_answers")),
                          (act, t(lang, "open_actions"))):
            df.rename(columns=cols).to_excel(writer, sheet_name=sheet[:31], index=False)
            ws = writer.sheets[sheet[:31]]
            ws.freeze_panes = "A2"
            for column in ws.columns:
                width = max(len(str(c.value or "")) for c in column[:200])
                ws.column_dimensions[column[0].column_letter].width = min(max(10, width + 2), 60)
    return buf.getvalue()


def column_names(lang: str) -> dict:
    """Database column -> translated header, shared by the history tables and the export."""
    keys = {
        "id": "col_id", "inspection_id": "col_id", "inspection_date": "date", "site": "site",
        "installation": "installation", "inspectors": "inspectors", "stage_id": "stage",
        "score": "col_score", "critical_nc": "critical_nc", "section_id": "col_section",
        "item_id": "col_item_id", "item_text": "item", "criticality": "criticality", "status": "status",
        "observation": "observation", "action": "action", "owner": "owner", "due_date": "due",
        "priority": "priority", "overdue": "overdue", "action_closed": "col_closed",
        "closed_at": "col_closed_at", "closed_by": "closed_by", "closing_note": "closing_note",
    }
    return {col: t(lang, key) for col, key in keys.items()}
