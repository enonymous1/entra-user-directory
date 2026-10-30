"""CSV importers for the two Entra export formats this project has seen.

* "admin" format -- the mp-active-users export: 28 columns headed
  ``Display name``, ``User principal name``, ``Object Id``, ``When created``,
  ``Licenses``, and so on.
* "graph" format -- the original ss-ums export: 15 columns headed ``Id``,
  ``Display Name``, ``Given Name``, ``User Principal Name``, ``User Type``, ...

Both readers use ``utf-8-sig``. That one change fixes the mp-active-users
bug where the BOM on the first header made every display name load as "".
Rows are validated, never crash on a missing boolean column, and importing
the same file twice upserts instead of hitting the primary key twice.
"""

from __future__ import annotations

import csv
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from .directory import DirectoryUser, parse_bool, parse_datetime


@dataclass
class ImportResult:
    rows_read: int = 0
    imported: int = 0  # newly inserted
    updated: int = 0  # already existed, fields refreshed
    skipped: int = 0
    errors: list[str] = field(default_factory=list)


def _clean(row: dict) -> dict:
    """Strip whitespace from header names and values; tolerate a BOM header."""
    out = {}
    for key, value in row.items():
        if key is None:
            continue
        clean_key = key.strip().lstrip("\ufeff")
        out[clean_key] = value.strip() if isinstance(value, str) else value
    return out


def _from_admin(row: dict) -> DirectoryUser:
    upn = row.get("User principal name", "")
    blocked = parse_bool(row.get("Block credential"))
    return DirectoryUser(
        display_name=row.get("Display name", ""),
        user_principal_name=upn,
        object_id=row.get("Object Id", ""),
        first_name=row.get("First name") or None,
        last_name=row.get("Last name") or None,
        mail=upn or None,
        job_title=row.get("Title") or None,
        department=row.get("Department") or None,
        office_location=row.get("Office") or None,
        city=row.get("City") or None,
        country_or_region=row.get("CountryOrRegion") or None,
        mobile_phone=row.get("Mobile Phone") or None,
        account_enabled=not blocked,
        user_type="Guest" if "#EXT#" in upn else "Member",
        licenses=row.get("Licenses") or None,
        when_created=parse_datetime(row.get("When created")),
    )


def _from_graph(row: dict) -> DirectoryUser:
    upn = row.get("User Principal Name", "")
    return DirectoryUser(
        display_name=row.get("Display Name", ""),
        user_principal_name=upn,
        object_id=row.get("Id", ""),
        first_name=row.get("Given Name") or None,
        last_name=row.get("Surname") or None,
        mail=row.get("Mail") or upn or None,
        job_title=row.get("Job Title") or None,
        office_location=row.get("Office Location") or None,
        business_phones=row.get("Business Phones") or None,
        mobile_phone=row.get("Mobile Phone") or None,
        is_resource_account=parse_bool(row.get("Is Resource Account")),
        account_enabled=parse_bool(row.get("Account Enabled"))
        if row.get("Account Enabled") not in (None, "") else True,
        user_type=row.get("User Type") or None,
        creation_type=row.get("Creation Type") or None,
        external_user_state=row.get("External User State") or None,
    )


def detect_format(fieldnames: Iterable[str]) -> str:
    names = {name.strip().lstrip("\ufeff") for name in fieldnames if name}
    if "Object Id" in names and "User principal name" in names:
        return "admin"
    if "Id" in names and "User Principal Name" in names:
        return "graph"
    raise ValueError(
        "Unrecognised CSV format: expected the Entra admin export "
        "('Object Id' / 'User principal name') or the Graph export "
        "('Id' / 'User Principal Name')"
    )


def load_users_from_csv(path: str | Path) -> list[DirectoryUser]:
    """Parse either export format into DirectoryUser objects (no database)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            return []
        fmt = detect_format(reader.fieldnames)
        users: list[DirectoryUser] = []
        for raw in reader:
            row = _clean(raw)
            if not any(row.values()):
                continue
            user = _from_admin(row) if fmt == "admin" else _from_graph(row)
            # A row with neither an id nor a UPN cannot be keyed; skip it.
            if not user.object_id and not user.user_principal_name:
                continue
            users.append(user)
    return users


def import_users_to_db(db, users: Iterable[DirectoryUser]) -> ImportResult:
    """Upsert DirectoryUsers into the SQLAlchemy User table, idempotently."""
    from .models import User  # local import: avoids a circular import at load time

    result = ImportResult()
    for user in users:
        result.rows_read += 1
        key = user.object_id or user.user_principal_name
        existing = db.session.get(User, key) if key else None
        if existing is None:
            db.session.add(User.from_directory(user, key=key))
            result.imported += 1
        else:
            existing.update_from_directory(user)
            result.updated += 1
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return result
