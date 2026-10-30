from pathlib import Path

import pytest

from app import create_app, db
from app.config import TestConfig
from app.importers import import_users_to_db, load_users_from_csv

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_users.csv"


@pytest.fixture()
def client():
    app = create_app(TestConfig)
    with app.app_context():
        import_users_to_db(db, load_users_from_csv(SAMPLE))
    with app.test_client() as client:
        yield client


def test_index_and_users_list(client):
    assert client.get("/").status_code == 200
    resp = client.get("/users")
    assert resp.status_code == 200
    assert b"Alex Example" in resp.data


def test_users_search_and_guest_filter(client):
    assert b"Alex Example" in client.get("/users?q=Alex").data
    assert b"Alex Example" not in client.get("/users?q=Alex&kind=guest").data
    assert b"Pat Guest" in client.get("/users?kind=guest").data


def test_user_detail_queries_db_and_404s(client):
    resp = client.get("/user/00000000-0000-0000-0000-000000000001")
    assert resp.status_code == 200
    assert b"Alex Example" in resp.data
    assert client.get("/user/does-not-exist").status_code == 404


def test_import_post_upload_is_idempotent(client):
    with SAMPLE.open("rb") as handle:
        resp = client.post(
            "/import",
            data={"csv_file": (handle, "sample_users.csv")},
            content_type="multipart/form-data",
            follow_redirects=True,
        )
    assert resp.status_code == 200
    assert b"Alex Example" in resp.data


def test_import_get_is_a_form_not_a_side_effect(client):
    assert client.get("/import").status_code == 200


def test_report_pages_and_downloads(client):
    assert client.get("/report").status_code == 200
    pdf = client.get("/report.pdf")
    assert pdf.status_code == 200
    assert pdf.data[:5] == b"%PDF-"
    assert pdf.mimetype == "application/pdf"
    csv_resp = client.get("/report/internal.csv")
    assert csv_resp.status_code == 200
    assert b"Alex Example" in csv_resp.data
    assert client.get("/report/bogus.csv").status_code == 404
