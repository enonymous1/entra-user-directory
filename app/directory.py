"""Shared directory-user model, used by the CSV importers and the PDF reporter.

This is the mp-active-users model, modernised: a plain dataclass instead of a
161-line hand-written ``__init__``, with the two bugs fixed that the audit
found -- ``is_licensed`` always returns a real bool, and boolean parsing never
crashes on a missing column.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


def parse_bool(value: object) -> bool:
    """Parse a CSV boolean cell. Missing/blank cells are False, never a crash."""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "yes", "1"}


def parse_datetime(value: object) -> datetime | None:
    """Parse an Entra export timestamp, or None when the cell is blank/unparseable."""
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S%z", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


@dataclass
class DirectoryUser:
    display_name: str = ""
    user_principal_name: str = ""
    object_id: str = ""
    first_name: str | None = None
    last_name: str | None = None
    mail: str | None = None
    job_title: str | None = None
    department: str | None = None
    office_location: str | None = None
    city: str | None = None
    country_or_region: str | None = None
    business_phones: str | None = None
    mobile_phone: str | None = None
    is_resource_account: bool = False
    account_enabled: bool = True
    user_type: str | None = None
    creation_type: str | None = None
    external_user_state: str | None = None
    licenses: str | None = None
    when_created: datetime | None = None

    @property
    def full_name(self) -> str:
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.display_name

    @property
    def is_external_user(self) -> bool:
        """External (guest) users carry #EXT# in their user principal name."""
        if self.user_type and self.user_type.strip().lower() == "guest":
            return True
        return "#EXT#" in (self.user_principal_name or "")

    @property
    def is_licensed(self) -> bool:
        # Always a bool: the original returned "" for an empty license string.
        if not self.licenses:
            return False
        return self.licenses.strip().lower() != "unlicensed"

    @property
    def license_list(self) -> list[str]:
        """Split a '+'-joined license cell into individual license names."""
        if not self.licenses or self.licenses.strip().lower() == "unlicensed":
            return []
        return [part.strip() for part in self.licenses.split("+") if part.strip()]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.mail or self.user_principal_name})"
