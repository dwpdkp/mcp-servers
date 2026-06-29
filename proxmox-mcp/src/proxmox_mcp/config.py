"""Centralised configuration — env vars, client init, safety policy."""

from __future__ import annotations

import os
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
PROXMOX_VERIFY_SSL = os.getenv("PROXMOX_VERIFY_SSL", "true").lower() == "true"
PROXMOX_ALLOW_DANGER = os.getenv("PROXMOX_ALLOW_DANGER", "false").lower() == "true"
PROXMOX_SSH_USER = os.getenv("PROXMOX_SSH_USER", "ansible")

SAFETY_POLICY = load_safety_policy(PROJECT_ROOT)

proxmox_client = ProxmoxClient(
    url=PROXMOX_URL,
    token_name=PROXMOX_TOKEN_NAME,
    token_value=PROXMOX_TOKEN_VALUE,
    verify_ssl=PROXMOX_VERIFY_SSL,
)
