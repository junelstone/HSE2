# HSE inspection app for oil and gas production

A Streamlit app to run HSE (health, safety and environment) inspections on oil
and gas sites and produce a signed-off PDF report. The checklists follow IOGP,
API, ISO 45001 / 14001, OSHA PSM and IFC EHS references.

## Features

- **One checklist per production stage**: exploration and seismic, drilling,
  completion and well intervention, production, processing and storage,
  transport and pipelines, maintenance and shutdowns, decommissioning.
- **Common sections on every inspection**: general safety, fire, equipment,
  environment, behaviour, training, the 9 IOGP Life-Saving Rules, and risk
  assessment / emergency / health.
- Each item has an ID, a reference standard and a criticality (critical, major, minor).
- Each item is marked **Conforme / Non conforme / N/A**. A non-conformity asks
  for a corrective action, owner, due date, priority and an optional photo.
- Live compliance score per section and overall, with critical findings highlighted.
- **PDF report** with summary, detailed checklist, action plan, photos and signatures.
- **History**: every inspection is saved (SQLite) with its PDF. Open corrective
  actions are listed with overdue ones first, and can be closed.
- French and English interface and checklists, with a FR / EN switch next to the title.
- Each section header shows its progress and score; a button marks the rest of a section "Conforme".
- A non-conformity cannot be saved without a corrective action and an owner. An empty due date
  is set from the priority: 7 days (high), 30 (medium) or 90 (low).
- An optional photo can be added to any item.
- The inspection in progress is saved as you go, so a page refresh or a lost signal does not lose it
  (the page address carries the draft number).
- Sites and installations used before can be picked from a list.
- Closing an action records who closed it, when, and a closing comment.
- **Excel export** of inspections, every answer and the open actions.

## Run it

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

Or open the repository in GitHub Codespaces: the dev container installs
everything and starts the app.

Inspections are stored in `data/inspections.db` (not committed). Set
`HSE_DB_PATH` to use another location.

> **Streamlit Community Cloud:** the app's disk is reset when it restarts or is
> redeployed, so the SQLite history does not last there. Download each PDF (or the
> Excel export) until the history is moved to a hosted database.

## Edit the checklists

Checklists are plain YAML files in [`checklists/`](checklists/), so HSE staff
can change them without touching the Python code. `00_common.yaml` holds the
sections shown on every inspection; each other file is one production stage.

```yaml
sections:
  - id: well_control
    title: {fr: Contrôle des puits, en: Well control}
    items:
      - id: DRL-WC-01          # unique across all files
        fr: Tests du BOP enregistrés et à jour
        en: BOP tests recorded and current
        ref: API Std 53        # reference standard
        criticality: critical  # critical | major | minor
```

To add a stage, add a new YAML file with a unique `id` and an `order`. The app
checks the files when it starts and reports any missing field or duplicate ID.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

The tests check every checklist file, the scoring, the PDF export for every
stage in both languages, and the database. They run on GitHub Actions for
every pull request.

## Project layout

```
streamlit_app.py       Streamlit interface (main file for Streamlit Cloud)
hse_app/checklists.py  loads and validates the YAML checklists
hse_app/scoring.py     compliance score and critical findings
hse_app/pdf_report.py  PDF report
hse_app/storage.py     SQLite history, corrective actions and drafts
hse_app/actions.py     rules for corrective actions (required fields, default due dates)
hse_app/export.py      Excel export
hse_app/i18n.py        French / English interface text
checklists/            checklist content, one file per stage
tests/                 pytest suite
```
