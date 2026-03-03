"""WSGI entry point for Gunicorn and Flask dev server.

    Production:  gunicorn src.wsgi:app
    Development: flask --app src.wsgi:app run --debug
"""
from .app import create_app

app = create_app()
