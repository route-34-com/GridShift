"""Everything a service call needs about the request that made it."""

import sqlite3
from dataclasses import dataclass

from backend.services.audit import SYSTEM, Origin
from backend.settings import Settings


@dataclass
class Ctx:
    """Database connection, settings, signed-in user and request origin."""

    db: sqlite3.Connection
    settings: Settings
    actor: dict | None = None
    origin: Origin = SYSTEM
    base_url: str = ""

    @property
    def app_url(self) -> str:
        """Return the public address used in emailed links."""
        return (self.settings.app_url or self.base_url).rstrip("/")
