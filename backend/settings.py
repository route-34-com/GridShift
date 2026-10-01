"""Runtime settings read from the environment."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Smtp:
    """Outgoing mail server settings."""

    host: str
    port: int
    user: str
    password: str
    sender: str
    starttls: bool

    @property
    def enabled(self) -> bool:
        """Return True when a mail host is configured."""
        return bool(self.host)


@dataclass(frozen=True)
class Settings:
    """Paths, solver limits and mail settings."""

    data_dir: Path
    db_path: Path
    solver_time_limit: float
    smtp: Smtp

    @property
    def site_path(self) -> Path:
        """Return the site config path."""
        return self.data_dir / "site.yaml"

    @property
    def machines_path(self) -> Path:
        """Return the machines config path."""
        return self.data_dir / "machines.yaml"

    @property
    def demand_path(self) -> Path:
        """Return the demand history path."""
        return self.data_dir / "demand_history.csv"

    @property
    def price_history_path(self) -> Path:
        """Return the price history path."""
        return self.data_dir / "price_history.csv"


def _path(name: str, default: str) -> Path:
    path = Path(os.getenv(name) or default)
    return path if path.is_absolute() else ROOT / path


def load_settings() -> Settings:
    """Read settings from the environment and an optional .env file."""
    load_dotenv(ROOT / ".env")
    return Settings(
        data_dir=_path("GRIDSHIFT_DATA_DIR", "data/sample"),
        db_path=_path("GRIDSHIFT_DB_PATH", "data/gridshift.db"),
        solver_time_limit=float(os.getenv("GRIDSHIFT_SOLVER_TIME_LIMIT") or 60),
        smtp=Smtp(
            host=os.getenv("SMTP_HOST", ""),
            port=int(os.getenv("SMTP_PORT") or 587),
            user=os.getenv("SMTP_USER", ""),
            password=os.getenv("SMTP_PASSWORD", ""),
            sender=os.getenv("SMTP_FROM") or "gridshift@example.com",
            starttls=(os.getenv("SMTP_STARTTLS", "true").lower() != "false"),
        ),
    )
