import re
from typing import Any


def sanitize_identifier(value: Any, allow_colons: bool = False) -> str:
    """Ensures identifiers are alphanumeric (plus underscores/hyphens/dots, optionally colons for UPIDs)."""
    s = str(value)
    # UPIDs from API-token callers end in user@realm!tokenid:, so colon mode allows @ and !
    pattern = r"^[a-zA-Z0-9\._\-:@!]+$" if allow_colons else r"^[a-zA-Z0-9\._\-]+$"
    if not re.match(pattern, s):
        allowed = "alphanumeric characters, dots, underscores, hyphens, colons, @ and !" if allow_colons else "alphanumeric characters, dots, underscores, and hyphens"
        raise ValueError(f"Invalid identifier: '{s}'. Only {allowed} are allowed.")
    return s


def sanitize_vmid(value: Any) -> int:
    """Ensures VMID is a positive integer."""
    try:
        vmid = int(value)
        if vmid <= 0:
            raise ValueError()
        return vmid
    except (ValueError, TypeError):
        raise ValueError(f"Invalid VMID: '{value}'. Must be a positive integer.")
