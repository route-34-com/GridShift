"""Fixed roles and what each role may do."""

ROLES = ("admin", "planner", "viewer")
ROLE_NAMES = {"admin": "Admin", "planner": "Planner", "viewer": "Viewer"}
EVERYONE = frozenset(ROLES)
PLANNERS = frozenset({"admin", "planner"})
ADMINS = frozenset({"admin"})

TABLE: dict[str, frozenset] = {
    "plan.view": EVERYONE,
    "plan.run": PLANNERS,
    "meter.upload": PLANNERS,
    "export": EVERYONE,
    "config.view": EVERYONE,
    "users.manage": ADMINS,
    "audit.view": ADMINS,
    "email.test": ADMINS,
}


def can(user: dict, permission: str) -> bool:
    """Return whether a user's role grants a permission."""
    return user.get("role") in TABLE.get(permission, frozenset())


def permissions_for(role: str) -> list[str]:
    """Return every permission a role has."""
    return sorted(p for p, roles in TABLE.items() if role in roles)
