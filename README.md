# entra-user-directory

A Flask + SQLite viewer **and** PDF reporter for a Microsoft Entra / M365 user export.

This is two older projects folded into one:

- **ss-ums** (2025) — a Flask viewer for a Graph-style user export. It could list users, but the detail page never queried the database, the list was unbounded, and importing was a GET that hard-coded a Windows path and crashed on a second import.
- **mp-active-users** (2025) — a CLI that turned an Entra admin-center export into a ReportLab PDF plus split internal/external CSVs. Its charts were defined but never called, its totals were computed but never printed, and a BOM on the source header made every display name load as empty.

The folded version keeps both halves, on one database, with both bugs fixed.

## What it does

- Browse users with search, member/guest filter, and pagination; click through to a real detail page.
- Import either export format (admin 28-column or Graph 15-column), idempotently — re-importing updates instead of failing on the primary key.
- View an HTML summary report, download it as PDF (with summary counts, license table, monthly chart, and member/guest tables), or download the member/guest CSV split. The split is lossless: every user lands in exactly one file.
- CLI: `ums run`, `ums import FILE.csv`, `ums report --input FILE.csv --pdf OUT.pdf`, `ums seed`.

## Demo data only

Everything shipped here is fictional: `data/sample_users.csv` (12 people at `example.org`, 8 members + 4 guests) and `data/sample_users_graph.csv` (the same directory in Graph format). **No real directory export ships in this repo.** The original projects' real exports are not included, and their histories are not merged here — this is a fresh, single-commit export.

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e .[test]

ums seed          # load the fictional sample
ums run           # http://127.0.0.1:5000/
```

Or report straight from a CSV, without the database:

```bash
ums report --input data/sample_users.csv --pdf report.pdf \
  --internal-csv internal_users.csv --external-csv external_users.csv
```

For a real deployment, set `UMS_SECRET_KEY` and `UMS_DATABASE_URI`; the defaults are dev-only.

## Tests

```bash
pytest -q
ruff check app tests
```

## Layout

```text
entra-user-directory/
├── app/
│   ├── __init__.py      # Flask app factory
│   ├── config.py        # env-based config (no hard-coded secrets/paths)
│   ├── models.py        # SQLAlchemy User (superset of both export formats)
│   ├── directory.py     # shared dataclass + bool/date parsing
│   ├── importers.py     # admin + Graph CSV readers, idempotent upsert
│   ├── reporting.py     # summary, charts, PDF, CSV split
│   ├── routes.py        # viewer + report routes
│   ├── cli.py           # `ums` console script
│   ├── templates/       # Jinja templates (styles block actually exists now)
│   └── static/style.css
├── data/
│   ├── sample_users.csv        # fictional admin-format sample
│   └── sample_users_graph.csv  # fictional Graph-format sample
└── tests/
```
