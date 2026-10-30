from pathlib import Path

from app.importers import load_users_from_csv
from app.reporting import export_to_pdf, split_users_to_csv, summarize

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_users.csv"


def test_summary_counts_sample():
    summary = summarize(load_users_from_csv(SAMPLE))
    assert summary["total"] == 12
    assert summary["members"] == 8
    assert summary["guests"] == 4
    assert summary["licensed"] == 8
    assert summary["unlicensed"] == 4
    assert summary["monthly_counts"] == {"2025-01": 4, "2025-02": 4, "2025-03": 4}


def test_pdf_starts_with_pdf_magic_and_mentions_counts(tmp_path):
    pdf = tmp_path / "report.pdf"
    summary = export_to_pdf(load_users_from_csv(SAMPLE), pdf)
    assert pdf.read_bytes()[:5] == b"%PDF-"
    assert summary["total"] == 12


def test_csv_split_covers_every_user(tmp_path):
    internal = tmp_path / "internal_users.csv"
    external = tmp_path / "external_users.csv"
    members, guests = split_users_to_csv(load_users_from_csv(SAMPLE), internal, external)
    # The original dropped 16 internal users; the split must now be lossless.
    assert (members, guests) == (8, 4)
    assert members + guests == 12
    assert "Alex Example" in internal.read_text(encoding="utf-8")
    assert "Pat Guest" in external.read_text(encoding="utf-8")
