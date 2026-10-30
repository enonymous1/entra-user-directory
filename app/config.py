"""Configuration. The original config.py was a one-line placeholder and the
original app hard-coded debug=True with no SECRET_KEY; both are fixed here.
"""

import os
from pathlib import Path


class Config:
    SECRET_KEY = os.environ.get("UMS_SECRET_KEY", "dev-only-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "UMS_DATABASE_URI",
        "sqlite:///" + str(Path(__file__).resolve().parent / "users.db"),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UMS_PAGE_SIZE = 25


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SECRET_KEY = "test-secret"
