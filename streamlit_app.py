"""HSE inspection app for the stages of oil and gas production.

Run with:  streamlit run streamlit_app.py
"""

from __future__ import annotations

import uuid
from datetime import date

import pandas as pd
import streamlit as st

from hse_app import actions, scoring, storage
from hse_app.checklists import load_library
from hse_app.export import build_excel, column_names
from hse_app.i18n import t
from hse_app.pdf_report import build_pdf

STATUS_OPTIONS = list(scoring.STATUSES)
PRIORITIES = ["high", "medium", "low"]
CRIT_BADGE = {"critical": "🔴", "major": "🟠", "minor": "🟢"}
RATING_BADGE = {"green": "🟢", "amber": "🟠", "red": "🔴", "none": "⚪"}

# Header fields of the form, as session keys. They and every "item_" key are kept in the draft.
HEADER_KEYS = ("hdr_date", "hdr_site", "hdr_installation", "hdr_inspectors", "hdr_department",
               "hdr_stage", "hdr_comments")
DRAFT_SKIP_SUFFIXES = ("_photo",)  # photos are not kept in drafts (too large)

CSS = """
<style>
/* Shorter heading on phones so the form starts higher up */
@media (max-width: 640px) {
  h1 { font-size: 1.7rem !important; }
  .block-container { padding-top: 2.5rem !important; }
}
div[data-testid="stExpander"] summary p { font-weight: 600; }
</style>
"""


@st.cache_resource
def get_library():
    return load_library()


def _pct(score) -> str:
    return "-" if score.percent is None else f"{score.percent:.0f} %"


# ---------- drafts ----------

def _draft_keys():
    for key in list(st.session_state.keys()):
        if key in HEADER_KEYS or (key.startswith("item_") and not key.endswith(DRAFT_SKIP_SUFFIXES)):
            yield key


def _serialise(value):
    if isinstance(value, date):
        return {"__date__": value.isoformat()}
    return value


def _deserialise(value):
    if isinstance(value, dict) and "__date__" in value:
        return date.fromisoformat(value["__date__"])
    return value


def restore_draft() -> None:
    """On a fresh session, reload the inspection in progress named in the page address."""
    if st.session_state.get("_draft_checked"):
        return
    st.session_state["_draft_checked"] = True
    draft_id = st.query_params.get("draft")
    if not draft_id:
        return
    data = storage.load_draft(draft_id)
    if not data:
        del st.query_params["draft"]
        return
    for key, value in data.items():
        st.session_state[key] = _deserialise(value)
    st.session_state["_draft_id"] = draft_id
    st.toast(t(st.session_state.get("lang", "fr"), "draft_restored"), icon="💾")


def save_draft() -> None:
    data = {key: _serialise(st.session_state[key]) for key in _draft_keys()
            if st.session_state[key] not in (None, "", [])}
    has_answers = any(k.startswith("item_") for k in data) or any(
        data.get(k) for k in ("hdr_site", "hdr_inspectors", "hdr_installation"))
    if not has_answers:
        return
    draft_id = st.session_state.get("_draft_id")
    if not draft_id:
        draft_id = uuid.uuid4().hex[:12]
        st.session_state["_draft_id"] = draft_id
    if st.query_params.get("draft") != draft_id:
        st.query_params["draft"] = draft_id
    storage.save_draft(draft_id, data)


def start_new_inspection() -> None:
    draft_id = st.session_state.pop("_draft_id", None)
    if draft_id:
        storage.delete_draft(draft_id)
    for key in list(st.session_state.keys()):
        if key in HEADER_KEYS or key.startswith("item_") or key == "last_report":
            del st.session_state[key]
    if "draft" in st.query_params:
        del st.query_params["draft"]


# ---------- new inspection ----------

def mark_rest_conform(item_ids: list) -> None:
    for item_id in item_ids:
        key = f"item_{item_id}_status"
        if st.session_state.get(key) is None:
            st.session_state[key] = scoring.CONFORM


