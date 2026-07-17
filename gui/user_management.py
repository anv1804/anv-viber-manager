"""
gui/user_management.py
UserManagementWindow — Admin panel to list, create, edit, delete users
and reset their HWID. Also opens ClientProfilesViewWindow.
"""
import hashlib
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

import requests

from config import (
    BG_MAIN, BG_SIDEBAR, BG_CARD, TEXT_MAIN, TEXT_MUTED,
    VIBER_PURPLE, STOP_RED, BTN_DARK, BORDER_COLOR,
)
import services.supabase as db


class UserManagementWindow:
    def __init__(self, parent: tk.Widget, main_app):
        self.parent   = parent
        self.main_app = main_app  # AnvViberManager instance

        self.window = tk.Toplevel(parent)
        self.window.title("ANV Viber - User Management Panel")
        self.window.geometry("840x520")
        self.window.configure(bg=BG_MAIN)
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.wait_visibility()
        self.window.grab_set()

        self.headers   = db.make_headers()
        self.all_users: list[dict] = []

        self._build_ui()
        self._load_users()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.window, bg=BG_SIDEBAR, height=50)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text=" CLIENTS MANAGEMENT PANEL",
                 font=("Segoe UI", 12, "bold"), bg=BG_SIDEBAR, fg=VIBER_PURPLE,
                 ).pack(side=tk.LEFT, padx=20, pady=10)

        # Filter bar
        bar = tk.Frame(self.window, bg=BG_SIDEBAR)
        bar.pack(fill=tk.X, padx=20, pady=(10, 0), ipady=5)

        tk.Label(bar, text="Search Username:", font=("Segoe UI", 9, "bold"),
                 bg=BG_SIDEBAR, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(15, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._apply_filters)
        tk.Entry(bar, textvariable=self.search_var, bg=BG_MAIN, fg=TEXT_MAIN,
                 insertbackground=TEXT_MAIN, font=("Segoe UI", 9), bd=1,
                 relief=tk.FLAT, width=22).pack(side=tk.LEFT, padx=5, ipady=2)

        tk.Label(bar, text="Status:", font=("Segoe UI", 9, "bold"),
                 bg=BG_SIDEBAR, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(20, 5))
        self.filter_status_var = tk.StringVar(value="All")
        cmb = ttk.Combobox(bar, textvariable=self.filter_status_var,
                            values=["All", "active", "blocked"], state="readonly", width=10)
        cmb.pack(side=tk.LEFT, padx=5)
        cmb.bind("<<ComboboxSelected>>", self._apply_filters)

        # Content split
        content = tk.Frame(self.window, bg=BG_MAIN)
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 15))

        # Right control panel
        ctrl = tk.Frame(content, bg=BG_SIDEBAR, width=180)
        ctrl.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))
        ctrl.pack_propagate(False)

        ttk.Button(ctrl, text=" Add User",      style="Primary.TButton",   command=self._add_user   ).pack(fill=tk.X, padx=15, pady=(20, 8), ipady=4)
        self.btn_edit         = ttk.Button(ctrl, text=" Edit User",      style="Secondary.TButton", command=self._edit_user,         state=tk.DISABLED)
        self.btn_view_profiles= ttk.Button(ctrl, text=" View Profiles", style="Secondary.TButton", command=self._view_profiles,     state=tk.DISABLED)
        self.btn_reset_hwid   = ttk.Button(ctrl, text=" Reset HWID",    style="Secondary.TButton", command=self._reset_hwid,        state=tk.DISABLED)
        for btn in (self.btn_edit, self.btn_view_profiles, self.btn_reset_hwid):
            btn.pack(fill=tk.X, padx=15, pady=6, ipady=4)

        self.btn_history = ttk.Button(ctrl, text=" Push History", style="Secondary.TButton", command=self._view_push_history)
        self.btn_history.pack(fill=tk.X, padx=15, pady=6, ipady=4)

        tk.Frame(ctrl, bg=BORDER_COLOR, height=1).pack(fill=tk.X, padx=15, pady=12)

        self.btn_delete = ttk.Button(ctrl, text=" Delete User", style="Stop.TButton",
                                     command=self._delete_user, state=tk.DISABLED)
        self.btn_delete.pack(fill=tk.X, padx=15, pady=6, ipady=4)

        # Left table
        table = tk.Frame(content, bg=BG_CARD)
        table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sb = ttk.Scrollbar(table)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(
            table,
            columns=("stt", "username", "hwid", "status", "role", "expires"),
            show="headings", yscrollcommand=sb.set, selectmode="browse",
        )
        for col, text, width in [
            ("stt",      "STT",         50),
            ("username", "Username",   120),
            ("hwid",     "HWID",       130),
            ("status",   "Status",      90),
            ("role",     "Role",        80),
            ("expires",  "Expires At", 130),
        ]:
            self.tree.heading(col, text=text, anchor=tk.CENTER)
            self.tree.column(col, width=width, anchor=tk.CENTER)

        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        sb.config(command=self.tree.yview)

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _load_users(self):
        try:
            self.all_users = db.get_all_users(self.headers)
            self._apply_filters()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to retrieve users: {e}", parent=self.window)

    def _apply_filters(self, *_):
        for item in self.tree.get_children():
            self.tree.delete(item)

        query  = self.search_var.get().strip().lower()
        status = self.filter_status_var.get()

        for idx, row in enumerate(self.all_users, 1):
            uname = row.get("username", "")
            ustatus = row.get("status", "active")
            if query and query not in uname.lower():
                continue
            if status != "All" and ustatus != status:
                continue

            hwid_disp = (row.get("hwid") or "")[:12] + ("..." if row.get("hwid") else "Unbound")
            if not row.get("hwid"):
                hwid_disp = "Unbound"
            exp_disp = row.get("expires_at", "").split("T")[0] if row.get("expires_at") else "Permanent"

            self.tree.insert("", tk.END, iid=row["id"], values=(
                str(idx), uname, hwid_disp, ustatus, row.get("role", "user"), exp_disp,
            ))

        self._on_select(None)

    def _on_select(self, _event):
        state = tk.NORMAL if self.tree.selection() else tk.DISABLED
        for btn in (self.btn_edit, self.btn_view_profiles, self.btn_reset_hwid, self.btn_delete):
            btn.config(state=state)

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------

    def _add_user(self):
        dialog = tk.Toplevel(self.window)
        dialog.title("Add New User")
        dialog.geometry("340x260")
        dialog.configure(bg=BG_SIDEBAR)
        dialog.resizable(False, False)
        dialog.transient(self.window)
        dialog.wait_visibility()
        dialog.grab_set()

        tk.Label(dialog, text="Username:", bg=BG_SIDEBAR, fg=TEXT_MAIN,
                 font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, padx=30, pady=(15, 2))
        e_user = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, bd=1, relief=tk.FLAT)
        e_user.pack(fill=tk.X, padx=30, ipady=3)

        tk.Label(dialog, text="Password:", bg=BG_SIDEBAR, fg=TEXT_MAIN,
                 font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, padx=30, pady=(10, 2))
        e_pass = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, bd=1, relief=tk.FLAT)
        e_pass.pack(fill=tk.X, padx=30, ipady=3)

        tk.Label(dialog, text="Expiry (YYYY-MM-DD) or empty for permanent:", bg=BG_SIDEBAR,
                 fg=TEXT_MAIN, font=("Segoe UI", 9)).pack(anchor=tk.W, padx=30, pady=(10, 2))
        e_exp = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, bd=1, relief=tk.FLAT)
        e_exp.pack(fill=tk.X, padx=30, ipady=3)

        def save():
            username = e_user.get().strip()
            password = e_pass.get().strip()
            exp      = e_exp.get().strip()

            if not username or not password:
                messagebox.showerror("Error", "Username and Password cannot be empty!", parent=dialog)
                return

            payload = {
                "username":      username,
                "password_hash": hashlib.sha256(password.encode()).hexdigest(),
                "status":        "active",
                "role":          "user",
            }
            if exp:
                try:
                    datetime.strptime(exp, "%Y-%m-%d")
                    payload["expires_at"] = exp + "T23:59:59+00:00"
                except ValueError:
                    messagebox.showerror("Error", "Invalid date format! Use YYYY-MM-DD.", parent=dialog)
                    return

            resp = db.create_user(payload, self.headers)
            if resp.status_code in (200, 201, 204):
                dialog.destroy()
                self._load_users()
                messagebox.showinfo("Success", f"User '{username}' created!", parent=self.window)
            else:
                messagebox.showerror("Error", f"Failed: {resp.text}", parent=dialog)

        ttk.Button(dialog, text="Create User", style="Primary.TButton", command=save).pack(pady=20, ipady=4, padx=30, fill=tk.X)

    def _edit_user(self):
        user_id = self.tree.selection()[0]
        vals    = self.tree.item(user_id, "values")
        username, cur_status, cur_role, cur_expiry = vals[1], vals[3], vals[4], vals[5]

        dialog = tk.Toplevel(self.window)
        dialog.title(f"Edit User - {username}")
        dialog.geometry("340x360")
        dialog.configure(bg=BG_SIDEBAR)
        dialog.resizable(False, False)
        dialog.transient(self.window)
        dialog.wait_visibility()
        dialog.grab_set()

        tk.Label(dialog, text="Username:", bg=BG_SIDEBAR, fg=TEXT_MAIN,
                 font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, padx=30, pady=(15, 2))
        e_user = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, bd=1, relief=tk.FLAT)
        e_user.pack(fill=tk.X, padx=30, ipady=3)
        e_user.insert(0, username)

        tk.Label(dialog, text="New Password (leave empty to keep):", bg=BG_SIDEBAR, fg=TEXT_MAIN,
                 font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, padx=30, pady=(10, 2))
        e_pass = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, bd=1, relief=tk.FLAT)
        e_pass.pack(fill=tk.X, padx=30, ipady=3)

        tk.Label(dialog, text="Expiry (YYYY-MM-DD) or empty:", bg=BG_SIDEBAR, fg=TEXT_MAIN).pack(anchor=tk.W, padx=30, pady=(10, 2))
        e_exp = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, bd=1, relief=tk.FLAT)
        e_exp.pack(fill=tk.X, padx=30, ipady=3)
        if cur_expiry != "Permanent":
            e_exp.insert(0, cur_expiry)

        tk.Label(dialog, text="Status:", bg=BG_SIDEBAR, fg=TEXT_MAIN).pack(anchor=tk.W, padx=30, pady=(10, 2))
        c_status = ttk.Combobox(dialog, values=["active", "blocked"], state="readonly")
        c_status.pack(fill=tk.X, padx=30)
        c_status.set(cur_status)

        tk.Label(dialog, text="Role:", bg=BG_SIDEBAR, fg=TEXT_MAIN).pack(anchor=tk.W, padx=30, pady=(10, 2))
        c_role = ttk.Combobox(dialog, values=["user", "admin"], state="readonly")
        c_role.pack(fill=tk.X, padx=30)
        c_role.set(cur_role)

        def update():
            new_uname = e_user.get().strip()
            password  = e_pass.get().strip()
            exp       = e_exp.get().strip()

            if not new_uname:
                messagebox.showerror("Error", "Username cannot be empty!", parent=dialog)
                return

            payload: dict = {
                "username":   new_uname,
                "status":     c_status.get(),
                "role":       c_role.get(),
                "expires_at": None,
            }
            if password:
                payload["password_hash"] = hashlib.sha256(password.encode()).hexdigest()
            if exp:
                try:
                    datetime.strptime(exp, "%Y-%m-%d")
                    payload["expires_at"] = exp + "T23:59:59+00:00"
                except ValueError:
                    messagebox.showerror("Error", "Invalid date format!", parent=dialog)
                    return

            resp = db.update_user(user_id, payload, self.headers)
            if resp.status_code in (200, 204):
                dialog.destroy()
                self._load_users()
                messagebox.showinfo("Success", "User updated!", parent=self.window)
            else:
                messagebox.showerror("Error", f"Failed: {resp.text}", parent=dialog)

        ttk.Button(dialog, text="Save Changes", style="Primary.TButton", command=update).pack(pady=20, ipady=4, padx=30, fill=tk.X)

    def _view_profiles(self):
        from gui.profile_viewer import ClientProfilesViewWindow
        user_id  = self.tree.selection()[0]
        username = self.tree.item(user_id, "values")[1]
        ClientProfilesViewWindow(self.window, user_id, username, self.main_app)

    def _reset_hwid(self):
        user_id  = self.tree.selection()[0]
        username = self.tree.item(user_id, "values")[1]
        if messagebox.askyesno("Confirm Reset", f"Reset HWID for '{username}'?", parent=self.window):
            resp = db.reset_hwid(user_id, self.headers)
            if resp.status_code in (200, 204):
                self._load_users()
                messagebox.showinfo("Success", f"HWID reset for '{username}'!", parent=self.window)
            else:
                messagebox.showerror("Error", f"Failed: {resp.text}", parent=self.window)

    def _delete_user(self):
        user_id = self.tree.selection()[0]
        vals    = self.tree.item(user_id, "values")
        username, role = vals[1], vals[4]

        if role == "admin":
            messagebox.showerror("Error", "Cannot delete an Administrator account!", parent=self.window)
            return

        if messagebox.askyesno("Confirm Delete", f"Delete user '{username}'?", parent=self.window):
            resp = db.delete_user(user_id, self.headers)
            if resp.status_code in (200, 204):
                self._load_users()
                messagebox.showinfo("Success", f"User '{username}' deleted!", parent=self.window)
            else:
                messagebox.showerror("Error", f"Failed: {resp.text}", parent=self.window)

    def _view_push_history(self):
        from gui.push_history import PushHistoryWindow
        # Create user map: user_id -> username for pretty printing targets
        user_map = {u.get("id"): u.get("username", "Unknown") for u in self.all_users}
        PushHistoryWindow(self.window, user_map)
