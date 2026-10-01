"""Load and validate site and machine configuration files."""

from pathlib import Path

import yaml
from pydantic import TypeAdapter, ValidationError

from backend.planner.model import Machine, Site


class ConfigError(ValueError):
    """Raised when a configuration file is missing or invalid."""


def _read_yaml(path: Path) -> object:
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"{path.name} is not valid YAML: {exc}") from exc


def _describe(exc: ValidationError) -> str:
    return "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())


def load_site(path: Path) -> Site:
    """Load the site configuration from YAML."""
    try:
        return Site.model_validate(_read_yaml(path))
    except ValidationError as exc:
        raise ConfigError(f"{path.name} is invalid: {_describe(exc)}") from exc


def load_machines(path: Path) -> list[Machine]:
    """Load the machine list from YAML."""
    data = _read_yaml(path)
    rows = data.get("machines") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ConfigError(f"{path.name} must contain a non-empty 'machines' list")
    try:
        machines = TypeAdapter(list[Machine]).validate_python(rows)
    except ValidationError as exc:
        raise ConfigError(f"{path.name} is invalid: {_describe(exc)}") from exc
    ids = [m.id for m in machines]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ConfigError(f"{path.name} has duplicate machine ids: {', '.join(duplicates)}")
    return machines
