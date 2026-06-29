import os
import logging
import copy
from typing import Any, Dict, Optional
from logging.handlers import RotatingFileHandler

SENSITIVE_KEYS = {
    "password", "token", "sshkeys", "ssh-public-keys",
    "cipassword", "PROXMOX_TOKEN_VALUE", "confirm_vmid",
    "net0", "ipconfig0"
}


def redact_arguments(args: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Returns a copy of the arguments with sensitive data masked."""
    if args is None:
        return {}
    redacted = copy.deepcopy(args)
    for key in redacted:
        if any(sk in key.lower() for sk in SENSITIVE_KEYS):
            redacted[key] = "[REDACTED]"
    return redacted


def setup_logger(project_root: str) -> logging.Logger:
    """Configures and returns the project-wide logger."""
    log_file = os.path.join(project_root, "proxmox-mcp.log")
    handler = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger = logging.getLogger("proxmox-mcp")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logger.addHandler(handler)
    return logger
