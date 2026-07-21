"""
gui/admin.py — Admin panel for user management (role=admin only).

Features:
  - List all users
  - Create / edit / delete users
  - Reset HWID
  - View client_profiles per user
  - Send UPLOAD / DOWNLOAD remote commands
"""
import hashlib
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import services.supabase as db
from config import (
    BG_MAIN, BG_SIDEBAR, BG_CARD, TEXT_MAIN, TEXT_MUTED,
    VIBER_PURPLE, VIBER_HOVER, STOP_RED, STOP_HOVER,
    BTN_DARK, BTN_DARK_HOVER,
)


class AdminPanel:
    def __init__(self, parent: tk.Tk):
        self.root = tk.Toplevel(parent)
        self.root.title("Admin Panel — User Management")
        self.root.geometry("860x560")
        self.root.configure(bg=BG_MAIN)
        self.root.resizable(True, True)
        self.root.transient(parent)
        self.root.wait_visibility()
        self.root.grab_set()

        self._headers = db.make_headers()
        self._setup_styles()
        self._build_ui()
        self._load_users()

    # ──────────────────────────────────────── styles ──────────────────────────

    def _setup_styles(self):
        s = ttk.Style()
        for name, bg, hover in [
            ("AP.Primary.TButton", VIBER_PURPLE, VIBER_HOVER),
            ("AP.Danger.TButton",  STOP_RED,    STOP_HOVER),
            ("AP.Dark.TButton",    BTN_DARK,    BTN_DARK_HOVER),
        ]:
            s.configure(name, background=bg, foreground="white",
                        font=("Segoe UI", 9, "bold"), borderwidth=0)
            s.map(name, background=[("active", hover)])
        s.configure("Admin.Treeview", background=BG_CARD, foreground=TEXT_MAIN,
                    fieldbackground=BG_CARD, rowheight=28, borderwidth=0,
                    font=("Segoe UI", 9))
        s.configure("Admin.Treeview.Heading", background=BG_SIDEBAR,
                    foreground=TEXT_MUTED, font=("Segoe UI", 9, "bold"), borderwidth=0)
        s.map("Admin.Treeview",
              background=[("selected", "#2D2D3A")], foreground=[("selected", TEXT_MAIN)])

    # ──────────────────────────────────────── UI ──────────────────────────────

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.root, bg=BG_SIDEBAR, height=48)
        hdr.pack(fill=tk.X)
        hdr.pack_propagate(False)
        tk.Label(hdr, text="Admin Panel", font=("Segoe UI", 13, "bold"),
                 bg=BG_SIDEBAR, fg=VIBER_PURPLE).pack(side=tk.LEFT, padx=16)

        # ── left: user list ───────────────────────────────────────────────────
        pane = tk.PanedWindow(self.root, orient=tk.HORIZONTAL,
                              bg=BG_MAIN, sashwidth=6, sashpad=0)
        pane.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(pane, bg=BG_MAIN)
        pane.add(left, minsize=360)

        # toolbar
        tb = tk.Frame(left, bg=BG_MAIN, pady=8)
        tb.pack(fill=tk.X, padx=8)
        for text, style, cmd in [
            ("+ Add",    "AP.Primary.TButton", self._add_user),
            ("✎ Edit",   "AP.Dark.TButton",    self._edit_user),
            ("🔑 Reset HWID", "AP.Dark.TButton", self._reset_hwid),
            ("🗑 Delete", "AP.Danger.TButton",  self._delete_user),
            ("↺ Refresh", "AP.Dark.TButton",   self._load_users),
        ]:
            ttk.Button(tb, text=text, style=style, command=cmd).pack(
                side=tk.LEFT, padx=2, ipady=3)

        # user table
        cols = ("Username", "Role", "Status", "Created")
        self.user_tree = ttk.Treeview(left, columns=cols, show="headings",
                                      style="Admin.Treeview", selectmode="browse")
        for col, w in zip(cols, [140, 70, 80, 160]):
            self.user_tree.heading(col, text=col)
            self.user_tree.column(col, width=w)
        vsb = ttk.Scrollbar(left, orient="vertical", command=self.user_tree.yview)
        self.user_tree.configure(yscrollcommand=vsb.set)
        self.user_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=4)
        vsb.pack(side=tk.RIGHT, fill=tk.Y, pady=4)
        self.user_tree.bind("<<TreeviewSelect>>", self._on_user_select)

        # ── right: profiles ───────────────────────────────────────────────────
        right = tk.Frame(pane, bg=BG_MAIN)
        pane.add(right, minsize=360)

        tb2 = tk.Frame(right, bg=BG_MAIN, pady=8)
        tb2.pack(fill=tk.X, padx=8)
        tk.Label(tb2, text="Client Profiles", font=("Segoe UI", 10, "bold"),
                 bg=BG_MAIN, fg=TEXT_MAIN).pack(side=tk.LEFT)
        for text, style, cmd in [
            ("↑ Upload", "AP.Primary.TButton", self._cmd_upload),
            ("↓ Download", "AP.Dark.TButton",  self._cmd_download),
        ]:
            ttk.Button(tb2, text=text, style=style, command=cmd).pack(
                side=tk.RIGHT, padx=2, ipady=3)

        p_cols = ("Profile", "Phone", "Status", "Last Update")
        self.profile_tree = ttk.Treeview(right, columns=p_cols, show="headings",
                                         style="Admin.Treeview", selectmode="browse")
        for col, w in zip(p_cols, [120, 120, 70, 180]):
            self.profile_tree.heading(col, text=col)
            self.profile_tree.column(col, width=w)
        vsb2 = ttk.Scrollbar(right, orient="vertical", command=self.profile_tree.yview)
        self.profile_tree.configure(yscrollcommand=vsb2.set)
        self.profile_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0), pady=4)
        vsb2.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

        # status
        self._status = tk.Label(self.root, text="", font=("Segoe UI", 8),
                                bg=BG_SIDEBAR, fg=TEXT_MUTED, anchor="w")
        self._status.pack(fill=tk.X, side=tk.BOTTOM)

    # ──────────────────────────────────────── data loading ────────────────────

    def _load_users(self):
        def run():
            users = db.get_all_users(self._headers)
            self.root.after(0, lambda: self._populate_users(users))
        threading.Thread(target=run, daemon=True).start()
        self._set_status("Loading users…")

    def _populate_users(self, users: list[dict]):
        for i in self.user_tree.get_children():
            self.user_tree.delete(i)
        self._users = users
        for u in users:
            created = (u.get("created_at") or "")[:10]
            self.user_tree.insert("", tk.END, iid=u["id"],
                                  values=(u["username"], u.get("role", "user"),
                                          u.get("status", "active"), created))
        self._set_status(f"{len(users)} user(s) loaded.")

    def _on_user_select(self, _):
        uid = self._selected_uid()
        if not uid:
            return
        threading.Thread(target=self._load_profiles, args=(uid,), daemon=True).start()

    def _load_profiles(self, uid: str):
        profiles = db.get_client_profiles(uid, self._headers)
        self.root.after(0, lambda: self._populate_profiles(profiles))

    def _populate_profiles(self, profiles: list[dict]):
        for i in self.profile_tree.get_children():
            self.profile_tree.delete(i)
        for p in profiles:
            updated = (p.get("updated_at") or "")[:19].replace("T", " ")
            self.profile_tree.insert("", tk.END, iid=p["profile_name"],
                                     values=(p["profile_name"], p.get("phone_number", ""),
                                             p.get("status", ""), updated))

    # ──────────────────────────────────────── user CRUD ───────────────────────

    def _add_user(self):
        self._user_form("Add User", {}, is_new=True)

    def _edit_user(self):
        uid = self._selected_uid()
        if not uid:
            return messagebox.showwarning("Select", "Select a user first.")
        user = next((u for u in self._users if u["id"] == uid), None)
        if user:
            self._user_form("Edit User", user, is_new=False)

    def _user_form(self, title: str, user: dict, is_new: bool):
        d = tk.Toplevel(self.root)
        d.title(title)
        d.geometry("320x340")
        d.configure(bg=BG_SIDEBAR)
        d.resizable(False, False)
        d.transient(self.root)
        d.wait_visibility()
        d.grab_set()

        fields = {}
        for label, key, default in [
            ("Username",    "username", user.get("username", "")),
            ("Password",    "_pw",      ""),
            ("Role",        "role",     user.get("role", "user")),
            ("Status",      "status",   user.get("status", "active")),
            ("Expires (YYYY-MM-DD)", "expires_at", (user.get("expires_at") or "")[:10]),
        ]:
            tk.Label(d, text=label, font=("Segoe UI", 9, "bold"),
                     bg=BG_SIDEBAR, fg=TEXT_MUTED).pack(anchor="w", padx=20, pady=(8, 0))
            if key in ("role", "status"):
                opts = ["admin", "user"] if key == "role" else ["active", "blocked"]
                var = tk.StringVar(value=default)
                ttk.Combobox(d, textvariable=var, values=opts,
                             state="readonly", font=("Segoe UI", 9)).pack(
                    fill=tk.X, padx=20, pady=2)
                fields[key] = var
            else:
                show = "*" if key == "_pw" else ""
                e = tk.Entry(d, show=show, bg=BG_MAIN, fg=TEXT_MAIN,
                             insertbackground=TEXT_MAIN, font=("Segoe UI", 9), bd=0)
                e.insert(0, default)
                e.pack(fill=tk.X, padx=20, pady=2, ipady=3)
                fields[key] = e

        def save():
            payload: dict = {}
            uname = fields["username"].get().strip()
            pw = fields["_pw"].get().strip()
            if not uname:
                return messagebox.showerror("Error", "Username required.")
            payload["username"] = uname
            if pw:
                payload["password_hash"] = hashlib.sha256(pw.encode()).hexdigest()
            payload["role"]   = fields["role"].get()
            payload["status"] = fields["status"].get()
            exp = fields["expires_at"].get().strip()
            if exp:
                payload["expires_at"] = exp + "T00:00:00Z"

            def run():
                if is_new:
                    resp = db.create_user(payload, self._headers)
                else:
                    resp = db.update_user(user["id"], payload, self._headers)
                if resp.status_code in (200, 201, 204):
                    self.root.after(0, self._load_users)
                else:
                    self.root.after(0, lambda: messagebox.showerror(
                        "Error", f"Failed ({resp.status_code}):\n{resp.text[:200]}"))
            threading.Thread(target=run, daemon=True).start()
            d.destroy()

        ttk.Button(d, text="Save", style="AP.Primary.TButton", command=save).pack(
            fill=tk.X, padx=20, pady=14, ipady=5)

    def _reset_hwid(self):
        uid = self._selected_uid()
        if not uid:
            return messagebox.showwarning("Select", "Select a user first.")
        if not messagebox.askyesno("Reset HWID", "Reset hardware ID for this user?"):
            return

        def run():
            resp = db.reset_hwid(uid, self._headers)
            msg = "HWID reset." if resp.status_code in (200, 204) else f"Failed: {resp.text}"
            self.root.after(0, lambda: self._set_status(msg))
        threading.Thread(target=run, daemon=True).start()

    def _delete_user(self):
        uid = self._selected_uid()
        if not uid:
            return messagebox.showwarning("Select", "Select a user first.")
        uname = self.user_tree.item(uid, "values")[0]
        if not messagebox.askyesno("Delete User", f"Delete user '{uname}'? Cannot be undone."):
            return

        def run():
            db.delete_user(uid, self._headers)
            self.root.after(0, self._load_users)
        threading.Thread(target=run, daemon=True).start()

    # ──────────────────────────────────────── remote commands ─────────────────

    def _cmd_upload(self):
        uid, pname = self._selected_uid(), self._selected_profile()
        if not uid or not pname:
            return messagebox.showwarning("Select", "Select a user and profile first.")
        db.post_command({"user_id": uid, "command": "UPLOAD_PROFILE",
                         "profile_name": pname, "status": "pending"}, self._headers)
        self._set_status(f"UPLOAD_PROFILE queued for {pname}.")

    def _cmd_download(self):
        uid, pname = self._selected_uid(), self._selected_profile()
        if not uid or not pname:
            return messagebox.showwarning("Select", "Select a user and profile first.")
        # Get the file_id from the profile record
        profiles = db.get_client_profiles(uid, self._headers)
        fid = next((p.get("telegram_file_id") for p in profiles
                    if p["profile_name"] == pname), None)
        if not fid:
            return messagebox.showerror("No Backup", "No Telegram backup found for this profile.")
        db.post_command({"user_id": uid, "command": "DOWNLOAD_PROFILE",
                         "profile_name": pname, "status": "pending",
                         "telegram_file_id": fid}, self._headers)
        self._set_status(f"DOWNLOAD_PROFILE queued for {pname}.")

    # ──────────────────────────────────────── helpers ─────────────────────────

    def _selected_uid(self) -> str | None:
        sel = self.user_tree.selection()
        return sel[0] if sel else None

    def _selected_profile(self) -> str | None:
        sel = self.profile_tree.selection()
        return sel[0] if sel else None

    def _set_status(self, msg: str):
        self._status.config(text=msg)