def lang_widget(widget, label: str, options: list, state_key: str, lang: str, format_func, **kwargs):
    """A radio or selectbox whose value lives in ``state_key`` and whose labels follow the language.

    Streamlit keeps showing the old choice text (or drops the selection) when only format_func
    changes, so there is one widget per language. The value is kept in ``state_key`` and copied
    into the widget before it is drawn.
    """
    widget_key = f"_{state_key}_{lang}"

    def _copy():
        st.session_state[state_key] = st.session_state[widget_key]

    st.session_state[widget_key] = st.session_state.get(state_key)
    value = widget(label, options, key=widget_key, on_change=_copy, format_func=format_func, **kwargs)
    st.session_state[state_key] = value
    return value


def render_item(item, lang: str) -> dict:
    """Draw one checklist item and return its result."""
    key = f"item_{item.id}"
    st.markdown(f"{CRIT_BADGE[item.criticality]} **{item.id}** · {item.label(lang)}  \n"
                f"<small>{t(lang, 'ref')} {item.ref} · {t(lang, 'crit_' + item.criticality)}</small>",
                unsafe_allow_html=True)
    status = lang_widget(st.radio, item.id, STATUS_OPTIONS, f"{key}_status", lang,
                         lambda s: t(lang, f"status_{s}"), horizontal=True, label_visibility="collapsed")
    result = {"status": status}
    c_obs, c_photo = st.columns([5, 1], vertical_alignment="bottom")
    result["observation"] = c_obs.text_input(t(lang, "observation"), key=f"{key}_obs")
    has_photo = st.session_state.get(f"{key}_photo") is not None
    with c_photo.popover(("✅ " if has_photo else "📷 ") + t(lang, "photo_btn"), width="stretch"):
        photo = st.file_uploader(t(lang, "photo"), type=["png", "jpg", "jpeg"], key=f"{key}_photo")
    result["photo"] = photo.getvalue() if photo else None
    if status == scoring.NON_CONFORM:
        c1, c2 = st.columns(2)
        result["action"] = c1.text_input(t(lang, "action") + " *", key=f"{key}_action")
        result["owner"] = c2.text_input(t(lang, "owner") + " *", key=f"{key}_owner")
        c3, c4 = st.columns(2)
        st.session_state.setdefault(f"{key}_prio", "high" if item.criticality == "critical" else "medium")
        with c3:
            result["priority"] = lang_widget(st.selectbox, t(lang, "priority"), PRIORITIES, f"{key}_prio", lang,
                                             lambda p: t(lang, f"prio_{p}"))
        st.session_state.setdefault(f"{key}_due", None)
        due = c4.date_input(t(lang, "due"), key=f"{key}_due", format="DD/MM/YYYY", help=t(lang, "due_help"))
        result["due"] = due.isoformat() if due else ""
    st.divider()
    return result


def _section_progress(section) -> tuple[int, scoring.Score]:
    results = {i.id: {"status": st.session_state.get(f"item_{i.id}_status")} for i in section.items}
    sc = scoring.score_items(section.items, results)
    return len(section.items) - sc.unanswered, sc


def header_fields(library, lang: str):
    sites, installs = storage.known_sites()
    st.session_state.setdefault("hdr_date", date.today())
    st.session_state.setdefault("hdr_stage", library.stages[0].id)
    for key in ("hdr_site", "hdr_installation"):
        st.session_state.setdefault(key, None)
    # keep a restored value selectable even if it is not in the saved list
    for key, options in (("hdr_site", sites), ("hdr_installation", installs)):
        value = st.session_state.get(key)
        if value and value not in options:
            options.insert(0, value)
    stage_ids = [s.id for s in library.stages]
    if st.session_state["hdr_stage"] not in stage_ids:
        st.session_state["hdr_stage"] = stage_ids[0]

    c1, c2 = st.columns(2)
    with c1:
        st.date_input(t(lang, "date"), key="hdr_date", format="DD/MM/YYYY")
        st.selectbox(t(lang, "site") + " *", sites, key="hdr_site", accept_new_options=True,
                     placeholder=t(lang, "site_placeholder"))
        st.selectbox(t(lang, "installation"), installs, key="hdr_installation", accept_new_options=True,
                     placeholder=t(lang, "install_placeholder"))
    with c2:
        st.text_input(t(lang, "inspectors") + " *", key="hdr_inspectors")
        st.text_input(t(lang, "department"), key="hdr_department")
        lang_widget(st.selectbox, t(lang, "stage"), stage_ids, "hdr_stage", lang,
                    lambda sid: library.stage(sid).label(lang))
    return library.stage(st.session_state["hdr_stage"])


