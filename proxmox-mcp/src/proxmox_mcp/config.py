"""Centralised configuration — env vars, client init, safety policy."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from proxmox_mcp.api.client import ProxmoxClient
from proxmox_mcp.core.logger import setup_logger
from proxmox_mcp.core.safety import load_safety_policy

# Project root is two levels up from this file (src/proxmox_mcp/config.py -> repo root)
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)

load_dotenv(dotenv_path=os.path.join(PROJECT_ROOT, ".env"))

logger = setup_logger(PROJECT_ROOT)

PROXMOX_URL = os.getenv("PROXMOX_URL")
PROXMOX_TOKEN_NAME = os.getenv("PROXMOX_TOKEN_NAME")
PROXMOX_TOKEN_VALUE = os.getenv("PROXMOX_TOKEN_VALUE")

# TLS verification. Disabling it (PROXMOX_VERIFY_SSL=false) is gated behind a
# SECOND explicit opt-in (PROXMOX_ALLOW_INSECURE_TLS=true) — with verification off,
# the API token is sent to an unverified peer, exposing it to MITM interception.
_raw_verify_ssl = os.getenv("PROXMOX_VERIFY_SSL", "true").lower()
PROXMOX_ALLOW_INSECURE_TLS = os.getenv("PROXMOX_ALLOW_INSECURE_TLS", "false").lower() == "true"
if _raw_verify_ssl in ("false", "0", "no"):
    if not PROXMOX_ALLOW_INSECURE_TLS:
        print(
            "FATAL: PROXMOX_VERIFY_SSL is disabled but PROXMOX_ALLOW_INSECURE_TLS is not set. "
            "Disabling TLS verification sends the Proxmox API token to an unverified peer, "
            "exposing it to man-in-the-middle interception. Prefer installing a trusted cert "
            "on the Proxmox node. To proceed anyway, set PROXMOX_ALLOW_INSECURE_TLS=true.",
            file=sys.stderr,
        )
        sys.exit(1)
    logger.warning(
        "SECURITY: TLS verification DISABLED for Proxmox API (PROXMOX_VERIFY_SSL=false, "
        "PROXMOX_ALLOW_INSECURE_TLS=true). Connections are vulnerable to MITM interception "
        "of the API token. Use only on trusted networks."
    )
    PROXMOX_VERIFY_SSL = False
else:
    PROXMOX_VERIFY_SSL = True

PROXMOX_ALLOW_DANGER = os.getenv("PROXMOX_ALLOW_DANGER", "false").lower() == "true"
PROXMOX_SSH_USER = os.getenv("PROXMOX_SSH_USER", "ansible")

SAFETY_POLICY = load_safety_policy(PROJECT_ROOT)

proxmox_client = ProxmoxClient(
    url=PROXMOX_URL,
    token_name=PROXMOX_TOKEN_NAME,
    token_value=PROXMOX_TOKEN_VALUE,
    verify_ssl=PROXMOX_VERIFY_SSL,
)
