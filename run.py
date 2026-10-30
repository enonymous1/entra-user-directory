"""Backwards-compatible entry point: `python run.py` still starts the server."""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
