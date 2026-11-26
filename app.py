"""HSE inspection app for the stages of oil and gas production.

Run with:  streamlit run app.py
"""

from __future__ import annotations

from datetime import date

import pandas as pd
import streamlit as st

from hse_app import scoring, storage
from hse_app.checklists import load_library
from hse_app.i18n import t
from hse_app.pdf_report import build_pdf

STATUS_OPTIONS = list(scoring.STATUSES)
PRIORITIES = ["high", "medium", "low"]
CRIT_BADGE = {"critical": "🔴", "major": "🟠", "minor": "🟢"}
RATING_BADGE = {"green": "🟢", "amber": "🟠", "red": "🔴", "none": "⚪"}


@st.cache_resource
def get_library():
    return load_library()


def _pct(score) -> str:
    return "-" if score.percent is None else f"{score.percent:.0f} %"


def render_item(item, lang: str) -> dict:
    """Draw one checklist item and return its result."""
    key = f"item_{item.id}"
    st.markdown(f"{CRIT_BADGE[item.criticality]} **{item.id}** · {item.label(lang)}  \n"
                f"<small>{t(lang, 'ref')} {item.ref} · {t(lang, 'crit_' + item.criticality)}</small>",
                unsafe_allow_html=True)
    status = st.radio(item.id, STATUS_OPTIONS, index=None, horizontal=True, key=f"{key}_status",
                      format_func=lambda s: t(lang, f"status_{s}"), label_visibility="collapsed")
    result = {"status": status}
    result["observation"] = st.text_input(t(lang, "observation"), key=f"{key}_obs")
    if status == scoring.NON_CONFORM:
        c1, c2, c3, c4 = st.columns([3, 2, 2, 1.5])
        result["action"] = c1.text_input(t(lang, "action"), key=f"{key}_action")
        result["owner"] = c2.text_input(t(lang, "owner"), key=f"{key}_owner")
        due = c3.date_input(t(lang, "due"), value=None, key=f"{key}_due", format="DD/MM/YYYY")
        result["due"] = due.isoformat() if due else ""
        default_prio = 0 if item.criticality == "critical" else 1
        result["priority"] = c4.selectbox(t(lang, "priority"), PRIORITIES, index=default_prio,
                                          key=f"{key}_prio", format_func=lambda p: t(lang, f"prio_{p}"))
        photo = st.file_uploader(t(lang, "photo"), type=["png", "jpg", "jpeg"], key=f"{key}_photo")
        result["photo"] = photo.getvalue() if photo else None
    st.divider()
    return result


def new_inspection_tab(library, lang: str) -> None:
    c1, c2 = st.columns(2)
    with c1:
        inspection_date = st.date_input(t(lang, "date"), date.today(), format="DD/MM/YYYY")
        site = st.text_input(t(lang, "site"))
        installation = st.text_input(t(lang, "installation"))
    with c2:
        inspectors = st.text_input(t(lang, "inspectors"))
        department = st.text_input(t(lang, "department"))
        stage = st.selectbox(t(lang, "stage"), library.stages, format_func=lambda s: s.label(lang))

    sections = library.sections_for(stage.id)
    results: dict = {}
    for section in sections:
        prefix = stage.label(lang) if section in stage.sections else library.common.label(lang)
        with st.expander(f"{section.label(lang)}  ·  {prefix}", expanded=False):
            for item in section.items:
                results[item.id] = render_item(item, lang)
            sc = scoring.score_items(section.items, results)
            st.caption(f"{t(lang, 'score')} : {_pct(sc)}  ·  "
                       f"{t(lang, 'answered')} : {len(section.items) - sc.unanswered}/{len(section.items)}")

    comments = st.text_area(t(lang, "comments"))

    total = scoring.overall(sections, results)
    critical = scoring.critical_findings(sections, results)
    m1, m2, m3 = st.columns(3)
    m1.metric(t(lang, "score"), f"{RATING_BADGE[scoring.rating(total.percent, len(critical))]} {_pct(total)}")
    n_items = sum(len(s.items) for s in sections)
    m2.metric(t(lang, "answered"), f"{n_items - total.unanswered}/{n_items}")
    m3.metric(t(lang, "critical_nc"), len(critical))
    if critical:
        st.error("\n".join(f"- **{i.id}** {i.label(lang)}" for i in critical))
    if total.unanswered:
        st.info(t(lang, "unanswered_warn", n=total.unanswered))

    if st.button(t(lang, "generate"), type="primary"):
        if not site.strip() or not inspectors.strip():
            st.warning(t(lang, "missing_fields"))
        else:
            inspection = {
                "date": inspection_date.strftime("%d/%m/%Y"),
                "site": site, "installation": installation, "inspectors": inspectors,
                "department": department, "stage_id": stage.id, "lang": lang,
                "comments": comments, "results": results,
            }
            pdf = build_pdf(inspection, sections, stage.label(lang))
            inspection_id = storage.save_inspection(inspection, sections, pdf)
            st.session_state["last_report"] = (inspection_id, pdf, inspection_date.strftime("%Y%m%d"))

    if "last_report" in st.session_state:
        inspection_id, pdf, stamp = st.session_state["last_report"]
        st.success(t(lang, "generated", id=inspection_id))
        st.download_button(t(lang, "download"), data=pdf, mime="application/pdf",
                           file_name=f"hse_rapport_{stamp}_{inspection_id}.pdf")


