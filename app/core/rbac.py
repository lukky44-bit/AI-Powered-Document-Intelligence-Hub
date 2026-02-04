ROLE_MODE_MAP = {
    "lawyer": ["legal"],
    "doctor": ["healthcare"],
    "researcher": ["academic"],
    "finance": ["finance"],
    "business": ["business"],
    "admin": ["legal", "finance", "academic", "healthcare", "business", "general"],
}
ROLE_DOMAIN_MAP = {
    "lawyer": ["legal"],
    "doctor": ["healthcare"],
    "researcher": ["academic"],
    "finance": ["finance"],
    "business": ["business"],
    "admin": None,
}


def get_allowed_modes(roles: list[str]) -> list[str]:
    """Get all allowed modes for a list of roles."""
    if "admin" in roles:
        return ROLE_MODE_MAP["admin"]

    allowed_modes = set()
    for role in roles:
        modes = ROLE_MODE_MAP.get(role, [])
        allowed_modes.update(modes)
    return list(allowed_modes)


def get_allowed_domains(roles: list[str]) -> list[str] | None:
    """Get all allowed domains for a list of roles. Returns None for admin (all access)."""
    if "admin" in roles:
        return None  # Admin has access to all domains

    allowed_domains = set()
    for role in roles:
        domains = ROLE_DOMAIN_MAP.get(role)
        if domains:
            allowed_domains.update(domains)
    return list(allowed_domains) if allowed_domains else []


def has_admin_role(roles: list[str]) -> bool:
    """Check if the user has admin role."""
    return "admin" in roles


def can_access_mode(roles: list[str], mode: str) -> bool:
    """Check if any of the user's roles can access the given mode."""
    allowed_modes = get_allowed_modes(roles)
    return mode in allowed_modes


def can_access_domain(roles: list[str], domain: str) -> bool:
    """Check if any of the user's roles can access the given domain."""
    allowed_domains = get_allowed_domains(roles)
    if allowed_domains is None:  # Admin
        return True
    return domain in allowed_domains