def new_inspection_tab(library, lang: str) -> None:
    if "last_report" in st.session_state:
        report_done(lang)
        return

    st.caption(t(lang, "intro"))
    stage = header_fields(library, lang)

    sections = library.sections_for(stage.id)
    results: dict = {}
    for section in sections:
        prefix = stage.label(lang) if section in stage.sections else library.common.label(lang)
        answered, sc = _section_progress(section)
        n = len(section.items)
        done = "✅ " if answered == n else ""
        label = f"{done}{section.label(lang)} · {prefix} — {answered}/{n}"
        if sc.percent is not None:
            label += f" · {_pct(sc)}"
        with st.expander(label, expanded=False, key=f"exp_{stage.id}_{section.id}"):
            if answered < n:
                st.button(t(lang, "mark_rest"), key=f"rest_{section.id}", on_click=mark_rest_conform,
                          args=([i.id for i in section.items],), icon="✔️")
            for item in section.items:
                results[item.id] = render_item(item, lang)

    st.text_area(t(lang, "comments"), key="hdr_comments")

    total = scoring.overall(sections, results)
    critical = scoring.critical_findings(sections, results)
    n_items = sum(len(s.items) for s in sections)
    st.progress((n_items - total.unanswered) / n_items if n_items else 0.0)
    m1, m2, m3 = st.columns(3)
    m1.metric(t(lang, "score"), f"{RATING_BADGE[scoring.rating(total.percent, len(critical))]} {_pct(total)}")
    m2.metric(t(lang, "answered"), f"{n_items - total.unanswered}/{n_items}")
    m3.metric(t(lang, "critical_nc"), len(critical))
    if critical:
        st.error("\n".join(f"- **{i.id}** {i.label(lang)}" for i in critical))
    if total.unanswered:
        st.info(t(lang, "unanswered_warn", n=total.unanswered))

    save_draft()

    if st.button(t(lang, "generate"), type="primary", width="stretch"):
        site = (st.session_state.get("hdr_site") or "").strip()
        inspectors = (st.session_state.get("hdr_inspectors") or "").strip()
        missing = actions.missing_action_fields(sections, results)
        if not site or not inspectors:
            st.warning(t(lang, "missing_fields"))
        elif missing:
            st.error(t(lang, "missing_actions") + "\n" + "\n".join(
                f"- **{i.id}** {i.label(lang)}" for i in missing))
        else:
            actions.fill_default_dues(sections, results)
            inspection_date = st.session_state["hdr_date"]
            inspection = {
                "date": inspection_date.strftime("%d/%m/%Y"),
                "site": site, "installation": st.session_state.get("hdr_installation") or "",
                "inspectors": inspectors, "department": st.session_state.get("hdr_department") or "",
                "stage_id": stage.id, "lang": lang,
                "comments": st.session_state.get("hdr_comments") or "", "results": results,
            }
            pdf = build_pdf(inspection, sections, stage.label(lang))
            inspection_id = storage.save_inspection(inspection, sections, pdf)
            draft_id = st.session_state.pop("_draft_id", None)
            if draft_id:
                storage.delete_draft(draft_id)
            if "draft" in st.query_params:
                del st.query_params["draft"]
            st.session_state["last_report"] = (inspection_id, pdf, inspection_date.strftime("%Y%m%d"))
            st.rerun()


def report_done(lang: str) -> None:
    inspection_id, pdf, stamp = st.session_state["last_report"]
    st.success(t(lang, "generated", id=inspection_id))
    st.download_button(t(lang, "download"), data=pdf, mime="application/pdf", type="primary",
                       file_name=f"hse_rapport_{stamp}_{inspection_id}.pdf", icon="📄")
    st.button(t(lang, "new_inspection"), on_click=start_new_inspection, icon="➕")


# ---------- history ----------

