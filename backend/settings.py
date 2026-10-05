"""Runtime settings read from the environment."""

import os
from dataclasses import dataclass, replace
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
TLS_MODES = ("starttls", "ssl", "none")


@dataclass(frozen=True)
class Smtp:
    """Outgoing mail server settings."""

    host: str
    port: int
    user: str
    password: str
    sender: str
    tls: str = "starttls"

    @property
    def enabled(self) -> bool:
        """Return True when a mail host and sender are configured."""
        return bool(self.host and self.sender)


@dataclass(frozen=True)
class Settings:
    """Paths, solver limits, mail and access settings."""

    data_dir: Path
    db_path: Path
    solver_time_limit: float
    smtp: Smtp
    app_url: str = ""
    trust_proxy: bool = False
    allow_remote_setup: bool = False
    #: Built-in sample data set the dashboard can switch to; None disables the switch.
    sample_dir: Path | None = None

    def for_data(self, data_dir: Path) -> "Settings":
        """Return these settings reading site data from another folder."""
        return replace(self, data_dir=data_dir)

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
    def meter_path(self) -> Path:
        """Return the uploaded interval meter data path."""
        return self.data_dir / "meter_data.csv"

    @property
    def price_history_path(self) -> Path:
        """Return the price history path."""
        return self.data_dir / "price_history.csv"


def _path(name: str, default: str) -> Path:
    path = Path(os.getenv(name) or default)
    return path if path.is_absolute() else ROOT / path


def _flag(name: str) -> bool:
    return (os.getenv(name) or "").strip().lower() in ("1", "true", "yes")


def _tls() -> str:
    mode = (os.getenv("SMTP_TLS") or "starttls").strip().lower()
    return mode if mode in TLS_MODES else "starttls"


def load_settings() -> Settings:
    """Read settings from the environment and an optional .env file."""
    load_dotenv(ROOT / ".env")
    return Settings(
        data_dir=_path("GRIDSHIFT_DATA_DIR", "data/live"),
        db_path=_path("GRIDSHIFT_DB_PATH", "data/gridshift.db"),
        solver_time_limit=float(os.getenv("GRIDSHIFT_SOLVER_TIME_LIMIT") or 60),
        smtp=Smtp(
            host=os.getenv("SMTP_HOST", ""),
            port=int(os.getenv("SMTP_PORT") or 587),
            user=os.getenv("SMTP_USER", ""),
            password=os.getenv("SMTP_PASSWORD", ""),
            sender=os.getenv("SMTP_FROM", ""),
            tls=_tls(),
        ),
        app_url=(os.getenv("APP_URL") or "").rstrip("/"),
        trust_proxy=_flag("TRUST_PROXY"),
        allow_remote_setup=_flag("GRIDSHIFT_ALLOW_SETUP"),
        sample_dir=None if _flag("GRIDSHIFT_NO_SAMPLE") else _path("GRIDSHIFT_SAMPLE_DIR", "data/holcim"),
    )
