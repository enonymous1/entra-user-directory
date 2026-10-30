from pathlib import Path

from app.cli import main

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_users.csv"


def test_cli_report_from_csv(tmp_path, capsys):
    pdf = tmp_path / "out.pdf"
    internal = tmp_path / "internal.csv"
    external = tmp_path / "external.csv"
    assert main(["report", "--input", str(SAMPLE), "--pdf", str(pdf),
                 "--internal-csv", str(internal), "--external-csv", str(external)]) == 0
    assert pdf.read_bytes()[:5] == b"%PDF-"
    out = capsys.readouterr().out
    assert "12 users" in out
    assert len(internal.read_text(encoding="utf-8").splitlines()) == 9  # header + 8
    assert len(external.read_text(encoding="utf-8").splitlines()) == 5  # header + 4
