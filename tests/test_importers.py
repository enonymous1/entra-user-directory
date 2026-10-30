from pathlib import Path

import pytest

from app import create_app, db
from app.config import TestConfig
from app.importers import import_users_to_db, load_users_from_csv
from app.models import User

SAMPLE = Path(__file__).resolve().parent.parent / "data" / "sample_users.csv"
GRAPH = Path(__file__).resolve().parent.parent / "data" / "sample_users_graph.csv"


def test_admin_sample_loads_names_and_counts():
    users = load_users_from_csv(SAMPLE)
    assert len(users) == 12
    assert users[0].display_name == "Alex Example"
    assert sum(1 for u in users if u.is_external_user) == 4
    assert sum(1 for u in users if not u.is_external_user) == 8


def test_bom_header_loads_display_names(tmp_path):
    # Regression test for the mp-active-users BOM bug: with plain utf-8 the
    # first header becomes "\ufeffDisplay name" and every name loads as "".
    bom = tmp_path / "bom.csv"
    header = SAMPLE.read_text(encoding="utf-8").splitlines()[0]
    first_row = SAMPLE.read_text(encoding="utf-8").splitlines()[1]
    bom.write_bytes(("\ufeff" + header + "\n" + first_row + "\n").encode("utf-8"))
    users = load_users_from_csv(bom)
    assert len(users) == 1
    assert users[0].display_name == "Alex Example"


def test_graph_sample_loads():
    users = load_users_from_csv(GRAPH)
    assert len(users) == 3
    assert users[2].is_external_user
    assert users[2].user_type == "Guest"


def test_unknown_format_raises(tmp_path):
    bad = tmp_path / "bad.csv"
    bad.write_text("Foo,Bar\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_users_from_csv(bad)


def test_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_users_from_csv("/nonexistent/nope.csv")


def test_import_is_idempotent():
    app = create_app(TestConfig)
    with app.app_context():
        users = load_users_from_csv(SAMPLE)
        first = import_users_to_db(db, users)
        second = import_users_to_db(db, load_users_from_csv(SAMPLE))
        assert first.imported == 12 and first.updated == 0
        assert second.imported == 0 and second.updated == 12
        assert User.query.count() == 12
        assert db.session.get(User, "00000000-0000-0000-0000-000000000001").display_name == "Alex Example"
