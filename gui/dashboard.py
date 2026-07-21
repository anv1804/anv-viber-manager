"""
gui/dashboard.py — Main application window after login.

Core responsibilities:
  - Display and manage list of Viber profiles (local folders).
  - Launch / stop individual Viber instances with isolated HOME + TMPDIR.
  - CRUD: create, rename, delete profiles.
  - Export / import profiles as .viberprofile archives.
  - Sync All: upload from source machine → Telegram → download on this machine.
  - Background loop: sync profile list to Supabase + process remote commands.
"""
import os
import sys
import shutil
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timezone

import services.supabase as db
import services.telegram as tg
from utils.profile import (
    detect_viber_path, get_profile_phone, get_viber_pc_dir,
    pack_profile_to_zip, unpack_profile_zip,
)
from utils.crypto import get_profile_key, encrypt_file, decrypt_file
from config import (
    BG_MAIN, BG_SIDEBAR, BG_CARD, TEXT_MAIN, TEXT_MUTED,
    VIBER_PURPLE, VIBER_HOVER, STOP_RED, STOP_HOVER,
    BTN_DARK, BTN_DARK_HOVER, BORDER_COLOR, SUPABASE_URL,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe_name(s: str) -> str:
    return "".join(c for c in s if c.isalnum() or c in "-_ ").strip()


def _script_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────

class Dashboard:
    SYNC_INTERVAL = 15  # seconds between background syncs

    def __init__(self, root: tk.Tk, user_id: str, username: str,
                 expires_info: str, role: str = "user"):
        self.root = root
        self.user_id = user_id
        self.username = username
        self.expires_info = expires_info
        self.role = role

        self.script_dir = _script_dir()
        self.profiles_dir = os.path.join(self.script_dir, "viber_profiles", username)
        os.makedirs(self.profiles_dir, exist_ok=True)

        self.viber_path: str | None = detect_viber_path()
        self.running: dict[str, bool] = {}   # profile_name → True if running
        self._all_profiles: list[dict] = []  # cache for filter

        self.root.title("ANV Viber Manager")
        self.root.geometry("900x620")
        self.root.configure(bg=BG_MAIN)
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.root.destroy)
        self._center()

        self._setup_styles()
        self._build_ui()
        self._load_profiles()
        self._poll_running(first=True)
        self._start_bg_loop()

    # ──────────────────────────────────────── layout ──────────────────────────

    def _center(self):
        self.root.update_idletasks()
        w, h = 900, 620
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _setup_styles(self):
        s = ttk.Style()
        s.theme_use("clam")
        for name, bg, hover in [
            ("Primary.TButton", VIBER_PURPLE, VIBER_HOVER),
            ("Danger.TButton",  STOP_RED,    STOP_HOVER),
            ("Dark.TButton",    BTN_DARK,    BTN_DARK_HOVER),
        ]:
            s.configure(name, background=bg, foreground="white",
                        font=("Segoe UI", 9, "bold"), borderwidth=0, relief="flat")
            s.map(name, background=[("active", hover)])
        s.configure("Treeview", background=BG_CARD, foreground=TEXT_MAIN,
                    fieldbackground=BG_CARD, rowheight=32, borderwidth=0,
                    font=("Segoe UI", 9))
        s.configure("Treeview.Heading", background=BG_SIDEBAR, foreground=TEXT_MUTED,
                    font=("Segoe UI", 9, "bold"), borderwidth=0)
        s.map("Treeview", background=[("selected", "#2D2D3A")], foreground=[("selected", TEXT_MAIN)])

    def _build_ui(self):
        # ── top bar ──────────────────────────────────────────────────────────
        top = tk.Frame(self.root, bg=BG_SIDEBAR, height=56)
        top.pack(fill=tk.X, side=tk.TOP)
        top.pack_propagate(False)

        tk.Label(top, text="ANV VIBER", font=("Segoe UI", 14, "bold"),
                 bg=BG_SIDEBAR, fg=VIBER_PURPLE).pack(side=tk.LEFT, padx=20)

        right_info = tk.Frame(top, bg=BG_SIDEBAR)
        right_info.pack(side=tk.RIGHT, padx=20)
        tk.Label(right_info, text=f"👤 {self.username}  |  🗓 {self.expires_info}",
                 font=("Segoe UI", 9), bg=BG_SIDEBAR, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 10))
        if self.role == "admin":
            ttk.Button(right_info, text="Admin", style="Dark.TButton",
                       command=self._open_admin).pack(side=tk.LEFT, padx=4)
        ttk.Button(right_info, text="Sign Out", style="Danger.TButton",
                   command=self._logout).pack(side=tk.LEFT, padx=4)

        # ── viber path bar ────────────────────────────────────────────────────
        path_bar = tk.Frame(self.root, bg=BG_SIDEBAR, height=38)
        path_bar.pack(fill=tk.X)
        path_bar.pack_propagate(False)

        self._lbl_path = tk.Label(path_bar, text="Viber Path",
                                  font=("Segoe UI", 8), bg=BG_SIDEBAR, fg=TEXT_MUTED)
        self._lbl_path.pack(side=tk.LEFT, padx=10)

        self._path_var = tk.StringVar(value=self.viber_path or "")
        self._path_var.trace_add("write", self._on_path_change)
        path_entry = tk.Entry(path_bar, textvariable=self._path_var, bg=BG_MAIN,
                              fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
                              font=("Segoe UI", 9), bd=0, relief=tk.FLAT, width=48)
        path_entry.pack(side=tk.LEFT, padx=6, ipady=3)

        ttk.Button(path_bar, text="Browse", style="Dark.TButton",
                   command=self._browse_viber).pack(side=tk.LEFT, padx=4)
        ttk.Button(path_bar, text="Auto-Detect", style="Dark.TButton",
                   command=self._auto_detect).pack(side=tk.LEFT, padx=4)
        self._update_path_label()

        # ── action toolbar ────────────────────────────────────────────────────
        toolbar = tk.Frame(self.root, bg=BG_MAIN, pady=8)
        toolbar.pack(fill=tk.X, padx=12)

        def tb(text, style, cmd, **kw):
            b = ttk.Button(toolbar, text=text, style=style, command=cmd, **kw)
            b.pack(side=tk.LEFT, padx=3, ipady=4)
            return b

        tb("+ New",    "Primary.TButton", self._create_profile)
        tb("▶ Launch", "Primary.TButton", self._launch_selected)
        tb("⏹ Stop",   "Dark.TButton",    self._stop_selected)
        tb("🗑 Delete", "Danger.TButton",  self._delete_selected)
        tb("📤 Export", "Dark.TButton",    self._export_profile)
        tb("📥 Import", "Dark.TButton",    self._import_profile)
        tb("☁ Sync All","Primary.TButton", self._sync_all)

        # filters
        filt = tk.Frame(toolbar, bg=BG_MAIN)
        filt.pack(side=tk.RIGHT)
        self._f_name  = tk.StringVar()
        self._f_phone = tk.StringVar()
        self._f_status = tk.StringVar(value="All")
        for var, ph in [(self._f_name, "Name…"), (self._f_phone, "Phone…")]:
            e = tk.Entry(filt, textvariable=var, bg=BG_CARD, fg=TEXT_MAIN,
                         insertbackground=TEXT_MAIN, font=("Segoe UI", 9), bd=0, width=12)
            e.pack(side=tk.LEFT, padx=3, ipady=3)
            var.trace_add("write", lambda *_: self._apply_filter())
        ttk.Combobox(filt, textvariable=self._f_status, values=["All", "Running", "Idle"],
                     state="readonly", width=8, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=3)
        self._f_status.trace_add("write", lambda *_: self._apply_filter())
        ttk.Button(filt, text="✕", style="Dark.TButton", command=self._clear_filter,
                   width=2).pack(side=tk.LEFT, padx=2)

        # ── profile table ─────────────────────────────────────────────────────
        table_frame = tk.Frame(self.root, bg=BG_MAIN)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        cols = ("#", "No", "Name", "Phone", "Status", "Actions")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings",
                                 selectmode="extended")
        widths = [44, 44, 200, 140, 80, 200]
        for col, w in zip(cols, widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, minwidth=w, stretch=False)

        vsb = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<<TreeviewSelect>>", lambda _: self._refresh_btn_states())

        # ── status bar ────────────────────────────────────────────────────────
        self._status_bar = tk.Label(self.root, text="Ready", font=("Segoe UI", 8),
                                    bg=BG_SIDEBAR, fg=TEXT_MUTED, anchor="w")
        self._status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    # ──────────────────────────────────────── profile loading ─────────────────

    def _load_profiles(self):
        self._all_profiles = []
        if os.path.exists(self.profiles_dir):
            for name in sorted(os.listdir(self.profiles_dir)):
                if os.path.isdir(os.path.join(self.profiles_dir, name)):
                    self._all_profiles.append({
                        "name": name,
                        "phone": get_profile_phone(self.profiles_dir, name),
                        "status": "Running" if name in self.running else "Idle",
                    })
        self._apply_filter()

    def _apply_filter(self):
        sel_names = {self.tree.item(i, "values")[2]
                     for i in self.tree.selection()
                     if len(self.tree.item(i, "values")) > 2}
        for i in self.tree.get_children():
            self.tree.delete(i)

        fn = self._f_name.get().strip().lower()
        fp = self._f_phone.get().strip()
        fs = self._f_status.get()

        idx = 1
        for p in self._all_profiles:
            if fn and fn not in p["name"].lower():
                continue
            if fp and fp not in p["phone"]:
                continue
            if fs != "All" and p["status"] != fs:
                continue
            sel_glyph = "✓" if p["name"] in sel_names else ""
            running = p["name"] in self.running
            actions = "Stop | Rename | Del" if running else "▶ | Rename | Del"
            iid = self.tree.insert("", tk.END, values=(
                sel_glyph, idx, p["name"], p["phone"], p["status"], actions))
            if p["name"] in sel_names:
                self.tree.selection_add(iid)
            idx += 1
        self._refresh_btn_states()

    def _clear_filter(self):
        self._f_name.set("")
        self._f_phone.set("")
        self._f_status.set("All")

    def _refresh_btn_states(self):
        pass  # buttons always enabled; actions check selection internally

    # ──────────────────────────────────────── process tracking ────────────────

    def _poll_running(self, first=False):
        changed = False
        if os.path.exists(self.profiles_dir):
            for name in os.listdir(self.profiles_dir):
                if not os.path.isdir(os.path.join(self.profiles_dir, name)):
                    continue
                pids = self._get_pids(name)
                was = name in self.running
                now = bool(pids)
                if now and not was:
                    self.running[name] = True; changed = True
                elif not now and was:
                    del self.running[name]; changed = True
        if changed or first:
            self._load_profiles()
        self.root.after(1500, self._poll_running)

    def _get_pids(self, name: str) -> list[int]:
        home_dir = os.path.abspath(
            os.path.join(self.profiles_dir, name, "data", "Home"))
        pids = []
        if not os.path.exists("/proc"):
            return pids
        for pid_str in os.listdir("/proc"):
            if not pid_str.isdigit():
                continue
            try:
                with open(f"/proc/{pid_str}/cmdline", "rb") as f:
                    if b"viber" not in f.read().lower():
                        continue
                with open(f"/proc/{pid_str}/environ", "rb") as f:
                    env = f.read()
                for var in env.split(b"\x00"):
                    if var.startswith(b"HOME=") and \
                            os.path.abspath(var[5:].decode(errors="ignore")) == home_dir:
                        pids.append(int(pid_str))
                        break
            except Exception:
                continue
        return pids

    # ──────────────────────────────────────── launch / stop ───────────────────

    def _launch_selected(self):
        names = self._selected_names()
        if not names:
            return messagebox.showwarning("No Selection", "Select at least one profile.")
        if not self.viber_path:
            return messagebox.showerror("Error", "Viber path not configured.")
        for name in names:
            self._launch_one(name)
        self._load_profiles()

    def _launch_one(self, name: str):
        if name in self.running:
            return
        home = os.path.join(self.profiles_dir, name, "data", "Home")
        tmp  = os.path.join(self.profiles_dir, name, "data", "Tmp")
        os.makedirs(home, exist_ok=True)
        os.makedirs(tmp, exist_ok=True)
        env = os.environ.copy()
        env.update({"HOME": home, "TMPDIR": tmp, "TMP": tmp, "TEMP": tmp})
        try:
            cmd = [self.viber_path]
            kw: dict = {"env": env, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
            if sys.platform.startswith("win") or os.name == "nt":
                if self.viber_path.startswith("/"):  # Linux path under Wine
                    cmd = ["start", "/unix", self.viber_path]
                else:
                    kw["creationflags"] = 0x00000008
            else:
                kw["start_new_session"] = True
            subprocess.Popen(cmd, **kw)
            self.running[name] = True
        except Exception as e:
            messagebox.showerror("Launch Error", f"'{name}': {e}")

    def _stop_selected(self):
        for name in self._selected_names():
            self._stop_one(name)
        self._load_profiles()

    def _stop_one(self, name: str):
        for pid in self._get_pids(name):
            try:
                subprocess.run(["kill", "-9", str(pid)],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        self.running.pop(name, None)

    # ──────────────────────────────────────── CRUD ────────────────────────────

    def _create_profile(self):
        self._dialog("Create Profile", "Profile name:", "", self._do_create)

    def _do_create(self, name: str):
        safe = _safe_name(name)
        if not safe:
            return messagebox.showerror("Error", "Invalid name.")
        dest = os.path.join(self.profiles_dir, safe)
        if os.path.exists(dest):
            return messagebox.showerror("Error", "Profile already exists.")
        os.makedirs(os.path.join(dest, "data", "Home"), exist_ok=True)
        self._load_profiles()
        self._bg_sync_list()

    def _delete_selected(self):
        names = self._selected_names()
        if not names:
            return
        if not messagebox.askyesno("Confirm Delete",
                                   f"Delete {len(names)} profile(s)?\nThis cannot be undone."):
            return
        for name in names:
            self._stop_one(name)
            profile_dir = os.path.join(self.profiles_dir, name)
            # Unmount any stuck FUSE mounts
            tmp = os.path.join(profile_dir, "data", "Tmp")
            if os.path.exists(tmp):
                for item in os.listdir(tmp):
                    if item.startswith(".mount_viber"):
                        subprocess.run(["fusermount", "-u", "-z", os.path.join(tmp, item)],
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            shutil.rmtree(profile_dir, ignore_errors=True)
        self._load_profiles()
        self._bg_sync_list()

    def _rename_profile(self, old_name: str):
        self._dialog("Rename Profile", f"Rename '{old_name}' to:", old_name,
                     lambda new: self._do_rename(old_name, new))

    def _do_rename(self, old: str, new: str):
        safe = _safe_name(new)
        if not safe or safe == old:
            return
        dest = os.path.join(self.profiles_dir, safe)
        if os.path.exists(dest):
            return messagebox.showerror("Error", "Name already exists.")
        self._stop_one(old)
        shutil.move(os.path.join(self.profiles_dir, old), dest)
        self._load_profiles()
        self._bg_sync_list()

    # ──────────────────────────────────────── export / import ─────────────────

    def _export_profile(self):
        names = self._selected_names()
        if not names:
            return messagebox.showwarning("No Selection", "Select at least one profile.")
        if len(names) == 1:
            path = filedialog.asksaveasfilename(
                initialfile=f"{names[0]}.viberprofile",
                filetypes=[("Viber Profile", "*.viberprofile")],
                defaultextension=".viberprofile")
            if path:
                self._do_export(names[0], path)
        else:
            d = filedialog.askdirectory()
            if d:
                ok = sum(1 for n in names
                         if self._do_export(n, os.path.join(d, f"{n}.viberprofile"), quiet=True))
                messagebox.showinfo("Done", f"Exported {ok}/{len(names)}.")

    def _do_export(self, name: str, path: str, quiet=False) -> bool:
        vd = get_viber_pc_dir(os.path.join(self.profiles_dir, name))
        if not vd or not os.listdir(vd):
            if not quiet:
                messagebox.showerror("Export Failed", f"No data for '{name}'.")
            return False
        try:
            pack_profile_to_zip(vd, path)
            if not quiet:
                messagebox.showinfo("Exported", f"Saved to:\n{path}")
            return True
        except Exception as e:
            if not quiet:
                messagebox.showerror("Export Error", str(e))
            return False

    def _import_profile(self):
        paths = filedialog.askopenfilenames(filetypes=[("Viber Profile", "*.viberprofile")])
        if not paths:
            return
        ok = 0
        for p in paths:
            base = _safe_name(os.path.splitext(os.path.basename(p))[0])
            dest = os.path.join(self.profiles_dir, base)
            n = 1
            while os.path.exists(dest):
                dest = os.path.join(self.profiles_dir, f"{base}_{n}"); n += 1
            try:
                unpack_profile_zip(p, dest); ok += 1
            except Exception as e:
                shutil.rmtree(dest, ignore_errors=True)
                messagebox.showerror("Import Error", f"'{base}': {e}")
        self._load_profiles()
        if ok:
            messagebox.showinfo("Imported", f"Imported {ok} profile(s).")

    # ──────────────────────────────────────── sync all ────────────────────────

    def _sync_all(self):
        if not SUPABASE_URL or SUPABASE_URL == "https://your-project.supabase.co":
            return messagebox.showwarning("Unavailable", "Requires Supabase configuration.")

        headers = db.make_headers()
        remote = db.get_client_profiles(self.user_id, headers)
        if not remote:
            return messagebox.showinfo("Nothing to Sync", "No profiles in database.")

        names = [r["profile_name"] for r in remote]
        if not messagebox.askyesno("Confirm Sync", f"Sync {len(names)} profile(s) from cloud?"):
            return

        total = len(names)
        win = self._progress_window("Syncing Profiles", total)
        lbl_main, lbl_detail, bar, lbl_cnt = win

        def worker():
            # First handle any pending DOWNLOAD commands
            try:
                for cmd in db.get_pending_commands(self.user_id, headers):
                    if cmd.get("command") == "DOWNLOAD_PROFILE":
                        if lbl_detail.winfo_exists():
                            lbl_detail.config(text=f"Importing pushed: {cmd.get('profile_name')}")
                        self._process_remote_command(cmd, headers)
            except Exception:
                pass

            ok, failed = 0, []
            for idx, name in enumerate(names):
                try:
                    if lbl_main.winfo_exists():
                        lbl_main.config(text=f"Syncing: {name}")
                    # Request upload from source machine
                    db.post_command({
                        "user_id": self.user_id, "command": "UPLOAD_PROFILE",
                        "profile_name": name, "status": "pending"
                    }, headers)
                    cmd = db.get_latest_command(self.user_id, name, "UPLOAD_PROFILE", headers)
                    if not cmd:
                        raise RuntimeError("Command not registered.")
                    cmd_id = cmd["id"]

                    # Poll up to 90 s
                    file_id = None
                    deadline = time.time() + 90
                    while time.time() < deadline:
                        time.sleep(2)
                        rec = db.poll_command(cmd_id, headers)
                        if rec:
                            if rec.get("status") == "completed":
                                file_id = rec.get("telegram_file_id"); break
                            if rec.get("status") == "failed":
                                raise RuntimeError("Upload failed on source.")
                    if not file_id:
                        raise TimeoutError("Upload timed out (90 s).")

                    # Download and decrypt
                    actual_id = file_id.split("|", 1)[0] if "|" in file_id else file_id
                    zip_path = os.path.join(self.script_dir, f"{name}_sync.zip")
                    if lbl_detail.winfo_exists():
                        lbl_detail.config(text="Downloading…")
                    tg.download_file(actual_id, zip_path)
                    key = get_profile_key(self.user_id, name)
                    decrypt_file(zip_path, key)
                    dest = os.path.join(self.profiles_dir, name)
                    self._stop_one(name)
                    unpack_profile_zip(zip_path, dest)
                    os.remove(zip_path)
                    db.delete_command(cmd_id, headers)
                    ok += 1
                except Exception as e:
                    failed.append(f"{name}: {e}")
                finally:
                    if bar.winfo_exists():
                        bar["value"] = idx + 1
                        lbl_cnt.config(text=f"{idx + 1} / {total}")

            if lbl_main.winfo_exists():
                lbl_main.winfo_toplevel().destroy()
            self.root.after(0, self._load_profiles)
            self._bg_sync_list()
            if failed:
                messagebox.showwarning("Done with errors",
                                       f"✅ {ok}/{total}\n\n❌ Failed:\n" + "\n".join(failed))
            else:
                messagebox.showinfo("Sync Complete", f"✅ {ok}/{total} profiles synced!")

        threading.Thread(target=worker, daemon=True).start()

    # ──────────────────────────────────────── background loop ─────────────────

    def _start_bg_loop(self):
        if not SUPABASE_URL or SUPABASE_URL == "https://your-project.supabase.co":
            return

        def worker():
            headers = db.make_headers()
            while True:
                try:
                    for cmd in db.get_pending_commands(self.user_id, headers):
                        self._process_remote_command(cmd, headers)
                    self._bg_sync_list(headers=headers)
                except Exception:
                    pass
                time.sleep(self.SYNC_INTERVAL)

        threading.Thread(target=worker, daemon=True).start()

    def _bg_sync_list(self, headers=None):
        """Push current profile list to Supabase (metadata only, no files)."""
        def _run():
            h = headers or db.make_headers()
            profiles = []
            if os.path.exists(self.profiles_dir):
                for name in os.listdir(self.profiles_dir):
                    if not os.path.isdir(os.path.join(self.profiles_dir, name)):
                        continue
                    profiles.append({
                        "user_id":      self.user_id,
                        "profile_name": name,
                        "phone_number": get_profile_phone(self.profiles_dir, name),
                        "status":       "running" if name in self.running else "idle",
                        "updated_at":   datetime.utcnow().isoformat() + "Z",
                    })
            db.sync_profiles(profiles, self.user_id, h)
        threading.Thread(target=_run, daemon=True).start()

    def _process_remote_command(self, cmd: dict, headers: dict):
        """Execute a remote command (UPLOAD or DOWNLOAD)."""
        cmd_id   = cmd["id"]
        cmd_type = cmd["command"]
        name     = cmd["profile_name"]

        db.update_command_status(cmd_id, "processing", headers)
        try:
            if cmd_type == "UPLOAD_PROFILE":
                profile_path = os.path.join(self.profiles_dir, name)
                if not os.path.exists(profile_path):
                    db.update_command_status(cmd_id, "pending", headers)
                    return  # Let another machine handle it

                viber_pc = get_viber_pc_dir(profile_path)
                if not viber_pc or not os.path.exists(viber_pc) or not os.listdir(viber_pc):
                    # Create a minimal placeholder so pack doesn't crash
                    viber_pc = os.path.join(profile_path, "data", "Home", ".ViberPC")
                    os.makedirs(viber_pc, exist_ok=True)
                    with open(os.path.join(viber_pc, "viber.db"), "w") as f:
                        f.write("PLACEHOLDER")

                # Delete old Telegram message if we can find it
                old_msg_id = self._get_old_msg_id(name, headers)

                zip_path = os.path.join(self.script_dir, f"{name}_upload.zip")
                pack_profile_to_zip(viber_pc, zip_path)
                key = get_profile_key(self.user_id, name)
                encrypt_file(zip_path, key)
                file_id, msg_id = tg.upload_file(
                    zip_path, caption=f"Backup: {name}",
                    filename=f"{name}.viberprofile")
                os.remove(zip_path)

                composite = f"{file_id}|{msg_id}"
                db.update_profile_file_id(self.user_id, name, composite, headers)
                db.update_command_status(cmd_id, "completed", headers,
                                         telegram_file_id=composite)
                if old_msg_id:
                    threading.Thread(target=lambda: tg.delete_message(old_msg_id),
                                     daemon=True).start()

            elif cmd_type == "DOWNLOAD_PROFILE":
                fid_payload = cmd.get("telegram_file_id") or ""
                if not fid_payload:
                    raise ValueError("Missing file_id.")
                actual_id, orig_name = (fid_payload.split("|", 1)
                                        if "|" in fid_payload else (fid_payload, name))
                dest_name = name
                dest_path = os.path.join(self.profiles_dir, dest_name)
                n = 1
                while os.path.exists(dest_path):
                    dest_name = f"{name} ({n})"
                    dest_path = os.path.join(self.profiles_dir, dest_name)
                    n += 1

                zip_path = os.path.join(self.script_dir, f"{dest_name}_down.zip")
                tg.download_file(actual_id, zip_path)
                key = get_profile_key(self.user_id, orig_name)
                decrypt_file(zip_path, key)
                self._stop_one(dest_name)
                unpack_profile_zip(zip_path, dest_path)
                os.remove(zip_path)
                db.update_command_status(cmd_id, "completed", headers)
                self.root.after(0, self._load_profiles)
                self._bg_sync_list(headers=headers)

        except Exception as e:
            import traceback; traceback.print_exc()
            db.update_command_status(cmd_id, "failed", headers)

    def _get_old_msg_id(self, name: str, headers: dict) -> int | None:
        try:
            for p in db.get_client_profiles(self.user_id, headers):
                if p["profile_name"] == name:
                    val = p.get("telegram_file_id", "")
                    if val and "|" in val:
                        _, mid = val.split("|", 1)
                        if mid.isdigit():
                            return int(mid)
        except Exception:
            pass
        return None

    # ──────────────────────────────────────── table interaction ───────────────

    def _on_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return
        item = self.tree.identify_row(event.y)
        col  = self.tree.identify_column(event.x)
        vals = self.tree.item(item, "values")
        if not vals or len(vals) < 3:
            return
        name = vals[2]

        if col == "#4":  # phone → copy
            phone = vals[3]
            if phone and phone != "—":
                self.root.clipboard_clear()
                self.root.clipboard_append(phone)
                self._set_status(f"Copied {phone}!")
            return "break"

        if col == "#6":  # action buttons
            bbox = self.tree.bbox(item, col)
            if bbox:
                x_rel = event.x - bbox[0]
                third = bbox[2] / 3
                if x_rel < third:
                    self._stop_one(name) if name in self.running else self._launch_one(name)
                    self._load_profiles()
                elif x_rel < 2 * third:
                    self._rename_profile(name)
                else:
                    sel = self._selected_names()
                    if name not in sel:
                        sel = [name]
                    orig = self._selected_names()
                    # temporary override
                    self._selected_names_override = [name]
                    self._delete_selected()
                    self._selected_names_override = None
            return "break"

        # toggle row selection
        if item in self.tree.selection():
            self.tree.selection_remove(item)
        else:
            self.tree.selection_add(item)
        self._update_sel_glyphs()
        return "break"

    def _update_sel_glyphs(self):
        sel = set(self.tree.selection())
        for item in self.tree.get_children():
            vals = list(self.tree.item(item, "values"))
            if vals:
                vals[0] = "✓" if item in sel else ""
                self.tree.item(item, values=vals)

    # ──────────────────────────────────────── selection helpers ───────────────

    def _selected_names(self) -> list[str]:
        if hasattr(self, "_selected_names_override") and self._selected_names_override:
            return self._selected_names_override
        return [self.tree.item(i, "values")[2]
                for i in self.tree.selection()
                if len(self.tree.item(i, "values")) > 2]

    # ──────────────────────────────────────── path helpers ────────────────────

    def _on_path_change(self, *_):
        p = self._path_var.get().strip()
        self.viber_path = p if os.path.isfile(p) else None
        self._update_path_label()

    def _update_path_label(self):
        if self.viber_path:
            self._lbl_path.config(text="Viber Path ✓", fg="#12B76A")
        else:
            self._lbl_path.config(text="Viber Path ✗", fg=STOP_RED)

    def _browse_viber(self):
        ft = [("Executables", "*.exe")] if sys.platform.startswith("win") else [("All", "*")]
        p = filedialog.askopenfilename(title="Select Viber", filetypes=ft)
        if p:
            self._path_var.set(p)

    def _auto_detect(self):
        p = detect_viber_path()
        if p:
            self._path_var.set(p)
            messagebox.showinfo("Found", f"Viber found at:\n{p}")
        else:
            messagebox.showwarning("Not Found", "Could not auto-locate Viber.")

    # ──────────────────────────────────────── admin / logout ──────────────────

    def _open_admin(self):
        from gui.admin import AdminPanel
        AdminPanel(self.root)

    def _logout(self):
        if messagebox.askyesno("Sign Out", "Sign out?"):
            self.root.destroy()

    # ──────────────────────────────────────── ui utils ────────────────────────

    def _set_status(self, msg: str, ms: int = 2500):
        self._status_bar.config(text=msg)
        self.root.after(ms, lambda: self._status_bar.config(text="Ready"))

    def _dialog(self, title: str, prompt: str, default: str, callback):
        d = tk.Toplevel(self.root)
        d.title(title)
        d.geometry("300x160")
        d.configure(bg=BG_SIDEBAR)
        d.resizable(False, False)
        d.transient(self.root)
        d.wait_visibility()
        d.grab_set()
        tk.Label(d, text=prompt, bg=BG_SIDEBAR, fg=TEXT_MAIN,
                 font=("Segoe UI", 9, "bold")).pack(pady=(20, 5))
        e = tk.Entry(d, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
                     font=("Segoe UI", 10), bd=0, relief=tk.FLAT)
        e.pack(fill=tk.X, padx=30, pady=5, ipady=4)
        e.insert(0, default)
        e.focus_set()

        def confirm():
            val = e.get().strip()
            d.destroy()
            if val:
                callback(val)

        d.bind("<Return>", lambda _: confirm())
        ttk.Button(d, text="OK", style="Primary.TButton", command=confirm).pack(
            pady=10, ipady=3, padx=30, fill=tk.X)

    def _progress_window(self, title: str, total: int):
        w = tk.Toplevel(self.root)
        w.title(title)
        w.geometry("440x200")
        w.configure(bg=BG_SIDEBAR)
        w.resizable(False, False)
        w.transient(self.root)
        w.wait_visibility()
        w.grab_set()
        lbl_main = tk.Label(w, text="Initializing…", font=("Segoe UI", 10, "bold"),
                            bg=BG_SIDEBAR, fg=TEXT_MAIN)
        lbl_main.pack(pady=(20, 4))
        lbl_detail = tk.Label(w, text="", font=("Segoe UI", 9), bg=BG_SIDEBAR, fg=TEXT_MUTED)
        lbl_detail.pack(pady=(0, 8))
        bar = ttk.Progressbar(w, mode="determinate", length=360, maximum=total)
        bar.pack(pady=4)
        lbl_cnt = tk.Label(w, text=f"0 / {total}", font=("Segoe UI", 9),
                           bg=BG_SIDEBAR, fg=TEXT_MUTED)
        lbl_cnt.pack(pady=4)
        return lbl_main, lbl_detail, bar, lbl_cnt
