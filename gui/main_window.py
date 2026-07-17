"""
gui/main_window.py
AnvViberManager — the main application window after login.
"""
import os
import sys
import subprocess
import shutil
import zipfile
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import requests

from config import (
    BG_MAIN, BG_SIDEBAR, BG_CARD, TEXT_MAIN, TEXT_MUTED,
    VIBER_PURPLE, VIBER_HOVER, STOP_RED, STOP_HOVER,
    BTN_DARK, BTN_DARK_HOVER, BORDER_COLOR,
    SUPABASE_URL, SUPABASE_KEY,
)
from utils.profile import detect_viber_path, get_profile_phone, get_viber_pc_dir, pack_profile_to_zip, unpack_profile_zip
from utils.crypto import get_profile_key, encrypt_file, decrypt_file
import services.supabase as db
import services.telegram as tg
from services.backup_manager import BackupManager
import gui.main_window_ui as ui


class AnvViberManager:
    def __init__(self, root: tk.Tk, user_id: str, username: str, expires_info: str, role: str = "user"):
        self.root = root
        self.user_id = user_id
        self.username = username
        self.expires_info = expires_info
        self.role = role

        self.root.title("ANV Viber Manager")
        self.root.geometry("860x600")
        self.root.configure(bg=BG_MAIN)
        self.root.resizable(False, False)

        if getattr(sys, "frozen", False):
            # Running as compiled binary (PyInstaller)
            self.script_dir = os.path.dirname(sys.executable)
        else:
            # Running as raw python script
            self.script_dir = os.path.dirname(os.path.abspath(__file__))
            self.script_dir = os.path.normpath(os.path.join(self.script_dir, ".."))

        self.profiles_dir = os.path.join(self.script_dir, "viber_profiles", self.username)
        os.makedirs(self.profiles_dir, exist_ok=True)

        self.selected_profiles: list[str] = []
        self.viber_path: str | None = detect_viber_path()
        self.running_processes: dict = {}
        # Cache of all profile dicts for fast client-side filtering
        self._all_profiles_data: list[dict] = []

        # Initialize Backup Manager Service
        self.backup_mgr = BackupManager(self.script_dir, self.profiles_dir, self.user_id, self.username)

        ui.setup_styles()
        ui.build_ui_layout(self)
        self.load_profiles()
        self._check_running_processes()
        self._start_remote_sync_loop()

    # ------------------------------------------------------------------
    # UI actions mapping
    # ------------------------------------------------------------------

    def _on_path_change(self, *_args):
        path = self.viber_path_var.get().strip()
        if os.path.isfile(path):
            self.viber_path = path
            self.lbl_path.config(text="Viber Path (Detected)", fg="#12B76A")
        else:
            self.viber_path = None
            self.lbl_path.config(text="Viber Path (Not Found)", fg=STOP_RED)
        self._on_profile_select(None)

    def _auto_detect_viber(self):
        path = detect_viber_path()
        if path:
            self.viber_path_var.set(path)
            messagebox.showinfo("Success", f"Automatically located Viber at:\n{path}")
        else:
            messagebox.showwarning("Not Found", "Could not auto-locate Viber. Please select manually.")

    def _browse_viber_path(self):
        ft = [("Executables", "*.exe")] if sys.platform.startswith("win") else [("All Files", "*")]
        path = filedialog.askopenfilename(title="Select Viber Executable", filetypes=ft)
        if path:
            self.viber_path_var.set(path)

    # ------------------------------------------------------------------
    # Profile list & Filters
    # ------------------------------------------------------------------

    def load_profiles(self):
        """Read all profiles from disk into cache, then apply current filters."""
        self._all_profiles_data = []
        if os.path.exists(self.profiles_dir):
            for name in sorted(os.listdir(self.profiles_dir)):
                if os.path.isdir(os.path.join(self.profiles_dir, name)):
                    status = "Running" if name in self.running_processes else "Idle"
                    phone  = get_profile_phone(self.profiles_dir, name)
                    action = "Stop | Edit | Del" if name in self.running_processes else "Play | Edit | Del"
                    self._all_profiles_data.append({
                        "name": name, "phone": phone, "status": status, "action": action
                    })
        self._apply_filter()

    def _apply_filter(self):
        """Filter _all_profiles_data by name/phone/status and refresh the Treeview."""
        selected_names = [
            self.tree.item(i, "values")[2]
            for i in self.tree.selection()
            if len(self.tree.item(i, "values")) > 2
        ]
        for item in self.tree.get_children():
            self.tree.delete(item)

        q_name   = self._filter_name.get().strip().lower()  if hasattr(self, "_filter_name")  else ""
        q_phone  = self._filter_phone.get().strip()         if hasattr(self, "_filter_phone") else ""
        q_status = self._filter_status.get()                if hasattr(self, "_filter_status") else "Tất cả"

        display_idx = 1
        for p in self._all_profiles_data:
            if q_name  and q_name  not in p["name"].lower():
                continue
            if q_phone and q_phone not in p["phone"]:
                continue
            if q_status != "Tất cả" and p["status"] != q_status:
                continue

            iid = self.tree.insert("", tk.END, values=(
                "No", str(display_idx), p["name"], p["phone"], p["status"], p["action"]
            ))
            if p["name"] in selected_names:
                self.tree.selection_add(iid)
            display_idx += 1

        self._update_selection_visuals()

    def _clear_filter(self):
        """Reset all filter fields and refresh the full list."""
        self._filter_name.set("")
        self._filter_phone.set("")
        self._filter_status.set("Tất cả")
        self._apply_filter()

    def _update_selection_visuals(self):
        sel = self.tree.selection()
        # Update checkbox glyphs in the table
        for item in self.tree.get_children():
            vals = list(self.tree.item(item, "values"))
            if not vals:
                continue
            glyph = "Yes" if item in sel else "No"
            if vals[0] != glyph:
                vals[0] = glyph
                self.tree.item(item, values=vals)

        # Update button state
        self.selected_profiles = [
            self.tree.item(i, "values")[2] for i in sel
            if len(self.tree.item(i, "values")) > 2
        ]
        any_sel = len(self.selected_profiles) > 0
        self.btn_launch.config(state=tk.NORMAL if any_sel else tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL if any_sel else tk.DISABLED)
        self.btn_delete.config(state=tk.NORMAL if any_sel else tk.DISABLED)
        self.btn_export.config(state=tk.NORMAL if any_sel else tk.DISABLED)

    def _on_profile_select(self, _event):
        self._update_selection_visuals()

    def select_all_profiles(self):
        for item in self.tree.get_children():
            self.tree.selection_add(item)
        self._on_profile_select(None)

    def deselect_all_profiles(self):
        self.tree.selection_remove(*self.tree.selection())
        self._on_profile_select(None)

    # ------------------------------------------------------------------
    # Viber Launch & Stop Coordination
    # ------------------------------------------------------------------

    def launch_selected_profiles(self):
        if not self.viber_path:
            messagebox.showerror("Error", "Viber executable path not found or configured!")
            return
        for name in self.selected_profiles:
            if name in self.running_processes:
                continue
            profile_dir = os.path.join(self.profiles_dir, name)
            home_dir    = os.path.join(profile_dir, "data", "Home")
            tmp_dir     = os.path.join(profile_dir, "data", "Tmp")
            os.makedirs(home_dir, exist_ok=True)
            os.makedirs(tmp_dir, exist_ok=True)

            env = os.environ.copy()
            env["HOME"] = home_dir
            env["TMPDIR"] = tmp_dir
            env["TMP"] = tmp_dir
            env["TEMP"] = tmp_dir

            try:
                # Under Windows (or Wine spawner), start_new_session=True is not supported and raises WinError 1359.
                # On Windows, we can use creationflags to run detached.
                creationflags = 0
                start_new_session = True
                
                cmd_args = [self.viber_path]

                if sys.platform.startswith("win") or os.name == "nt":
                    start_new_session = False
                    # Check if the viber_path is a Linux path (e.g. starting with /home or containing forward slashes without drive letter)
                    # When running inside Wine, launching a Linux executable (AppImage) directly with Popen fails.
                    # We must wrap it using Wine's "start /unix" helper to delegate back to Linux host!
                    is_linux_path = (self.viber_path.startswith("/") or self.viber_path.startswith("~")) and not (":" in self.viber_path)
                    if is_linux_path:
                        cmd_args = ["start", "/unix", self.viber_path]
                    else:
                        creationflags = 0x00000008  # DETACHED_PROCESS

                subprocess.Popen(
                    cmd_args,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=start_new_session,
                    creationflags=creationflags,
                )
                self.running_processes[name] = True
            except Exception as e:
                messagebox.showerror("Launch Error", f"Failed to start profile '{name}': {e}")
        self.load_profiles()

    def stop_selected_profiles(self):
        for name in self.selected_profiles:
            self.stop_single_profile(name)
        self.load_profiles()

    def stop_single_profile(self, name: str):
        pids = self._get_profile_pids(name)
        for pid in pids:
            try:
                subprocess.run(["kill", "-9", str(pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        if name in self.running_processes:
            del self.running_processes[name]

    def _get_profile_pids(self, name: str) -> list[int]:
        pids = []
        profile_dir = os.path.join(self.profiles_dir, name)
        home_dir    = os.path.abspath(os.path.join(profile_dir, "data", "Home"))

        if not os.path.exists("/proc"):
            return pids

        for pid_str in os.listdir("/proc"):
            if pid_str.isdigit():
                pid = int(pid_str)
                try:
                    # check cmdline for Viber
                    with open(os.path.join("/proc", pid_str, "cmdline"), "rb") as f:
                        cmd = f.read().replace(b"\x00", b" ").decode("utf-8", errors="ignore")
                    if "viber" not in cmd.lower():
                        continue
                except Exception:
                    continue

                # check environment for matching HOME
                env_file = os.path.join("/proc", pid_str, "environ")
                if os.path.exists(env_file):
                    try:
                        with open(env_file, "rb") as f:
                            env_data = f.read()
                        for var in env_data.split(b"\x00"):
                            if var.startswith(b"HOME="):
                                if os.path.abspath(var[5:].decode("utf-8", errors="ignore")) == home_dir:
                                    pids.append(pid)
                                    break
                    except Exception:
                        continue
        return pids

    def _check_running_processes(self):
        changed = False
        if os.path.exists(self.profiles_dir):
            for name in os.listdir(self.profiles_dir):
                if os.path.isdir(os.path.join(self.profiles_dir, name)):
                    is_running = len(self._get_profile_pids(name)) > 0
                    if is_running and name not in self.running_processes:
                        self.running_processes[name] = True
                        changed = True
                    elif not is_running and name in self.running_processes:
                        del self.running_processes[name]
                        changed = True
        if changed:
            self.load_profiles()
            self._on_profile_select(None)
        self.root.after(1000, self._check_running_processes)

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    def create_profile(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Create Profile")
        dialog.geometry("300x150")
        dialog.configure(bg=BG_SIDEBAR)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.wait_visibility()
        dialog.grab_set()

        tk.Label(dialog, text="Enter Profile Name:", bg=BG_SIDEBAR, fg=TEXT_MAIN,
                 font=("Segoe UI", 9, "bold")).pack(pady=(20, 5))
        entry = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
                         font=("Segoe UI", 10), bd=0, relief=tk.FLAT)
        entry.pack(fill=tk.X, padx=30, pady=5, ipady=4)
        entry.focus_set()

        def confirm():
            name = entry.get().strip()
            if not name:
                return
            safe_name = "".join(c for c in name if c.isalnum() or c in "-_ ")
            if not safe_name:
                messagebox.showerror("Error", "Invalid profile name!")
                return
            dest = os.path.join(self.profiles_dir, safe_name)
            if os.path.exists(dest):
                messagebox.showerror("Error", "Profile already exists!")
                return
            os.makedirs(os.path.join(dest, "data", "Home"), exist_ok=True)
            dialog.destroy()
            self.load_profiles()
            self._trigger_immediate_sync()

        ttk.Button(dialog, text="Create", style="Primary.TButton",
                   command=confirm).pack(pady=15, ipady=3, padx=30, fill=tk.X)

    def delete_profiles(self):
        if not self.selected_profiles:
            return
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete {len(self.selected_profiles)} profile(s)?\n"
            "This will delete ALL local files and cannot be undone!"
        ):
            return
        for name in self.selected_profiles:
            self.stop_single_profile(name)
            
            # Clean up stuck FUSE mounts in Tmp folder
            profile_dir = os.path.join(self.profiles_dir, name)
            tmp_dir = os.path.join(profile_dir, "data", "Tmp")
            if os.path.exists(tmp_dir):
                try:
                    for item in os.listdir(tmp_dir):
                        if item.startswith(".mount_viber"):
                            mount_path = os.path.join(tmp_dir, item)
                            # Lazy unmount the FUSE filesystem
                            subprocess.run(
                                ["fusermount", "-u", "-z", mount_path],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL
                            )
                except Exception:
                    pass

            shutil.rmtree(profile_dir, ignore_errors=True)
        self.load_profiles()
        self._trigger_immediate_sync()

    def _rename_profile(self, old_name: str):
        dialog = tk.Toplevel(self.root)
        dialog.title("Rename Profile")
        dialog.geometry("300x150")
        dialog.configure(bg=BG_SIDEBAR)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.wait_visibility()
        dialog.grab_set()

        tk.Label(dialog, text=f"Rename '{old_name}' to:", bg=BG_SIDEBAR, fg=TEXT_MAIN,
                 font=("Segoe UI", 9, "bold")).pack(pady=(20, 5))
        entry = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
                         font=("Segoe UI", 10), bd=0, relief=tk.FLAT)
        entry.pack(fill=tk.X, padx=30, pady=5, ipady=4)
        entry.insert(0, old_name)
        entry.focus_set()

        def confirm():
            new_name = entry.get().strip()
            if not new_name or new_name == old_name:
                dialog.destroy()
                return
            safe_name = "".join(c for c in new_name if c.isalnum() or c in "-_ ")
            if not safe_name:
                messagebox.showerror("Error", "Invalid name!")
                return
            dest = os.path.join(self.profiles_dir, safe_name)
            if os.path.exists(dest):
                messagebox.showerror("Error", "Name already exists!")
                return
            self.stop_single_profile(old_name)
            shutil.move(os.path.join(self.profiles_dir, old_name), dest)
            dialog.destroy()
            self.load_profiles()
            self._trigger_immediate_sync()

        ttk.Button(dialog, text="Rename", style="Primary.TButton",
                   command=confirm).pack(pady=15, ipady=3, padx=30, fill=tk.X)

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def export_profile(self):
        if not self.selected_profiles:
            return
        if len(self.selected_profiles) == 1:
            name = self.selected_profiles[0]
            save_path = filedialog.asksaveasfilename(
                title=f"Export Profile '{name}'",
                initialfile=f"{name}.viberprofile",
                filetypes=[("Viber Profile", "*.viberprofile")],
                defaultextension=".viberprofile",
            )
            if save_path:
                self._do_export(name, save_path)
        else:
            save_dir = filedialog.askdirectory(title="Select Directory to Export Profiles")
            if not save_dir:
                return
            ok = sum(1 for n in self.selected_profiles if self._do_export(n, os.path.join(save_dir, f"{n}.viberprofile"), quiet=True))
            messagebox.showinfo("Export Complete", f"Exported {ok}/{len(self.selected_profiles)} profiles to:\n{save_dir}")

    def _do_export(self, name: str, save_path: str, quiet: bool = False) -> bool:
        viber_pc_dir = get_viber_pc_dir(os.path.join(self.profiles_dir, name))
        if not viber_pc_dir or not os.listdir(viber_pc_dir):
            if not quiet:
                messagebox.showerror("Export Failed", f"No Viber session data found for '{name}'. Run it at least once.")
            return False
        try:
            pack_profile_to_zip(viber_pc_dir, save_path)
            if not quiet:
                messagebox.showinfo("Export Successful", f"Profile exported to:\n{save_path}")
            return True
        except Exception as e:
            if not quiet:
                messagebox.showerror("Export Failed", f"Error exporting '{name}': {e}")
            return False

    def import_profile(self):
        paths = filedialog.askopenfilenames(title="Import Profiles", filetypes=[("Viber Profile", "*.viberprofile")])
        if not paths:
            return
        ok = 0
        for import_path in paths:
            default_name = "".join(c for c in os.path.splitext(os.path.basename(import_path))[0] if c.isalnum() or c in "-_ ")
            target_path  = os.path.join(self.profiles_dir, default_name)
            counter = 1
            final_name = default_name
            while os.path.exists(target_path):
                final_name = f"{default_name}_{counter}"
                target_path = os.path.join(self.profiles_dir, final_name)
                counter += 1
            try:
                unpack_profile_zip(import_path, target_path)
                ok += 1
            except Exception as e:
                shutil.rmtree(target_path, ignore_errors=True)
                messagebox.showerror("Import Failed", f"Could not import '{default_name}': {e}")
        self.load_profiles()
        self._on_profile_select(None)
        if ok > 0:
            messagebox.showinfo("Import Complete", f"Successfully imported {ok} profile(s)!")

    # ------------------------------------------------------------------
    # Open Admin Panel & User Logout
    # ------------------------------------------------------------------

    def _open_user_management(self):
        from gui.user_management import UserManagementWindow
        UserManagementWindow(self.root, self)

    def perform_logout(self):
        if not messagebox.askyesno("Confirm Sign Out", "Are you sure you want to sign out?"):
            return
        self.root.destroy()
        import main as entry
        entry.restart_login()

    # ------------------------------------------------------------------
    # Table click events mapping
    # ------------------------------------------------------------------

    def _on_table_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        item   = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        vals   = self.tree.item(item, "values")
        if not vals or len(vals) <= 2:
            return
        name = vals[2]

        if column == "#4":  # Phone — copy
            phone = vals[3]
            if phone and phone != "—":
                self.root.clipboard_clear()
                self.root.clipboard_append(phone)
                self.root.update()
                self.lbl_path.config(text=f"Copied {phone}!", fg="#12B76A")
                self.root.after(2000, lambda: self.lbl_path.config(
                    text="Viber Path (Detected)" if self.viber_path else "Viber Path (Not Found)",
                    fg="#12B76A" if self.viber_path else STOP_RED,
                ))
            return "break"

        elif column == "#6":  # Action buttons
            bbox = self.tree.bbox(item, column)
            if bbox:
                x_cell = event.x - bbox[0]
                third  = bbox[2] / 3
                if x_cell < third:
                    self.stop_single_profile_action(name) if name in self.running_processes else self.launch_single_profile_action(name)
                elif x_cell < 2 * third:
                    self._rename_profile(name)
                else:
                    self.delete_single_profile_action(name)
            return "break"
        else:
            if item in self.tree.selection():
                self.tree.selection_remove(item)
            else:
                self.tree.selection_add(item)
            self._on_profile_select(None)
            return "break"

    def launch_single_profile_action(self, name: str):
        orig = self.selected_profiles.copy()
        self.selected_profiles = [name]
        self.launch_selected_profiles()
        self._restore_selection(orig)

    def stop_single_profile_action(self, name: str):
        orig = self.selected_profiles.copy()
        self.selected_profiles = [name]
        self.stop_selected_profiles()
        self._restore_selection(orig)

    def delete_single_profile_action(self, name: str):
        orig = self.selected_profiles.copy()
        self.selected_profiles = [name]
        self.delete_profiles()
        self._restore_selection(orig)

    def _restore_selection(self, names: list[str]):
        self.tree.selection_remove(*self.tree.selection())
        for item in self.tree.get_children():
            val = self.tree.item(item, "values")
            if val and len(val) > 2 and val[2] in names:
                self.tree.selection_add(item)
        self._on_profile_select(None)

    def _trigger_immediate_sync(self):
        """Immediately trigger a profile list sync to Supabase in a background thread."""
        def sync_worker():
            try:
                headers = db.make_headers()
                profiles = []
                if os.path.exists(self.profiles_dir):
                    for name in os.listdir(self.profiles_dir):
                        if not os.path.isdir(os.path.join(self.profiles_dir, name)):
                            continue
                        profiles.append({
                            "user_id":      self.user_id,
                            "profile_name": name,
                            "phone_number": get_profile_phone(self.profiles_dir, name),
                            "status":       "running" if name in self.running_processes else "idle",
                            "updated_at":   datetime.utcnow().isoformat() + "Z",
                        })
                db.sync_profiles(profiles, self.user_id, headers)
            except Exception:
                pass
        threading.Thread(target=sync_worker, daemon=True).start()

    # ------------------------------------------------------------------
    # Remote Sync & Auto-Backup Threads Integration
    # ------------------------------------------------------------------

    def _start_remote_sync_loop(self):
        if SUPABASE_URL == "https://your-project.supabase.co" or not SUPABASE_URL:
            return

        def worker():
            headers = db.make_headers()
            first_run = True
            while True:
                try:
                    # 1. Process pending remote commands first (such as DOWNLOAD_PROFILE)
                    # to populate local folders before sync_profiles runs.
                    for cmd in db.get_pending_commands(self.user_id, headers):
                        self._process_remote_command(cmd, headers) # Run synchronously inside loop thread

                    profiles = []
                    if os.path.exists(self.profiles_dir):
                        for name in os.listdir(self.profiles_dir):
                            if not os.path.isdir(os.path.join(self.profiles_dir, name)):
                                continue
                            profiles.append({
                                "user_id":      self.user_id,
                                "profile_name": name,
                                "phone_number": get_profile_phone(self.profiles_dir, name),
                                "status":       "running" if name in self.running_processes else "idle",
                                "updated_at":   datetime.utcnow().isoformat() + "Z",
                            })

                            # Auto-backup has been disabled. Only sync when Sync All is clicked.
                            # viber_pc_dir = get_viber_pc_dir(os.path.join(self.profiles_dir, name))
                            # if viber_pc_dir and os.path.exists(viber_pc_dir) and os.listdir(viber_pc_dir):
                            #     current_mtime = self.backup_mgr.get_dir_mtime(viber_pc_dir)
                            #     if first_run:
                            #         self.backup_mgr.upload_mtimes[name] = current_mtime
                            #         continue

                            #     last_mtime    = self.backup_mgr.upload_mtimes.get(name, 0)
                            #     last_upload_t = self.backup_mgr.upload_timestamps.get(name, 0)
                            #     cooldown_ok   = (time.time() - last_upload_t) >= self.backup_mgr.cooldown_seconds
                            #     if current_mtime != last_mtime and cooldown_ok and name not in self.backup_mgr.uploading_profiles:
                            #         threading.Thread(
                            #             target=self.backup_mgr.auto_upload_profile,
                            #             args=(name, viber_pc_dir, current_mtime, headers),
                            #             daemon=True,
                            #         ).start()

                    first_run = False
                    db.sync_profiles(profiles, self.user_id, headers)

                except Exception:
                    pass
                time.sleep(15)

        threading.Thread(target=worker, daemon=True).start()

    def _process_remote_command(self, cmd: dict, headers: dict):
        cmd_id       = cmd["id"]
        cmd_type     = cmd["command"]
        profile_name = cmd["profile_name"]

        db.update_command_status(cmd_id, "processing", headers)
        try:
            if cmd_type == "UPLOAD_PROFILE":
                profile_path = os.path.join(self.profiles_dir, profile_name)
                if not os.path.exists(profile_path):
                    # We do not have this profile locally. Revert status to pending and ignore so the other machine can process it.
                    db.update_command_status(cmd_id, "pending", headers)
                    print(f"Ignoring UPLOAD_PROFILE for '{profile_name}' because it does not exist locally.")
                    return

                viber_pc_dir = get_viber_pc_dir(profile_path)
                # If viber_pc_dir does not exist or is empty, create dummy files so sync doesn't crash
                if not viber_pc_dir or not os.path.exists(viber_pc_dir) or not os.listdir(viber_pc_dir):
                    data_dir = os.path.join(profile_path, "data")
                    os.makedirs(data_dir, exist_ok=True)
                    if sys.platform.startswith("win"):
                        viber_pc_dir = os.path.join(data_dir, "Roaming", "ViberPC")
                    else:
                        viber_pc_dir = os.path.join(data_dir, "Home", ".ViberPC")
                    os.makedirs(viber_pc_dir, exist_ok=True)
                    # Create a dummy config/db file to bypass empty check
                    dummy_db = os.path.join(viber_pc_dir, "viber.db")
                    with open(dummy_db, "w") as f:
                        f.write("DUMMY_VIBER_DB")

                # Retrieve existing message_id to delete
                existing_msg_id = None
                try:
                    db_profiles = db.get_client_profiles(self.user_id, headers)
                    for p in db_profiles:
                        if p["profile_name"] == profile_name:
                            comp_val = p.get("telegram_file_id")
                            if comp_val and "|" in comp_val:
                                _, msg_id_str = comp_val.split("|", 1)
                                if msg_id_str.isdigit():
                                    existing_msg_id = int(msg_id_str)
                            break
                except Exception:
                    pass

                zip_path = os.path.join(self.script_dir, f"{profile_name}_temp.zip")
                pack_profile_to_zip(viber_pc_dir, zip_path)

                key = get_profile_key(self.user_id, profile_name)
                encrypt_file(zip_path, key)

                file_id, message_id = tg.upload_file(zip_path, caption=f"Backup: {profile_name}", filename=f"{profile_name}.viberprofile")
                os.remove(zip_path)

                composite_value = f"{file_id}|{message_id}"
                db.update_profile_file_id(self.user_id, profile_name, composite_value, headers)
                db.update_command_status(cmd_id, "completed", headers, telegram_file_id=composite_value)

                if existing_msg_id:
                    threading.Thread(target=lambda: tg.delete_message(existing_msg_id), daemon=True).start()

            elif cmd_type == "DOWNLOAD_PROFILE":
                file_id_payload = cmd.get("telegram_file_id")
                if not file_id_payload:
                    raise ValueError("Missing file ID.")

                # If composite payload (file_id|original_name), extract them
                if "|" in file_id_payload:
                    actual_file_id, original_name = file_id_payload.split("|", 1)
                else:
                    actual_file_id = file_id_payload
                    original_name = profile_name

                # Handle folder name collision
                target_dest_name = profile_name
                target_path = os.path.join(self.profiles_dir, target_dest_name)
                
                # If target directory already exists, find a unique suffix name (e.g. "3 (1)")
                if os.path.exists(target_path):
                    counter = 1
                    while os.path.exists(os.path.join(self.profiles_dir, f"{profile_name} ({counter})")):
                        counter += 1
                    target_dest_name = f"{profile_name} ({counter})"
                    target_path = os.path.join(self.profiles_dir, target_dest_name)

                zip_dest = os.path.join(self.script_dir, f"{target_dest_name}_temp_down.zip")
                tg.download_file(actual_file_id, zip_dest)

                # Decrypt using the key configured on original_name
                key = get_profile_key(self.user_id, original_name)
                decrypt_file(zip_dest, key)

                if target_dest_name in self.running_processes:
                    self.stop_single_profile(target_dest_name)

                unpack_profile_zip(zip_dest, target_path)
                os.remove(zip_dest)
                db.update_command_status(cmd_id, "completed", headers)

                # Force immediate DB sync so Admin sees the newly downloaded profile on their view list
                try:
                    sync_list = []
                    if os.path.exists(self.profiles_dir):
                        for name in os.listdir(self.profiles_dir):
                            if os.path.isdir(os.path.join(self.profiles_dir, name)):
                                sync_list.append({
                                    "user_id":      self.user_id,
                                    "profile_name": name,
                                    "phone_number": get_profile_phone(self.profiles_dir, name),
                                    "status":       "running" if name in self.running_processes else "idle",
                                    "updated_at":   datetime.utcnow().isoformat() + "Z",
                                })
                    db.sync_profiles(sync_list, self.user_id, headers)
                except Exception:
                    pass

                self.root.after(0, self.load_profiles)

        except Exception as e:
            import traceback
            print(f"Error processing command {cmd_id}:", e)
            traceback.print_exc()
            db.update_command_status(cmd_id, "failed", headers)

    def sync_all_profiles(self):
        """Sync ALL profiles for this account from the database (other machine)."""
        if SUPABASE_URL == "https://your-project.supabase.co" or not SUPABASE_URL:
            messagebox.showwarning("Sync Unavailable", "Requires Supabase database configuration.")
            return

        headers = db.make_headers()
        remote_profiles = db.get_client_profiles(self.user_id, headers)
        if not remote_profiles:
            messagebox.showinfo("Nothing to Sync", "No profiles found in the database.")
            return

        profile_names = [r["profile_name"] for r in remote_profiles]
        total = len(profile_names)

        if not messagebox.askyesno("Confirm Sync All", f"Sync {total} profiles from cloud?"):
            return

        progress = tk.Toplevel(self.root)
        progress.title("Syncing All Profiles")
        progress.geometry("420x200")
        progress.configure(bg=BG_SIDEBAR)
        progress.resizable(False, False)
        progress.transient(self.root)
        progress.wait_visibility()
        progress.grab_set()

        lbl_main = tk.Label(progress, text="Initializing sync...", font=("Segoe UI", 10, "bold"), bg=BG_SIDEBAR, fg=TEXT_MAIN)
        lbl_main.pack(pady=(20, 5))

        lbl_detail = tk.Label(progress, text="", font=("Segoe UI", 9), bg=BG_SIDEBAR, fg=TEXT_MUTED)
        lbl_detail.pack(pady=(0, 8))

        bar = ttk.Progressbar(progress, mode="determinate", length=340, maximum=total)
        bar.pack(pady=5)

        lbl_count = tk.Label(progress, text=f"0 / {total}", font=("Segoe UI", 9), bg=BG_SIDEBAR, fg=TEXT_MUTED)
        lbl_count.pack(pady=4)

        def worker():
            # 1. Process any pending DOWNLOAD_PROFILE push commands immediately
            lbl_main.config(text="Checking for pushed profiles...")
            downloaded_any = False
            try:
                for cmd in db.get_pending_commands(self.user_id, headers):
                    if cmd.get("command") == "DOWNLOAD_PROFILE":
                        lbl_detail.config(text=f"Importing pushed: {cmd.get('profile_name')}")
                        self._process_remote_command(cmd, headers)
                        downloaded_any = True
            except Exception:
                pass

            if downloaded_any:
                self.root.after(0, self.load_profiles)

            ok = 0
            failed = []
            for idx, name in enumerate(profile_names):
                try:
                    lbl_main.config(text=f"Syncing: {name}")
                    lbl_detail.config(text="Sending upload request...")

                    db.post_command({"user_id": self.user_id, "command": "UPLOAD_PROFILE", "profile_name": name, "status": "pending"}, headers)
                    cmd = db.get_latest_command(self.user_id, name, "UPLOAD_PROFILE", headers)
                    if not cmd:
                        raise RuntimeError("Failed command registration.")
                    cmd_id = cmd["id"]

                    start = time.time()
                    telegram_file_id = None
                    while time.time() - start < 90:
                        time.sleep(2)
                        record = db.poll_command(cmd_id, headers)
                        if record:
                            if record.get("status") == "completed":
                                telegram_file_id = record.get("telegram_file_id")
                                break
                            if record.get("status") == "failed":
                                raise RuntimeError("Upload failed.")

                    if not telegram_file_id:
                        raise TimeoutError("Timeout.")

                    lbl_detail.config(text="Downloading...")
                    actual_file_id = telegram_file_id.split("|", 1)[0] if (telegram_file_id and "|" in telegram_file_id) else telegram_file_id
                    zip_dest = os.path.join(self.script_dir, f"{name}_sync_down.zip")
                    tg.download_file(actual_file_id, zip_dest)

                    key = get_profile_key(self.user_id, name)
                    decrypt_file(zip_dest, key)

                    dest = os.path.join(self.profiles_dir, name)
                    if name in self.running_processes:
                        self.stop_single_profile(name)
                    unpack_profile_zip(zip_dest, dest)
                    os.remove(zip_dest)
                    db.delete_command(cmd_id, headers)
                    ok += 1
                except Exception as e:
                    failed.append(f"{name}: {e}")
                finally:
                    if progress.winfo_exists():
                        bar["value"] = idx + 1
                        lbl_count.config(text=f"{idx + 1} / {total}")

            progress.destroy()
            self.root.after(0, self.load_profiles)
            self._trigger_immediate_sync()

            if failed:
                messagebox.showwarning("Sync Done with Errors", f"✅ {ok}/{total} success.\n\n❌ Failed:\n" + "\n".join(failed))
            else:
                messagebox.showinfo("Sync Complete", f"✅ Sync complete!")

        threading.Thread(target=worker, daemon=True).start()
