"""Load, validate and save site and machine configuration files."""

import os
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
    return validate_machines(rows, path.name)


def validate_site(data: object) -> Site:
    """Return a validated site or raise ConfigError with a readable reason."""
    try:
        return Site.model_validate(data)
    except ValidationError as exc:
        raise ConfigError(f"Site settings are invalid: {_describe(exc)}") from exc


def validate_machines(rows: object, source: str = "Machine list") -> list[Machine]:
    """Return validated machines with unique ids or raise ConfigError."""
    if not isinstance(rows, list) or not rows:
        raise ConfigError(f"{source} must contain a non-empty 'machines' list")
    try:
        machines = TypeAdapter(list[Machine]).validate_python(rows)
    except ValidationError as exc:
        raise ConfigError(f"{source} is invalid: {_describe(exc)}") from exc
    ids = [m.id for m in machines]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ConfigError(f"{source} has duplicate machine ids: {', '.join(duplicates)}")
    return machines


def _write_yaml(path: Path, data: object, header: str) -> None:
    """Write YAML atomically so the planner never reads a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = header + yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(text, encoding="utf-8")
    os.replace(temp, path)


def save_site(path: Path, site: Site) -> None:
    """Write the site configuration."""
    _write_yaml(path, site.model_dump(mode="json"), "# Site settings, edited in the GridShift dashboard.\n")


def save_machines(path: Path, machines: list[Machine]) -> None:
    """Write the machine list."""
    rows = [m.model_dump(mode="json", exclude_none=True) for m in machines]
    _write_yaml(path, {"machines": rows}, "# Machines, edited in the GridShift dashboard.\n")
