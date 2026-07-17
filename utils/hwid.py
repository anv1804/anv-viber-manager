"""
utils/hwid.py
Hardware-ID detection: returns a stable SHA-256 fingerprint of the machine.
Supports Windows (WMIC UUID) and Linux/macOS (machine-id / hostname).
"""
import os
import sys
import subprocess
import hashlib


def get_hwid() -> str:
    """Return a SHA-256 hex string unique to this machine."""
    hwid_str = ""
    try:
        if sys.platform.startswith("win"):
            out = subprocess.check_output("wmic csproduct get uuid", shell=True).decode()
            hwid_str = out.split("\n")[1].strip()
        else:
            for path in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
                if os.path.exists(path):
                    with open(path) as f:
                        hwid_str = f.read().strip()
                    break
            if not hwid_str:
                import socket
                hwid_str = socket.gethostname()
    except Exception:
        import platform
        hwid_str = platform.node() + platform.processor() + platform.machine()

    return hashlib.sha256(hwid_str.encode()).hexdigest()
