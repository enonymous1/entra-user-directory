"""SQLAlchemy model for a directory user.

The original ss-ums model covered only the 15-column Graph export. This
superset also stores the admin-export fields the reporter needs (department,
licenses, when_created, country/region) so the viewer and the report read
from the same table instead of from two different CSVs.
"""

from __future__ import annotations

from . import db
from .directory import DirectoryUser


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.String, primary_key=True)
    display_name = db.Column(db.String(200))
    given_name = db.Column(db.String(100))
    surname = db.Column(db.String(100))
    user_principal_name = db.Column(db.String(200))
    mail = db.Column(db.String(200))
    job_title = db.Column(db.String(200))
    department = db.Column(db.String(200))
    office_location = db.Column(db.String(200))
    city = db.Column(db.String(100))
    country_or_region = db.Column(db.String(100))
    business_phones = db.Column(db.String(200))
    mobile_phone = db.Column(db.String(100))
    is_resource_account = db.Column(db.Boolean, default=False)
    account_enabled = db.Column(db.Boolean, default=True)
    user_type = db.Column(db.String(100))
    creation_type = db.Column(db.String(100))
    external_user_state = db.Column(db.String(100))
    licenses = db.Column(db.String(500))
    when_created = db.Column(db.DateTime, nullable=True)

    @classmethod
    def from_directory(cls, user: DirectoryUser, key: str) -> User:
        obj = cls(id=key)
        obj.update_from_directory(user)
        return obj

    def update_from_directory(self, user: DirectoryUser) -> None:
        self.display_name = user.display_name
        self.given_name = user.first_name
        self.surname = user.last_name
        self.user_principal_name = user.user_principal_name
        self.mail = user.mail
        self.job_title = user.job_title
        self.department = user.department
        self.office_location = user.office_location
        self.city = user.city
        self.country_or_region = user.country_or_region
        self.business_phones = user.business_phones
        self.mobile_phone = user.mobile_phone
        self.is_resource_account = user.is_resource_account
        self.account_enabled = user.account_enabled
        self.user_type = user.user_type
        self.creation_type = user.creation_type
        self.external_user_state = user.external_user_state
        self.licenses = user.licenses
        self.when_created = user.when_created

    def to_directory(self) -> DirectoryUser:
        return DirectoryUser(
            display_name=self.display_name or "",
            user_principal_name=self.user_principal_name or "",
            object_id=self.id or "",
            first_name=self.given_name,
            last_name=self.surname,
            mail=self.mail,
            job_title=self.job_title,
            department=self.department,
            office_location=self.office_location,
            city=self.city,
            country_or_region=self.country_or_region,
            business_phones=self.business_phones,
            mobile_phone=self.mobile_phone,
            is_resource_account=bool(self.is_resource_account),
            account_enabled=bool(self.account_enabled),
            user_type=self.user_type,
            creation_type=self.creation_type,
            external_user_state=self.external_user_state,
            licenses=self.licenses,
            when_created=self.when_created,
        )

    def __repr__(self) -> str:
        return f"<User {self.display_name}>"
