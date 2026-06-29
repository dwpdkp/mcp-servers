import pytest
from proxmox_mcp.core.sanitization import sanitize_identifier, sanitize_vmid


def test_valid_identifier():
    assert sanitize_identifier("pve-node1") == "pve-node1"


def test_identifier_with_dots():
    assert sanitize_identifier("local.storage") == "local.storage"


def test_identifier_rejects_shell_chars():
    with pytest.raises(ValueError):
        sanitize_identifier("node; rm -rf /")


def test_identifier_rejects_spaces():
    with pytest.raises(ValueError):
        sanitize_identifier("bad name")


def test_upid_allows_colons():
    assert sanitize_identifier("UPID:pve:00001234:task", allow_colons=True) == "UPID:pve:00001234:task"


def test_upid_rejects_colons_by_default():
    with pytest.raises(ValueError):
        sanitize_identifier("UPID:pve:task")


def test_valid_vmid():
    assert sanitize_vmid(100) == 100
    assert sanitize_vmid("200") == 200


def test_vmid_rejects_zero():
    with pytest.raises(ValueError):
        sanitize_vmid(0)


def test_vmid_rejects_negative():
    with pytest.raises(ValueError):
        sanitize_vmid(-1)


def test_vmid_rejects_string():
    with pytest.raises(ValueError):
        sanitize_vmid("abc")
