"""Tests for sensitive data redaction in proxmox_mcp.core.logger."""

import pytest
from proxmox_mcp.core.logger import redact_arguments


class TestRedactArguments:
    def test_none_input(self):
        assert redact_arguments(None) == {}

    def test_empty_dict(self):
        assert redact_arguments({}) == {}

    def test_non_sensitive_preserved(self):
        args = {"node": "pve1", "vmid": 100}
        result = redact_arguments(args)
        assert result == {"node": "pve1", "vmid": 100}

    def test_password_redacted(self):
        args = {"node": "pve1", "password": "s3cret"}
        result = redact_arguments(args)
        assert result["password"] == "[REDACTED]"
        assert result["node"] == "pve1"

    def test_token_redacted(self):
        args = {"token": "abc123"}
        assert redact_arguments(args)["token"] == "[REDACTED]"

    def test_sshkeys_redacted(self):
        args = {"sshkeys": "ssh-rsa AAAA..."}
        assert redact_arguments(args)["sshkeys"] == "[REDACTED]"

    def test_ssh_public_keys_redacted(self):
        args = {"ssh-public-keys": "ssh-rsa AAAA..."}
        assert redact_arguments(args)["ssh-public-keys"] == "[REDACTED]"

    def test_cipassword_redacted(self):
        args = {"cipassword": "secret"}
        assert redact_arguments(args)["cipassword"] == "[REDACTED]"

    def test_net0_redacted(self):
        args = {"net0": "name=eth0,bridge=vmbr0,ip=10.0.0.2/24"}
        assert redact_arguments(args)["net0"] == "[REDACTED]"

    def test_ipconfig0_redacted(self):
        args = {"ipconfig0": "ip=dhcp"}
        assert redact_arguments(args)["ipconfig0"] == "[REDACTED]"

    def test_confirm_vmid_redacted(self):
        args = {"confirm_vmid": 100}
        assert redact_arguments(args)["confirm_vmid"] == "[REDACTED]"

    def test_original_not_mutated(self):
        args = {"password": "s3cret", "node": "pve1"}
        redact_arguments(args)
        assert args["password"] == "s3cret"

    def test_substring_match(self):
        """Keys containing sensitive substrings are also redacted."""
        args = {"my_password_field": "val"}
        assert redact_arguments(args)["my_password_field"] == "[REDACTED]"