def history_tab(library, lang: str) -> None:
    stage_names = {s.id: s.label(lang) for s in library.stages}
    inspections = storage.list_inspections()
    st.subheader(t(lang, "inspections"))
    if not inspections:
        st.info(t(lang, "no_history"))
        return
    df = pd.DataFrame(inspections)
    df["stage_id"] = df["stage_id"].map(stage_names).fillna(df["stage_id"])
    df = df.rename(columns={"inspection_date": t(lang, "date"), "site": t(lang, "site"),
                            "installation": t(lang, "installation"), "inspectors": t(lang, "inspectors"),
                            "stage_id": t(lang, "stage"), "score": t(lang, "score") + " %",
                            "critical_nc": t(lang, "critical_nc")})
    st.dataframe(df, hide_index=True, width="stretch")

    chosen = st.selectbox(t(lang, "select_inspection"), [r["id"] for r in inspections],
                          format_func=lambda i: next(f"#{r['id']} · {r['inspection_date']} · {r['site']}"
                                                     for r in inspections if r["id"] == i))
    pdf = storage.get_pdf(chosen)
    if pdf:
        st.download_button(t(lang, "download"), data=pdf, mime="application/pdf",
                           file_name=f"hse_rapport_{chosen}.pdf", key="history_dl")

    st.subheader(t(lang, "open_actions"))
    actions = storage.open_actions()
    if not actions:
        st.info(t(lang, "no_actions"))
        return
    adf = pd.DataFrame(actions)
    adf["overdue"] = adf["overdue"].map({1: "⚠️ " + t(lang, "overdue"), 0: ""})
    adf["criticality"] = adf["criticality"].map(lambda c: t(lang, f"crit_{c}"))
    adf["priority"] = adf["priority"].map(lambda p: t(lang, f"prio_{p}") if p else "")
    st.dataframe(adf.drop(columns=["id"]), hide_index=True, width="stretch")
    to_close = st.selectbox(t(lang, "select_action"), [a["id"] for a in actions],
                            format_func=lambda i: next(f"{a['item_id']} · {a['site']} · {a['action'] or ''}"
                                                       for a in actions if a["id"] == i))
    if st.button(t(lang, "close_action")):
        storage.close_action(to_close)
        st.toast(t(lang, "action_closed"))
        st.rerun()


def main() -> None:
    st.set_page_config(page_title="HSE Inspection App", page_icon="🦺", layout="wide")
    lang = st.sidebar.radio("Langue / Language", ["fr", "en"],
                            format_func=lambda l: {"fr": "Français", "en": "English"}[l])
    st.title(t(lang, "app_title"))
    library = get_library()
    tab_new, tab_history = st.tabs([t(lang, "tab_new"), t(lang, "tab_history")])
    with tab_new:
        new_inspection_tab(library, lang)
    with tab_history:
        history_tab(library, lang)


if __name__ == "__main__":
    main()