def history_tab(library, lang: str) -> None:
    stage_names = {s.id: s.label(lang) for s in library.stages}
    cols = column_names(lang)
    inspections = storage.list_inspections()
    st.subheader(t(lang, "inspections"))
    if not inspections:
        st.info(t(lang, "no_history"))
        return
    df = pd.DataFrame(inspections)
    df["stage_id"] = df["stage_id"].map(stage_names).fillna(df["stage_id"])
    df["critical_nc"] = df["critical_nc"].fillna(0).astype(int)
    st.dataframe(df.rename(columns=cols), hide_index=True, width="stretch",
                 column_config={cols["score"]: st.column_config.ProgressColumn(
                     cols["score"], min_value=0, max_value=100, format="%.0f %%")})

    c1, c2 = st.columns([3, 2], vertical_alignment="bottom")
    chosen = c1.selectbox(t(lang, "select_inspection"), [r["id"] for r in inspections],
                          format_func=lambda i: next(f"#{r['id']} · {r['inspection_date']} · {r['site']}"
                                                     for r in inspections if r["id"] == i))
    pdf = storage.get_pdf(chosen)
    if pdf:
        c2.download_button(t(lang, "download"), data=pdf, mime="application/pdf", icon="📄",
                           file_name=f"hse_rapport_{chosen}.pdf", key="history_dl", width="stretch")

    open_list = storage.open_actions()
    excel = build_excel(inspections, storage.all_results(), open_list, lang, stage_names)
    st.download_button(t(lang, "export_excel"), data=excel, icon="📊", file_name=f"hse_export_{date.today():%Y%m%d}.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    st.subheader(t(lang, "open_actions"))
    if not open_list:
        st.info(t(lang, "no_actions"))
    else:
        adf = pd.DataFrame(open_list)
        adf["overdue"] = adf["overdue"].map({1: "⚠️ " + t(lang, "overdue"), 0: ""})
        adf["criticality"] = adf["criticality"].map(lambda c: t(lang, f"crit_{c}"))
        adf["priority"] = adf["priority"].map(lambda p: t(lang, f"prio_{p}") if p else "")
        adf = adf.drop(columns=["id"]).rename(columns=cols)
        st.dataframe(adf, hide_index=True, width="stretch")
        with st.form("close_action", clear_on_submit=True, border=True):
            to_close = st.selectbox(t(lang, "select_action"), [a["id"] for a in open_list],
                                    format_func=lambda i: next(f"{a['item_id']} · {a['site']} · {a['action'] or ''}"
                                                               for a in open_list if a["id"] == i))
            c1, c2 = st.columns([1, 2])
            closed_by = c1.text_input(t(lang, "closed_by") + " *")
            note = c2.text_input(t(lang, "closing_note"))
            if st.form_submit_button(t(lang, "close_action")):
                if not closed_by.strip():
                    st.warning(t(lang, "closed_by_required"))
                else:
                    storage.close_action(to_close, closed_by=closed_by.strip(), note=note.strip())
                    st.toast(t(lang, "action_closed"))
                    st.rerun()

    closed = storage.closed_actions()
    if closed:
        st.subheader(t(lang, "closed_recent"))
        cdf = pd.DataFrame(closed)
        cdf["closed_at"] = pd.to_datetime(cdf["closed_at"]).dt.strftime("%d/%m/%Y %H:%M")
        st.dataframe(cdf.rename(columns=cols), hide_index=True, width="stretch")


# ---------- page ----------

def language_switch() -> str:
    if "lang" not in st.session_state:
        st.session_state["lang"] = st.query_params.get("lang", "fr") if st.query_params.get("lang") in ("fr", "en") \
            else "fr"
    return st.session_state["lang"]


def main() -> None:
    st.set_page_config(page_title="HSE Inspection App", page_icon="🦺", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    language_switch()
    restore_draft()
    c_title, c_lang = st.columns([5, 1], vertical_alignment="center")
    with c_lang:
        st.segmented_control("Langue / Language", ["fr", "en"], key="lang", required=True,
                             format_func=lambda l: {"fr": "🇫🇷 FR", "en": "🇬🇧 EN"}[l],
                             label_visibility="collapsed")
    lang = st.session_state["lang"]
    if st.query_params.get("lang") != lang:
        st.query_params["lang"] = lang
    c_title.title(t(lang, "app_title"))

    library = get_library()
    tab_new, tab_history = st.tabs([t(lang, "tab_new"), t(lang, "tab_history")])
    with tab_new:
        new_inspection_tab(library, lang)
    with tab_history:
        history_tab(library, lang)


if __name__ == "__main__":
    main()
