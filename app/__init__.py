"""Flask app factory. The original used a module-global app/db singleton
and created tables only as a side effect of run.py; the factory makes the
app testable and lets the CLI and the web server share one code path.
"""

from __future__ import annotations

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(config=None):
    app = Flask(__name__)
    if config is None:
        from .config import Config

        config = Config
    app.config.from_object(config)

    db.init_app(app)

    from . import models  # noqa: F401  (registers the User model)
    from .routes import bp

    app.register_blueprint(bp)

    with app.app_context():
        db.create_all()

    return app
