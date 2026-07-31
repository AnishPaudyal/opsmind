"""ASGI entry point for the OpsMind backend."""

from opsmind.application import create_app

app = create_app()
