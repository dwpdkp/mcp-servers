import re

PERMISSION_MAP = {
    ("GET", "/nodes$"): "Sys.Audit",
    ("GET", "/nodes/.*/lxc$"): "VM.Audit",
    ("GET", "/nodes/.*/qemu$"): "VM.Audit",
    ("GET", "/nodes/.*/lxc/.*/config$"): "VM.Audit",
    ("GET", "/nodes/.*/qemu/.*/config$"): "VM.Audit",
    ("GET", "/nodes/.*/lxc/.*/interfaces$"): "VM.Audit",
    ("POST", "/nodes/.*/lxc/.*/status/.*$"): "VM.PowerMgmt",
    ("POST", "/nodes/.*/qemu/.*/status/.*$"): "VM.PowerMgmt",
    ("GET", "/nodes/.*/storage$"): "Datastore.Audit",
    ("GET", "/nodes/.*/storage/.*/content$"): "Datastore.Audit",
    ("GET", "/nodes/.*/tasks/.*/status$"): "Sys.Audit",
    ("GET", "/nodes/.*/tasks/.*/log$"): "Sys.Audit",
    ("POST", "/nodes/.*/lxc$"): "VM.Allocate, Datastore.AllocateSpace",
    ("POST", "/nodes/.*/lxc/.*/exec$"): "VM.Console",
    ("POST", "/nodes/.*/qemu$"): "VM.Allocate, Datastore.AllocateSpace",
    ("PUT", "/nodes/.*/qemu/.*/config$"): "VM.Config.Cloudinit",
    ("GET", "/nodes/.*/lxc/.*/snapshot$"): "VM.Audit",
    ("GET", "/nodes/.*/qemu/.*/snapshot$"): "VM.Audit",
    ("POST", "/nodes/.*/lxc/.*/snapshot$"): "VM.Snapshot",
    ("POST", "/nodes/.*/qemu/.*/snapshot$"): "VM.Snapshot",
    ("POST", "/nodes/.*/lxc/.*/snapshot/.*/rollback$"): "VM.Snapshot",
    ("POST", "/nodes/.*/qemu/.*/snapshot/.*/rollback$"): "VM.Snapshot",
    ("GET", "/nodes/.*/lxc/.*/rrddata$"): "VM.Audit",
    ("GET", "/nodes/.*/qemu/.*/rrddata$"): "VM.Audit",
    ("DELETE", "/nodes/.*/lxc/.*$"): "VM.Allocate",
    ("DELETE", "/nodes/.*/qemu/.*$"): "VM.Allocate",
}


def get_required_permission(method: str, url: str, base_url: str) -> str:
    """Helper to find matching permission requirement for a URL."""
    path = url.replace(base_url, "")
    for (m, pattern), permission in PERMISSION_MAP.items():
        if m == method and re.match(pattern, path):
            return permission
    return "Required privileges (Unknown endpoint)"
