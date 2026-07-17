"""
gui/login_window.py
LoginWindow — handles authentication, HWID binding, and session management.
"""
import os
import json
import hashlib
import threading
import time
import webbrowser
import tkinter as tk
from tkinter import ttk
from datetime import datetime

from config import (
    BG_MAIN, BG_SIDEBAR, TEXT_MAIN, TEXT_MUTED,
    VIBER_PURPLE, VIBER_HOVER, STOP_RED,
    SUPABASE_URL, SUPABASE_KEY,
)
from utils.hwid import get_hwid
import services.supabase as db


class LoginWindow:
    def __init__(self, root: tk.Tk, on_success):
        self.root = root
        self.on_success = on_success
        self.root.title("ANV Viber Manager - Sign In")
        self.root.geometry("380x340")
        self.root.configure(bg=BG_SIDEBAR)
        self.root.resizable(False, False)

        import sys
        if getattr(sys, "frozen", False):
            self.session_file = os.path.join(os.path.dirname(sys.executable), "session.json")
        else:
            self.session_file = os.path.normpath(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "session.json")
            )

        self._center_window()
        self._setup_styles()
        self._build_ui()
        self._load_session()

        self.root.bind("<Return>", lambda e: self._perform_login())

    # ------------------------------------------------------------------
    # Setup helpers
    # ------------------------------------------------------------------

    def _center_window(self):
        self.root.update_idletasks()
        w, h = self.root.winfo_width(), self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (w // 2)
        y = (self.root.winfo_screenheight() // 2) - (h // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "Login.TButton",
            background=VIBER_PURPLE, foreground="white",
            font=("Segoe UI", 10, "bold"), borderwidth=0,
        )
        style.map("Login.TButton", background=[("active", VIBER_HOVER)])

    def _build_ui(self):
        tk.Label(
            self.root, text="ANV VIBER MANAGER",
            font=("Segoe UI", 16, "bold"), bg=BG_SIDEBAR, fg=VIBER_PURPLE,
        ).pack(pady=(30, 20))

        # Username
        tk.Label(
            self.root, text="Username",
            font=("Segoe UI", 9, "bold"), bg=BG_SIDEBAR, fg=TEXT_MUTED,
        ).pack(anchor=tk.W, padx=40)
        self.entry_user = tk.Entry(
            self.root, bg=BG_MAIN, fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN, font=("Segoe UI", 10), bd=1, relief=tk.FLAT,
        )
        self.entry_user.pack(fill=tk.X, padx=40, pady=(4, 12), ipady=4)

        # Password
        tk.Label(
            self.root, text="Password",
            font=("Segoe UI", 9, "bold"), bg=BG_SIDEBAR, fg=TEXT_MUTED,
        ).pack(anchor=tk.W, padx=40)

        pass_frame = tk.Frame(self.root, bg=BG_SIDEBAR)
        pass_frame.pack(fill=tk.X, padx=40, pady=(4, 15))

        self.entry_pass = tk.Entry(
            pass_frame, show="*", bg=BG_MAIN, fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN, font=("Segoe UI", 10), bd=1, relief=tk.FLAT,
        )
        self.entry_pass.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)

        from PIL import ImageTk
        import gui.icons as icons
        self.eye_img = ImageTk.PhotoImage(icons.get_search_icon(TEXT_MUTED))
        self.btn_show_pass = tk.Label(
            pass_frame, image=self.eye_img, bg=BG_MAIN,
            cursor="hand2", width=24,
        )
        self.btn_show_pass.pack(side=tk.RIGHT, fill=tk.Y, padx=4)
        self.btn_show_pass.bind("<Button-1>", self._toggle_password)

        # Remember Me / Forgot Password
        self.opt_var = tk.BooleanVar(value=False)
        opt_frame = tk.Frame(self.root, bg=BG_SIDEBAR)
        opt_frame.pack(fill=tk.X, padx=40, pady=(0, 15))

        tk.Checkbutton(
            opt_frame, text="Remember Me", variable=self.opt_var,
            bg=BG_SIDEBAR, fg=TEXT_MAIN, selectcolor=BG_MAIN,
            activebackground=BG_SIDEBAR, activeforeground=TEXT_MAIN,
            font=("Segoe UI", 9), bd=0, highlightthickness=0,
        ).pack(side=tk.LEFT)

        lbl_forgot = tk.Label(
            opt_frame, text="Forgot Password?",
            font=("Segoe UI", 9, "underline"), bg=BG_SIDEBAR, fg=VIBER_PURPLE, cursor="hand2",
        )
        lbl_forgot.pack(side=tk.RIGHT)
        lbl_forgot.bind("<Button-1>", lambda e: webbrowser.open("https://t.me/anv184"))

        # Sign In button
        self.btn_login = ttk.Button(
            self.root, text="Sign In", style="Login.TButton", command=self._perform_login,
        )
        self.btn_login.pack(fill=tk.X, padx=40, ipady=6)

        # Status label
        self.lbl_status = tk.Label(
            self.root, text="",
            font=("Segoe UI", 9, "italic"), bg=BG_SIDEBAR, fg=TEXT_MUTED,
        )
        self.lbl_status.pack(pady=(10, 0))

    # ------------------------------------------------------------------
    # Session persistence
    # ------------------------------------------------------------------

    def _load_session(self):
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file) as f:
                    data = json.load(f)
                if data.get("remember"):
                    self.entry_user.insert(0, data.get("username", ""))
                    self.entry_pass.insert(0, data.get("password", ""))
                    self.opt_var.set(True)
        except Exception:
            pass

    def _save_session(self, username: str, password: str):
        try:
            if self.opt_var.get():
                with open(self.session_file, "w") as f:
                    json.dump({"username": username, "password": password, "remember": True}, f)
            elif os.path.exists(self.session_file):
                os.remove(self.session_file)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Password visibility toggle
    # ------------------------------------------------------------------

    def _toggle_password(self, _event):
        if self.entry_pass.cget("show") == "*":
            self.entry_pass.config(show="")
            self.btn_show_pass.config(text="🙈", fg=VIBER_PURPLE)
        else:
            self.entry_pass.config(show="*")
            self.btn_show_pass.config(text="👁", fg=TEXT_MUTED)

    # ------------------------------------------------------------------
    # Login logic
    # ------------------------------------------------------------------

    def _perform_login(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()

        if not username or not password:
            self.lbl_status.config(text="Please enter username and password.", fg=STOP_RED)
            return

        self.btn_login.config(state=tk.DISABLED)
        self.lbl_status.config(text="Signing in...", fg=VIBER_PURPLE)
        threading.Thread(
            target=self._login_thread, args=(username, password), daemon=True,
        ).start()

    def _login_thread(self, username: str, password: str):
        if SUPABASE_URL == "https://your-project.supabase.co" or not SUPABASE_URL:
            time.sleep(1)
            self.root.after(
                0,
                lambda: self._login_success(
                    "00000000-0000-0000-0000-000000000000", username, "Dev Mode (No DB)", "admin"
                ),
            )
            return

        try:
            hashed = hashlib.sha256(password.encode()).hexdigest()
            headers = db.make_headers()

            user = db.get_user_by_username(username, headers)
            if not user:
                self.root.after(0, lambda: self._login_failed("Account does not exist."))
                return

            if user.get("password_hash") != hashed:
                self.root.after(0, lambda: self._login_failed("Incorrect password."))
                return

            if user.get("status") == "blocked":
                self.root.after(0, lambda: self._login_failed("This account is blocked."))
                return

            # Expiry check
            expires_str = user.get("expires_at")
            if expires_str:
                try:
                    exp_dt = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
                    if datetime.now(exp_dt.tzinfo) > exp_dt:
                        self.root.after(0, lambda: self._login_failed("Your license has expired."))
                        return
                except Exception:
                    pass

            # HWID check / bind
            current_hwid = get_hwid()
            db_hwid = user.get("hwid")
            if not db_hwid:
                if not db.bind_hwid(user["id"], current_hwid, headers):
                    self.root.after(0, lambda: self._login_failed("Failed to bind device ID."))
                    return
            elif db_hwid != current_hwid:
                self.root.after(
                    0, lambda: self._login_failed("This account is bound to another device.")
                )
                return

            expires_info = expires_str.split("T")[0] if expires_str else "Permanent"
            role = user.get("role", "user")
            uid = user["id"]
            self.root.after(0, lambda: self._login_success(uid, username, expires_info, role))

        except Exception as e:
            self.root.after(0, lambda: self._login_failed(f"Login failed: {e}"))

    def _login_failed(self, message: str):
        self.btn_login.config(state=tk.NORMAL)
        self.lbl_status.config(text=message, fg=STOP_RED)

    def _login_success(self, user_id: str, username: str, expires_info: str, role: str):
        self.lbl_status.config(text="Success! Loading...", fg="#12B76A")
        self._save_session(username, self.entry_pass.get().strip())
        self.root.after(500, lambda: self.on_success(user_id, username, expires_info, role))
