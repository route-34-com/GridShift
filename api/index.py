"""Vercel entry point: the GridShift API as one Python function."""

from backend.api.main import app

__all__ = ["app"]
