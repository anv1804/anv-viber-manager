"""
gui/profile_viewer.py
ClientProfilesViewWindow — Admin view of a client's remote profiles with
pull (request upload from client) and push (send profile to client) actions.
"""
import os
import sys
import shutil
import threading
import time
import zipfile
import requests
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

from config import (
    BG_MAIN, BG_SIDEBAR, BG_CARD, TEXT_MAIN,
    VIBER_PURPLE, STOP_RED,
    SUPABASE_URL,
)
from utils.crypto import get_profile_key, encrypt_file, decrypt_file
from utils.profile import get_viber_pc_dir, pack_profile_to_zip, unpack_profile_zip
import services.supabase as db
import services.telegram as tg


class ClientProfilesViewWindow:
    def __init__(self, parent: tk.Widget, client_id: str, client_username: str, main_app):
        self.parent           = parent
        self.client_id        = client_id
        self.client_username  = client_username
        self.main_app         = main_app  # AnvViberManager instance

        self.window = tk.Toplevel(parent)
        self.window.title(f"Viber Profiles - {client_username}")
        self.window.geometry("540x410")
        self.window.configure(bg=BG_MAIN)
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.wait_visibility()
        self.window.grab_set()

        self.headers = db.make_headers()
        # Cache of full DB rows: profile_name -> row dict (for fast pull)
        self._profile_rows: dict[str, dict] = {}

        self._build_ui()
        self._load_profiles()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Title header
        hdr = tk.Frame(self.window, bg=BG_SIDEBAR, height=45)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text=f"📂 PROFILES OF {self.client_username.upper()}",
                 font=("Segoe UI", 11, "bold"), bg=BG_SIDEBAR, fg=VIBER_PURPLE,
                 ).pack(side=tk.LEFT, padx=15, pady=8)

        content = tk.Frame(self.window, bg=BG_MAIN)
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Bottom buttons
        bottom = tk.Frame(content, bg=BG_MAIN)
        bottom.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        self.btn_pull = ttk.Button(bottom, text="📥 Pull Profile to Admin",
                                   style="Primary.TButton",   command=self._pull_profile, state=tk.DISABLED)
        self.btn_push = ttk.Button(bottom, text="📤 Push Profile to Client",
                                   style="Secondary.TButton", command=self._push_profile)
        self.btn_pull.pack(side=tk.LEFT,  fill=tk.X, expand=True, padx=(0, 5), ipady=5)
        self.btn_push.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0), ipady=5)

        # Table
        card = tk.Frame(content, bg=BG_CARD)
        card.pack(fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(card)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(card, columns=("stt", "name", "phone", "status"),
                                  show="headings", yscrollcommand=sb.set, selectmode="browse")
        for col, text, width in [
            ("stt",    "STT",           50),
            ("name",   "Profile Name", 160),
            ("phone",  "Phone",        160),
            ("status", "Status",       100),
        ]:
            self.tree.heading(col, text=text, anchor=tk.CENTER)
            self.tree.column(col, width=width, anchor=tk.CENTER)

        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        sb.config(command=self.tree.yview)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _load_profiles(self):
        self._profile_rows = {}
        for item in self.tree.get_children():
            self.tree.delete(item)
        try:
            # Enforce absolute uniqueness in Python by keeping only the latest updated record per profile_name
            raw_profiles = db.get_client_profiles(self.client_id, self.headers)
            unique_map = {}
            for r in raw_profiles:
                pname = r["profile_name"]
                # Keep the latest updated record if duplicates exist
                if pname not in unique_map or r.get("updated_at", "") > unique_map[pname].get("updated_at", ""):
                    unique_map[pname] = r

            for idx, (pname, row) in enumerate(sorted(unique_map.items()), 1):
                self._profile_rows[pname] = row
                has_backup = bool(row.get("telegram_file_id"))
                backup_tag = " ✅" if has_backup else " ⏳"
                self.tree.insert("", tk.END, values=(
                    str(idx),
                    pname + backup_tag,
                    row.get("phone_number") or "—",
                    row.get("status") or "idle",
                ))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch profiles: {e}", parent=self.window)

    def _on_select(self, _event):
        self.btn_pull.config(state=tk.NORMAL if self.tree.selection() else tk.DISABLED)

    # ------------------------------------------------------------------
    # Pull: request client → upload → admin downloads
    # ------------------------------------------------------------------

    def _pull_profile(self):
        sel = self.tree.selection()
        if not sel:
            return
        # Strip backup tag suffix from display name
        display_name = self.tree.item(sel[0], "values")[1]
        profile_name = display_name.rstrip("✅⏳ ")

        row = self._profile_rows.get(profile_name, {})
        file_id = row.get("telegram_file_id")

        # Build local save name with client tag
        safe_username = "".join(c for c in self.client_username if c.isalnum() or c in "-_")
        local_name = f"{profile_name}_pull_{safe_username}"
        base_local = local_name
        counter = 1
        while os.path.exists(os.path.join(self.main_app.profiles_dir, local_name)):
            local_name = f"{base_local}_{counter}"
            counter += 1

        # Extract actual Telegram file_id if it's stored in composite "file_id|message_id" format
        actual_file_id = file_id.split("|", 1)[0] if (file_id and "|" in file_id) else file_id

        if not actual_file_id:
            messagebox.showinfo(
                "Backup Not Ready",
                f"Profile '{profile_name}' has not been backed up yet.\n\n"
                f"The client's app automatically backs up profiles when data changes.\n"
                f"Please wait for the client to open the app, then try again.\n\n"
                f"Tip: Profiles with ✅ are ready to pull immediately.",
                parent=self.window,
            )
            return

        if not messagebox.askyesno(
            "Confirm Pull",
            f"Download '{profile_name}' from {self.client_username}?\n"
            f"Will be saved as: '{local_name}'",
            parent=self.window,
        ):
            return

        progress, lbl_status = self._make_progress_dialog("Pulling Profile")

        def worker():
            zip_dest = os.path.join(self.main_app.script_dir, f"{profile_name}_remote_down.zip")
            try:
                lbl_status.config(text="Downloading from Telegram...")
                tg.download_file(actual_file_id, zip_dest)

                lbl_status.config(text="Decrypting...")
                key = get_profile_key(self.client_id, profile_name)
                decrypt_file(zip_dest, key)

                lbl_status.config(text=f"Extracting as '{local_name}'...")
                dest = os.path.join(self.main_app.profiles_dir, local_name)
                if local_name in getattr(self.main_app, "running_processes", {}):
                    self.main_app.stop_single_profile(local_name)
                unpack_profile_zip(zip_dest, dest)
                os.remove(zip_dest)

                progress.destroy()
                if hasattr(self.main_app, "load_profiles"):
                    self.main_app.load_profiles()
                messagebox.showinfo(
                    "Pull Successful ✅",
                    f"Profile '{profile_name}' from {self.client_username}\n"
                    f"saved as: '{local_name}'",
                    parent=self.window,
                )
            except Exception as e:
                if os.path.exists(zip_dest):
                    os.remove(zip_dest)
                progress.destroy()
                messagebox.showerror("Pull Failed", f"{e}", parent=self.window)

        threading.Thread(target=worker, daemon=True).start()

    # ------------------------------------------------------------------
    # Push: admin packs → uploads → client downloads
    # ------------------------------------------------------------------

    def _push_profile(self):
        # 1. Enumerate Admin's local profiles
        local_profiles = []
        if os.path.exists(self.main_app.profiles_dir):
            local_profiles = [
                n for n in os.listdir(self.main_app.profiles_dir)
                if os.path.isdir(os.path.join(self.main_app.profiles_dir, n))
            ]

        if not local_profiles:
            messagebox.showerror("Error", "You have no local profiles to push!", parent=self.window)
            return

        # 2. Profile selection dialog
        dialog = tk.Toplevel(self.window)
        dialog.title("Select Profile to Push")
        dialog.geometry("320x170")
        dialog.configure(bg=BG_SIDEBAR)
        dialog.resizable(False, False)
        dialog.transient(self.window)
        dialog.wait_visibility()
        dialog.grab_set()

        tk.Label(dialog, text="Select Local Profile to Push:", bg=BG_SIDEBAR, fg=TEXT_MAIN,
                 font=("Segoe UI", 9, "bold")).pack(pady=(20, 5))
        combo = ttk.Combobox(dialog, values=sorted(local_profiles), state="readonly")
        combo.pack(fill=tk.X, padx=30, pady=5)
        combo.current(0)

        def confirm_push():
            selected = combo.get()
            dialog.destroy()

            profile_path = os.path.join(self.main_app.profiles_dir, selected)
            viber_pc_dir = get_viber_pc_dir(profile_path)
            if not viber_pc_dir or not os.listdir(viber_pc_dir):
                messagebox.showerror("Push Failed",
                                     f"Profile '{selected}' has no Viber login data!",
                                     parent=self.window)
                return

            # Maintain original profile name when pushing
            target_profile_name = selected

            if not messagebox.askyesno(
                "Confirm Remote Push",
                f"Push '{selected}' to {self.client_username}?\n"
                f"It will be updated on the client machine as:\n→ '{target_profile_name}'",
                parent=self.window,
            ):
                return

            progress, lbl_status = self._make_progress_dialog("Remote Profile Pushing")

            def push_worker():
                zip_path = os.path.join(self.main_app.script_dir, f"{selected}_push_temp.zip")
                try:
                    # 1. Pack + encrypt
                    pack_profile_to_zip(viber_pc_dir, zip_path)
                    key = get_profile_key(self.client_id, selected)
                    encrypt_file(zip_path, key)

                    # 2. Upload to Telegram
                    lbl_status.config(text="Uploading to Telegram...")
                    file_id, message_id = tg.upload_file(
                        zip_path,
                        caption=f"Push: {selected} → {self.client_username}",
                        filename=f"{selected}.viberprofile",
                    )
                    os.remove(zip_path)

                    # 3. Post DOWNLOAD command with the new unique timestamped profile name
                    db.post_command({
                        "user_id":           self.client_id,
                        "command":           "DOWNLOAD_PROFILE",
                        "profile_name":      target_profile_name,
                        "telegram_file_id":  f"{file_id}|{selected}", # Send file_id and original name
                        "status":            "pending",
                    }, self.headers)

                    # 4. Insert placeholder in client_profiles so Admin can see it immediately
                    try:
                        post_url = f"{SUPABASE_URL}/rest/v1/client_profiles"
                        requests.post(post_url, json=[{
                            "user_id":      self.client_id,
                            "profile_name": target_profile_name,
                            "phone_number": "—",
                            "status":       "pushed",
                            "updated_at":   datetime.utcnow().isoformat() + "Z",
                        }], headers=self.headers, timeout=10)
                    except Exception:
                        pass

                    # Success immediately! No waiting.
                    progress.destroy()
                    self._load_profiles()
                    messagebox.showinfo(
                        "Success ✅",
                        f"Profile '{selected}' uploaded to Telegram successfully!\n\n"
                        f"It is saved on the cloud as '{target_profile_name}'.\n"
                        f"The client tool will automatically sync and import it when they open their app.",
                        parent=self.window,
                    )

                except Exception as e:
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
                    progress.destroy()
                    messagebox.showerror("Error", f"Push failed:\n{e}", parent=self.window)

            threading.Thread(target=push_worker, daemon=True).start()

        ttk.Button(dialog, text="Push Profile", style="Primary.TButton",
                   command=confirm_push).pack(pady=15, ipady=3, padx=30, fill=tk.X)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _make_progress_dialog(self, title: str):
        """Create and return (progress_window, status_label)."""
        progress = tk.Toplevel(self.window)
        progress.title(title)
        progress.geometry("380x140")
        progress.configure(bg=BG_SIDEBAR)
        progress.resizable(False, False)
        progress.transient(self.window)
        progress.wait_visibility()
        progress.grab_set()

        lbl = tk.Label(progress, text="Please wait...", bg=BG_SIDEBAR, fg=TEXT_MAIN,
                       font=("Segoe UI", 10, "bold"))
        lbl.pack(pady=(25, 10))

        bar = ttk.Progressbar(progress, mode="indeterminate", length=280)
        bar.pack(pady=5)
        bar.start(10)

        return progress, lbl

    def _poll_until_done(self, cmd_id: str, lbl_status: tk.Label, waiting_text: str, timeout: int = 60):
        """
        Poll a command row every 2 seconds until it reaches 'completed' or 'failed'.
        Returns the telegram_file_id (may be None) on success, raises on failure/timeout.
        """
        start = time.time()
        while time.time() - start < timeout:
            time.sleep(2)
            lbl_status.config(text=waiting_text)
            record = db.poll_command(cmd_id, self.headers)
            if record:
                status = record.get("status")
                if status == "completed":
                    return record.get("telegram_file_id")
                if status == "failed":
                    raise RuntimeError("Remote side reported failure.")
        return None
