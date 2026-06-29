"""Tests for safety policy file loading."""

import json
import os
import pytest

from proxmox_mcp.core.safety import load_safety_policy


class TestLoadSafetyPolicy:
    def test_valid_policy_file(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        policy = {
            "safe_tools": ["list_nodes"],
            "safe_command_patterns": ["^ls"],
            "restricted_tools": ["power_control"],
        }
        (config_dir / "safety_policy.json").write_text(json.dumps(policy))
        result = load_safety_policy(str(tmp_path))
        assert result["safe_tools"] == ["list_nodes"]
        assert result["restricted_tools"] == ["power_control"]

    def test_missing_file_returns_fallback(self, tmp_path):
        result = load_safety_policy(str(tmp_path))
        assert result == {"safe_tools": [], "safe_command_patterns": []}

    def test_invalid_json_returns_fallback(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "safety_policy.json").write_text("not json {{{")
        result = load_safety_policy(str(tmp_path))
        assert result == {"safe_tools": [], "safe_command_patterns": []}

    def test_empty_file_returns_fallback(self, tmp_path):
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "safety_policy.json").write_text("")
        result = load_safety_policy(str(tmp_path))
        assert result == {"safe_tools": [], "safe_command_patterns": []}
