"""Command line interface: ``ums run | import | report | seed``.

* ``ums run`` -- start the Flask dev server (never debug=True in prod;
  set UMS_SECRET_KEY and UMS_DATABASE_URI for a real deployment).
* ``ums import FILE.csv`` -- import either export format, idempotently.
* ``ums report --input FILE.csv --pdf OUT.pdf`` -- the mp-active-users
  report, straight from a CSV without touching the database.
* ``ums seed`` -- load the fictional sample CSV into the database.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import create_app, db
from .importers import import_users_to_db, load_users_from_csv
from .reporting import export_to_pdf, split_users_to_csv

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_users.csv"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ums", description="User Management System")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Start the Flask dev server")
    run.add_argument("--host", default="127.0.0.1")
    run.add_argument("--port", type=int, default=5000)

    imp = sub.add_parser("import", help="Import a user CSV (admin or Graph format)")
    imp.add_argument("csv_file")

    rep = sub.add_parser("report", help="Build a PDF report from a user CSV")
    rep.add_argument("--input", required=True, dest="input")
    rep.add_argument("--pdf", required=True)
    rep.add_argument("--internal-csv", default=None)
    rep.add_argument("--external-csv", default=None)

    sub.add_parser("seed", help="Load the fictional sample CSV into the database")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "report":
        users = load_users_from_csv(args.input)
        summary = export_to_pdf(users, args.pdf)
        print(f"Report written to {args.pdf} "
              f"({summary['total']} users, {summary['members']} members, "
              f"{summary['guests']} guests)")
        if args.internal_csv or args.external_csv:
            internal = args.internal_csv or "internal_users.csv"
            external = args.external_csv or "external_users.csv"
            members, guests = split_users_to_csv(users, internal, external)
            print(f"CSV split: {members} members -> {internal}, "
                  f"{guests} guests -> {external}")
        return 0

    app = create_app()
    with app.app_context():
        if args.command == "run":
            app.run(host=args.host, port=args.port)
            return 0
        if args.command == "import":
            result = import_users_to_db(db, load_users_from_csv(args.csv_file))
            print(f"Imported {result.imported} new, updated {result.updated} "
                  f"existing, from {result.rows_read} rows.")
            return 0
        if args.command == "seed":
            if not SAMPLE.exists():
                print(f"Sample file not found: {SAMPLE}", file=sys.stderr)
                return 1
            result = import_users_to_db(db, load_users_from_csv(SAMPLE))
            print(f"Seeded {result.imported} new, updated {result.updated} "
                  f"existing, from {result.rows_read} rows.")
            return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
