"""
gui/login.py — Login window with username/password authentication via Supabase.
"""
import os
import json
import hashlib
import threading
import tkinter as tk
from tkinter import ttk
from datetime import datetime, timezone

import services.supabase as db
from utils.hwid import get_hwid
from config import (
    BG_MAIN, BG_SIDEBAR, TEXT_MAIN, TEXT_MUTED,
    VIBER_PURPLE, VIBER_HOVER, STOP_RED, SUPABASE_URL,
)


class LoginWindow:
    SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "session.json")

    def __init__(self, root: tk.Tk, on_success):
        self.root = root
        self.on_success = on_success

        self.root.title("ANV Viber Manager — Sign In")
        self.root.geometry("380x350")
        self.root.configure(bg=BG_SIDEBAR)
        self.root.resizable(False, False)
        self.root.deiconify()
        self._center()
        self._build_ui()
        self._load_session()
        self.root.bind("<Return>", lambda _: self._login())

    # ------------------------------------------------------------------ helpers
    def _center(self):
        self.root.update_idletasks()
        w, h = 380, 350
        x = (self.root.winfo_screenwidth() - w) // 2
        y = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Login.TButton", background=VIBER_PURPLE, foreground="white",
                        font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("Login.TButton", background=[("active", VIBER_HOVER)])

        tk.Label(self.root, text="ANV VIBER MANAGER",
                 font=("Segoe UI", 16, "bold"), bg=BG_SIDEBAR, fg=VIBER_PURPLE).pack(pady=(30, 20))

        # Username
        tk.Label(self.root, text="Username", font=("Segoe UI", 9, "bold"),
                 bg=BG_SIDEBAR, fg=TEXT_MUTED).pack(anchor="w", padx=40)
        self._user = tk.Entry(self.root, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN,
                              font=("Segoe UI", 10), bd=1, relief=tk.FLAT)
        self._user.pack(fill=tk.X, padx=40, pady=(4, 12), ipady=4)

        # Password
        tk.Label(self.root, text="Password", font=("Segoe UI", 9, "bold"),
                 bg=BG_SIDEBAR, fg=TEXT_MUTED).pack(anchor="w", padx=40)
        pw_frame = tk.Frame(self.root, bg=BG_SIDEBAR)
        pw_frame.pack(fill=tk.X, padx=40, pady=(4, 15))
        self._pass = tk.Entry(pw_frame, show="*", bg=BG_MAIN, fg=TEXT_MAIN,
                              insertbackground=TEXT_MAIN, font=("Segoe UI", 10), bd=1, relief=tk.FLAT)
        self._pass.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        eye_btn = tk.Label(pw_frame, text="👁", bg=BG_MAIN, fg=TEXT_MUTED, cursor="hand2", width=3)
        eye_btn.pack(side=tk.RIGHT, fill=tk.Y)
        eye_btn.bind("<Button-1>", self._toggle_pw)

        # Remember + Forgot
        opt = tk.Frame(self.root, bg=BG_SIDEBAR)
        opt.pack(fill=tk.X, padx=40, pady=(0, 15))
        self._remember = tk.BooleanVar(value=False)
        tk.Checkbutton(opt, text="Remember Me", variable=self._remember,
                       bg=BG_SIDEBAR, fg=TEXT_MAIN, selectcolor=BG_MAIN,
                       activebackground=BG_SIDEBAR, activeforeground=TEXT_MAIN,
                       font=("Segoe UI", 9), bd=0).pack(side=tk.LEFT)

        # Sign In button
        self._btn = ttk.Button(self.root, text="Sign In", style="Login.TButton", command=self._login)
        self._btn.pack(fill=tk.X, padx=40, ipady=6)

        self._status = tk.Label(self.root, text="", font=("Segoe UI", 9, "italic"),
                                bg=BG_SIDEBAR, fg=TEXT_MUTED)
        self._status.pack(pady=(10, 0))

    def _toggle_pw(self, _):
        show = self._pass.cget("show")
        self._pass.config(show="" if show == "*" else "*")

    # ------------------------------------------------------------------ session
    def _load_session(self):
        try:
            path = os.path.normpath(self.SESSION_FILE)
            if os.path.exists(path):
                data = json.loads(open(path).read())
                if data.get("remember"):
                    self._user.insert(0, data.get("username", ""))
                    self._pass.insert(0, data.get("password", ""))
                    self._remember.set(True)
        except Exception:
            pass

    def _save_session(self, username, password):
        try:
            path = os.path.normpath(self.SESSION_FILE)
            if self._remember.get():
                with open(path, "w") as f:
                    json.dump({"username": username, "password": password, "remember": True}, f)
            elif os.path.exists(path):
                os.remove(path)
        except Exception:
            pass

    # ------------------------------------------------------------------ login
    def _login(self):
        u, p = self._user.get().strip(), self._pass.get().strip()
        if not u or not p:
            return self._fail("Please enter username and password.")
        self._btn.config(state=tk.DISABLED)
        self._status.config(text="Signing in…", fg=VIBER_PURPLE)
        threading.Thread(target=self._login_thread, args=(u, p), daemon=True).start()

    def _login_thread(self, username: str, password: str):
        # Dev mode
        if not SUPABASE_URL or SUPABASE_URL == "https://your-project.supabase.co":
            self.root.after(0, lambda: self._success(
                "00000000-0000-0000-0000-000000000000", username, "Permanent", "admin"))
            return

        try:
            hashed = hashlib.sha256(password.encode()).hexdigest()
            headers = db.make_headers()
            user = db.get_user_by_username(username, headers)

            if not user:
                return self.root.after(0, lambda: self._fail("Account does not exist."))
            if user.get("password_hash") != hashed:
                return self.root.after(0, lambda: self._fail("Incorrect password."))
            if user.get("status") == "blocked":
                return self.root.after(0, lambda: self._fail("This account is blocked."))

            # Optional expiry check (column may not exist)
            exp = user.get("expires_at")
            if exp:
                try:
                    exp_dt = datetime.fromisoformat(exp.replace("Z", "+00:00"))
                    if datetime.now(timezone.utc) > exp_dt:
                        return self.root.after(0, lambda: self._fail("License has expired."))
                except Exception:
                    pass

            # Optional HWID check (column may not exist)
            db_hwid = user.get("hwid")
            if db_hwid:
                if db_hwid != get_hwid():
                    return self.root.after(0, lambda: self._fail("Bound to another device."))
            else:
                # Try to bind, ignore failure silently (column might not exist)
                db.bind_hwid(user["id"], get_hwid(), headers)

            uid = user["id"]
            role = user.get("role", "user")
            expires_info = exp.split("T")[0] if exp else "Permanent"
            self.root.after(0, lambda: self._success(uid, username, expires_info, role))

        except Exception as e:
            self.root.after(0, lambda: self._fail(f"Error: {e}"))

    def _fail(self, msg: str):
        self._btn.config(state=tk.NORMAL)
        self._status.config(text=msg, fg=STOP_RED)

    def _success(self, uid, username, expires, role):
        self._status.config(text="Success! Loading…", fg="#12B76A")
        self._save_session(username, self._pass.get().strip())
        self.root.after(400, lambda: (self.root.withdraw(), self.on_success(uid, username, expires, role)))
