"""
utils/profile.py
Helpers for working with local Viber profile directories:
  - detecting the Viber executable path
  - reading the registered phone number from a profile
  - packing / unpacking profile data to/from ZIP archives
"""
import os
import sys
import subprocess
import zipfile
import shutil


# ---------------------------------------------------------------------------
# Viber executable detection
# ---------------------------------------------------------------------------

def detect_viber_path() -> str | None:
    """Auto-detect the Viber executable on Windows or Linux/macOS."""
    # If natively on Windows, check native candidates first
    if sys.platform.startswith("win"):
        user_profile = os.environ.get("USERPROFILE", "C:\\")
        candidates = [
            os.path.join(user_profile, "AppData", "Local", "Viber", "Viber.exe"),
            "C:\\Program Files\\Viber\\Viber.exe",
            "C:\\Program Files (x86)\\Viber\\Viber.exe",
        ]
        for p in candidates:
            if os.path.exists(p):
                return p
        
        # If running under Wine virtualenv on Linux, we can fall back to standard Linux locations
        # since Wine can launch Linux executables/AppImages or map paths
        linux_home = "/home/anv"
        wine_linux_candidates = [
            os.path.join(linux_home, "Downloads", "viber.AppImage"),
            os.path.join(linux_home, "Downloads", "Viber.AppImage"),
        ]
        for p in wine_linux_candidates:
            if os.path.exists(p):
                return p
        return None

    # Linux / macOS - Prioritize user-specific AppImage path first
    home = os.path.expanduser("~")
    candidates = [
        os.path.join(home, "Downloads", "viber.AppImage"),
        os.path.join(home, "Downloads", "Viber.AppImage"),
        "/usr/bin/viber",
        "/opt/viber/Viber",
        "/snap/bin/viber",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p

    try:
        path = subprocess.check_output(["which", "viber"], text=True).strip()
        if path:
            return path
    except subprocess.CalledProcessError:
        pass

    return None


# ---------------------------------------------------------------------------
# Phone number extraction
# ---------------------------------------------------------------------------

def get_profile_phone(profiles_dir: str, name: str) -> str:
    """Return the phone number stored inside a profile, or '—' if not found."""
    profile_path = os.path.join(profiles_dir, name)
    data_dir = os.path.join(profile_path, "data")

    viber_pc_dir = None
    if os.path.exists(os.path.join(data_dir, "Roaming", "ViberPC")):
        viber_pc_dir = os.path.join(data_dir, "Roaming", "ViberPC")
    elif os.path.exists(os.path.join(data_dir, "Home", ".ViberPC")):
        viber_pc_dir = os.path.join(data_dir, "Home", ".ViberPC")

    if viber_pc_dir and os.path.exists(viber_pc_dir):
        for sub in os.listdir(viber_pc_dir):
            sub_path = os.path.join(viber_pc_dir, sub)
            if not os.path.isdir(sub_path):
                continue
            clean = sub.replace("+", "")
            if clean.isdigit() and len(clean) >= 9:
                marker_files = ("Backgrounds", "Temporary", "QmlUrlCache", "viber.db")
                if any(os.path.exists(os.path.join(sub_path, m)) for m in marker_files):
                    return f"+{clean}"
    return "—"


# ---------------------------------------------------------------------------
# Profile ViberPC directory resolver
# ---------------------------------------------------------------------------

def get_viber_pc_dir(profile_path: str) -> str | None:
    """Return the ViberPC data directory inside a profile, or None."""
    data_dir = os.path.join(profile_path, "data")
    win_path = os.path.join(data_dir, "Roaming", "ViberPC")
    lin_path = os.path.join(data_dir, "Home", ".ViberPC")
    if os.path.exists(win_path):
        return win_path
    if os.path.exists(lin_path):
        return lin_path
    return None


# ---------------------------------------------------------------------------
# ZIP pack / unpack
# ---------------------------------------------------------------------------

def pack_profile_to_zip(viber_pc_dir: str, zip_path: str) -> None:
    """Compress the ViberPC directory into *zip_path*, skipping unreadable files/folders."""
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(viber_pc_dir, onerror=lambda e: None):
            # Exclude unreadable directories from traversal
            readable_dirs = []
            for d in dirs:
                full_d = os.path.join(root, d)
                try:
                    os.listdir(full_d)
                    readable_dirs.append(d)
                except OSError:
                    pass
            dirs[:] = readable_dirs

            for fname in files:
                full = os.path.join(root, fname)
                try:
                    rel = os.path.relpath(full, viber_pc_dir)
                    zf.write(full, rel)
                except OSError:
                    pass


def unpack_profile_zip(zip_path: str, dest_profile_path: str) -> None:
    """
    Extract *zip_path* into the correct platform-specific ViberPC directory
    inside *dest_profile_path*, creating all required sub-folders first.
    """
    shutil.rmtree(dest_profile_path, ignore_errors=True)
    data_dir = os.path.join(dest_profile_path, "data")
    os.makedirs(data_dir, exist_ok=True)

    if sys.platform.startswith("win"):
        viber_pc_dest = os.path.join(data_dir, "Roaming", "ViberPC")
        os.makedirs(os.path.join(data_dir, "Local", "Viber"), exist_ok=True)
        os.makedirs(os.path.join(data_dir, "UserProfile"), exist_ok=True)
    else:
        viber_pc_dest = os.path.join(data_dir, "Home", ".ViberPC")
        os.makedirs(os.path.join(data_dir, "Home", ".config", "ViberPC"), exist_ok=True)
        os.makedirs(os.path.join(data_dir, "Home", ".local", "share", "viberpc"), exist_ok=True)

    os.makedirs(viber_pc_dest, exist_ok=True)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(viber_pc_dest)
