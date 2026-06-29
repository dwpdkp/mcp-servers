"""Shared test fixtures."""

import pytest


@pytest.fixture
def safety_policy():
    """Minimal safety policy for testing."""
    return {
        "safe_tools": ["list_nodes", "list_vms"],
        "safe_command_patterns": ["^ls($| )", "^pwd$"],
        "restricted_tools": ["power_control"],
        "critical_tools": ["delete_instance"],
    }
