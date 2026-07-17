"""
services/supabase.py
Thin wrapper around the Supabase REST API for all database operations.
All functions accept an explicit `headers` dict so no global state is needed.
"""
import hashlib
from datetime import datetime

import requests

from config import SUPABASE_URL, SUPABASE_KEY


def make_headers() -> dict:
    """Return standard Supabase REST API request headers."""
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

def get_user_by_username(username: str, headers: dict) -> dict | None:
    """Fetch a single user record by username, or None if not found."""
    url = f"{SUPABASE_URL}/rest/v1/users?username=eq.{username}"
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code != 200:
        raise ConnectionError(f"Database error: {resp.status_code}")
    records = resp.json()
    return records[0] if records else None


def bind_hwid(user_id: str, hwid: str, headers: dict) -> bool:
    """Write the HWID for a user on first login. Returns True on success."""
    url = f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}"
    resp = requests.patch(url, json={"hwid": hwid}, headers=headers, timeout=10)
    return resp.status_code in (200, 204)


# ---------------------------------------------------------------------------
# Profile sync
# ---------------------------------------------------------------------------

def sync_profiles(profiles: list[dict], user_id: str, headers: dict) -> None:
    """Sync local profiles to client_profiles table.
    Safely deletes existing database entries with the same profile_name individually before posting 
    to prevent duplication even if unique constraints are missing on the database.
    """
    if not profiles:
        return

    # Deduplicate payload in Python first (group by profile_name, keep latest)
    unique_profiles = {}
    for p in profiles:
        pname = p["profile_name"]
        if pname not in unique_profiles or p.get("updated_at", "") > unique_profiles[pname].get("updated_at", ""):
            unique_profiles[pname] = p
    final_payload = list(unique_profiles.values())

    # Delete existing profiles of the same name individually to ensure no duplicates
    for p in final_payload:
        pname = p["profile_name"]
        del_url = f"{SUPABASE_URL}/rest/v1/client_profiles?user_id=eq.{user_id}&profile_name=eq.{pname}"
        requests.delete(del_url, headers=headers, timeout=10)

    # Insert updated profiles
    post_url = f"{SUPABASE_URL}/rest/v1/client_profiles"
    requests.post(post_url, json=final_payload, headers=headers, timeout=10)


def update_profile_file_id(user_id: str, profile_name: str, file_id: str, headers: dict) -> None:
    """Update telegram_file_id for a single profile row."""
    url = (
        f"{SUPABASE_URL}/rest/v1/client_profiles"
        f"?user_id=eq.{user_id}&profile_name=eq.{profile_name}"
    )
    requests.patch(url, json={"telegram_file_id": file_id}, headers=headers, timeout=10)


# ---------------------------------------------------------------------------
# Remote commands
# ---------------------------------------------------------------------------

def get_pending_commands(user_id: str, headers: dict) -> list[dict]:
    """Return all pending remote_commands rows for *user_id*."""
    url = (
        f"{SUPABASE_URL}/rest/v1/remote_commands"
        f"?user_id=eq.{user_id}&status=eq.pending"
    )
    resp = requests.get(url, headers=headers, timeout=10)
    return resp.json() if resp.status_code == 200 else []


def update_command_status(
    cmd_id: str,
    status: str,
    headers: dict,
    telegram_file_id: str | None = None,
) -> None:
    """Patch a remote_commands row with a new status (and optional file_id)."""
    url = f"{SUPABASE_URL}/rest/v1/remote_commands?id=eq.{cmd_id}"
    payload: dict = {"status": status}
    if telegram_file_id is not None:
        payload["telegram_file_id"] = telegram_file_id
    requests.patch(url, json=payload, headers=headers, timeout=10)


def delete_command(cmd_id: str, headers: dict) -> None:
    """Delete a single remote_commands row."""
    url = f"{SUPABASE_URL}/rest/v1/remote_commands?id=eq.{cmd_id}"
    requests.delete(url, headers=headers, timeout=10)


def post_command(payload: dict, headers: dict) -> None:
    """Insert a new remote_commands row."""
    url = f"{SUPABASE_URL}/rest/v1/remote_commands"
    resp = requests.post(url, json=payload, headers=headers, timeout=10)
    if resp.status_code not in (200, 201, 204):
        raise RuntimeError(f"Failed to post command: {resp.text}")


def get_latest_command(
    user_id: str,
    profile_name: str,
    command: str,
    headers: dict,
) -> dict | None:
    """Fetch the most-recently created command for (user, profile, type)."""
    url = (
        f"{SUPABASE_URL}/rest/v1/remote_commands"
        f"?user_id=eq.{user_id}"
        f"&profile_name=eq.{profile_name}"
        f"&command=eq.{command}"
        f"&order=created_at.desc"
    )
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code == 200 and resp.json():
        return resp.json()[0]
    return None


def poll_command(cmd_id: str, headers: dict) -> dict | None:
    """Return the current state of a single command row."""
    url = f"{SUPABASE_URL}/rest/v1/remote_commands?id=eq.{cmd_id}"
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code == 200 and resp.json():
        return resp.json()[0]
    return None


# ---------------------------------------------------------------------------
# Admin — user management
# ---------------------------------------------------------------------------

def get_all_users(headers: dict) -> list[dict]:
    url = f"{SUPABASE_URL}/rest/v1/users?order=username.asc"
    resp = requests.get(url, headers=headers, timeout=10)
    return resp.json() if resp.status_code == 200 else []


def create_user(payload: dict, headers: dict) -> requests.Response:
    url = f"{SUPABASE_URL}/rest/v1/users"
    return requests.post(url, json=payload, headers=headers, timeout=10)


def update_user(user_id: str, payload: dict, headers: dict) -> requests.Response:
    url = f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}"
    return requests.patch(url, json=payload, headers=headers, timeout=10)


def delete_user(user_id: str, headers: dict) -> requests.Response:
    url = f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}"
    return requests.delete(url, headers=headers, timeout=10)


def reset_hwid(user_id: str, headers: dict) -> requests.Response:
    url = f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_id}"
    return requests.patch(url, json={"hwid": None}, headers=headers, timeout=10)


# ---------------------------------------------------------------------------
# Admin — client profiles view
# ---------------------------------------------------------------------------

def get_client_profiles(client_id: str, headers: dict) -> list[dict]:
    # Query with filter first (efficient)
    url = f"{SUPABASE_URL}/rest/v1/client_profiles?user_id=eq.{client_id}&order=profile_name.asc"
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code == 200:
        return resp.json()
        
    # Fallback to query all and filter in Python case-insensitively
    url_fallback = f"{SUPABASE_URL}/rest/v1/client_profiles?order=profile_name.asc"
    resp_fb = requests.get(url_fallback, headers=headers, timeout=10)
    if resp_fb.status_code != 200:
        return []
    
    cid_lower = str(client_id).lower()
    return [r for r in resp_fb.json() if str(r.get("user_id") or "").lower() == cid_lower]
