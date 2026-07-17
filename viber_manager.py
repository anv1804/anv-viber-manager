#!/usr/bin/env python3
import os
import sys
import shutil
import subprocess
import zipfile
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import hashlib
import threading
import time
import requests
from datetime import datetime
import json
import webbrowser
import base64
from cryptography.fernet import Fernet

# ==========================================
# CONFIGURATION FOR ADMIN (EDIT BEFORE BUILD)
# ==========================================
SUPABASE_URL = "https://hqbsupczeujqgrkvrdjx.supabase.co"
SUPABASE_KEY = "sb_publishable_249FmOz7LjCvA6-dAlTHkg_mngyhFt9"
TELEGRAM_BOT_TOKEN = "8590170680:AAFZqP6KDe1nc0GjLJQEU1ghePCKzcpvUq4"
TELEGRAM_CHAT_ID = "7962221453"

# Premium Theme configuration (ANV Viber Dark Style)
BG_MAIN = "#0B0B0C"        # Deep rich dark background
BG_SIDEBAR = "#121214"     # Dark sidebar background
BG_CARD = "#16161A"        # Table/Card background
TEXT_MAIN = "#F4F4F5"       # White-gray text
TEXT_MUTED = "#71717A"      # Muted gray text
VIBER_PURPLE = "#7F56D9"    # Premium Viber purple
VIBER_HOVER = "#6941C6"     # Hover purple
STOP_RED = "#D92D20"        # Crimson stop red
STOP_HOVER = "#B42318"      # Hover red
BTN_DARK = "#27272A"        # Dark grey button
BTN_DARK_HOVER = "#3F3F46"  # Dark grey button hover
BORDER_COLOR = "#2D2D34"    # Subtle border color

# Cryptographic Helpers for Profile Security
def get_profile_key(user_id, profile_name):
    # Derive a secure 32-byte key from user_id and profile_name using SHA256
    raw_key = hashlib.sha256(f"{user_id}_{profile_name}_anv_secure_salt_2026".encode()).digest()
    return base64.urlsafe_b64encode(raw_key)

def encrypt_file(file_path, key):
    with open(file_path, 'rb') as f:
        data = f.read()
    fernet = Fernet(key)
    encrypted_data = fernet.encrypt(data)
    with open(file_path, 'wb') as f:
        f.write(encrypted_data)

def decrypt_file(file_path, key):
    with open(file_path, 'rb') as f:
        data = f.read()
    fernet = Fernet(key)
    decrypted_data = fernet.decrypt(data)
    with open(file_path, 'wb') as f:
        f.write(decrypted_data)

def get_hwid():
    hwid_str = ""
    try:
        if sys.platform.startswith("win"):
            cmd = "wmic csproduct get uuid"
            uuid = subprocess.check_output(cmd, shell=True).decode().split("\n")[1].strip()
            hwid_str = uuid
        else:
            for path in ["/etc/machine-id", "/var/lib/dbus/machine-id"]:
                if os.path.exists(path):
                    with open(path, "r") as f:
                        hwid_str = f.read().strip()
                        break
            if not hwid_str:
                import socket
                hwid_str = socket.gethostname()
    except Exception:
        import platform
        hwid_str = platform.node() + platform.processor() + platform.machine()
        
    return hashlib.sha256(hwid_str.encode()).hexdigest()

class LoginWindow:
    def __init__(self, root, on_success):
        self.root = root
        self.on_success = on_success
        self.root.title("ANV Viber Manager - Sign In")
        self.root.geometry("380x340")
        self.root.configure(bg=BG_SIDEBAR)
        self.root.resizable(False, False)

        self.session_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "session.json")

        # Center window
        self.center_window()

        # Styles
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Login.TButton", background=VIBER_PURPLE, foreground="white", font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("Login.TButton", background=[("active", VIBER_HOVER)])

        # UI Components
        lbl_title = tk.Label(self.root, text="ANV VIBER MANAGER", font=("Segoe UI", 16, "bold"), bg=BG_SIDEBAR, fg=VIBER_PURPLE)
        lbl_title.pack(pady=(30, 20))

        # Username
        lbl_user = tk.Label(self.root, text="Username", font=("Segoe UI", 9, "bold"), bg=BG_SIDEBAR, fg=TEXT_MUTED)
        lbl_user.pack(anchor=tk.W, padx=40)
        self.entry_user = tk.Entry(self.root, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, font=("Segoe UI", 10), bd=1, relief=tk.FLAT)
        self.entry_user.pack(fill=tk.X, padx=40, pady=(4, 12), ipady=4)

        # Password
        lbl_pass = tk.Label(self.root, text="Password", font=("Segoe UI", 9, "bold"), bg=BG_SIDEBAR, fg=TEXT_MUTED)
        lbl_pass.pack(anchor=tk.W, padx=40)
        
        pass_frame = tk.Frame(self.root, bg=BG_SIDEBAR)
        pass_frame.pack(fill=tk.X, padx=40, pady=(4, 15))
        
        self.entry_pass = tk.Entry(pass_frame, show="*", bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, font=("Segoe UI", 10), bd=1, relief=tk.FLAT)
        self.entry_pass.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4)
        
        self.btn_show_pass = tk.Label(pass_frame, text="👁", bg=BG_MAIN, fg=TEXT_MUTED, cursor="hand2", font=("Segoe UI", 10), width=3)
        self.btn_show_pass.pack(side=tk.RIGHT, fill=tk.Y)
        self.btn_show_pass.bind("<Button-1>", self.toggle_password_visibility)

        # Checkbox and Forgot Password container
        self.opt_var = tk.BooleanVar(value=False)
        opt_frame = tk.Frame(self.root, bg=BG_SIDEBAR)
        opt_frame.pack(fill=tk.X, padx=40, pady=(0, 15))

        self.chk_remember = tk.Checkbutton(
            opt_frame, text="Remember Me", variable=self.opt_var,
            bg=BG_SIDEBAR, fg=TEXT_MAIN, selectcolor=BG_MAIN,
            activebackground=BG_SIDEBAR, activeforeground=TEXT_MAIN,
            font=("Segoe UI", 9), bd=0, highlightthickness=0
        )
        self.chk_remember.pack(side=tk.LEFT)

        lbl_forgot = tk.Label(opt_frame, text="Forgot Password?", font=("Segoe UI", 9, "underline"), bg=BG_SIDEBAR, fg=VIBER_PURPLE, cursor="hand2")
        lbl_forgot.pack(side=tk.RIGHT)
        lbl_forgot.bind("<Button-1>", lambda e: webbrowser.open("https://t.me/anv184"))

        # Login button
        self.btn_login = ttk.Button(self.root, text="Sign In", style="Login.TButton", command=self.perform_login)
        self.btn_login.pack(fill=tk.X, padx=40, ipady=6)

        # Status text
        self.lbl_status = tk.Label(self.root, text="", font=("Segoe UI", 9, "italic"), bg=BG_SIDEBAR, fg=TEXT_MUTED)
        self.lbl_status.pack(pady=(10, 0))

        # Load session if exists
        self.load_session()

        # Bind Enter key
        self.root.bind("<Return>", lambda e: self.perform_login())

    def center_window(self):
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')

    def toggle_password_visibility(self, event):
        if self.entry_pass.cget("show") == "*":
            self.entry_pass.config(show="")
            self.btn_show_pass.config(text="🙈", fg=VIBER_PURPLE)
        else:
            self.entry_pass.config(show="*")
            self.btn_show_pass.config(text="👁", fg=TEXT_MUTED)

    def load_session(self):
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, "r") as f:
                    data = json.load(f)
                    if data.get("remember"):
                        self.entry_user.insert(0, data.get("username", ""))
                        self.entry_pass.insert(0, data.get("password", ""))
                        self.opt_var.set(True)
        except Exception:
            pass

    def save_session(self, username, password):
        try:
            if self.opt_var.get():
                with open(self.session_file, "w") as f:
                    json.dump({"username": username, "password": password, "remember": True}, f)
            else:
                if os.path.exists(self.session_file):
                    os.remove(self.session_file)
        except Exception:
            pass

    def perform_login(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()

        if not username or not password:
            self.lbl_status.config(text="Please enter username and password.", fg=STOP_RED)
            return

        self.btn_login.config(state=tk.DISABLED)
        self.lbl_status.config(text="Signing in...", fg=VIBER_PURPLE)

        # Run database operations in thread to keep GUI responsive
        threading.Thread(target=self.login_thread, args=(username, password), daemon=True).start()

    def login_thread(self, username, password):
        # Default Offline verification fallback (in case DB config is missing)
        if SUPABASE_URL == "https://hqbsupczeujqgrkvrdjx.supabase.co" and SUPABASE_KEY == "sb_publishable_249FmOz7LjCvA6-dAlTHkg_mngyhFt9" and username == "anv184" and password == "18042004@nV":
            # Developer Bypass for early setups
            self.root.after(0, lambda: self.login_success("00000000-0000-0000-0000-000000000000", username, "Permanent", "admin"))
            return

        if SUPABASE_URL == "https://your-project.supabase.co" or not SUPABASE_URL:
            time.sleep(1)
            self.root.after(0, lambda: self.login_success("00000000-0000-0000-0000-000000000000", username, "Dev Mode (No DB)", "admin"))
            return

        try:
            hashed_pass = hashlib.sha256(password.encode()).hexdigest()
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}"
            }
            url = f"{SUPABASE_URL}/rest/v1/users?username=eq.{username}"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code != 200:
                self.root.after(0, lambda: self.login_failed("Database connection error."))
                return

            records = response.json()
            if not records:
                self.root.after(0, lambda: self.login_failed("Account does not exist."))
                return

            user_record = records[0]
            if user_record.get("password_hash") != hashed_pass:
                self.root.after(0, lambda: self.login_failed("Incorrect password."))
                return

            # Check status
            if user_record.get("status") == "blocked":
                self.root.after(0, lambda: self.login_failed("This account is blocked."))
                return

            # Check license expiration
            expires_str = user_record.get("expires_at")
            if expires_str:
                try:
                    expires_dt = datetime.fromisoformat(expires_str.replace("Z", "+00:00"))
                    if datetime.now(expires_dt.tzinfo) > expires_dt:
                        self.root.after(0, lambda: self.login_failed("Your license has expired."))
                        return
                except Exception:
                    pass

            # HWID Check
            current_hwid = get_hwid()
            db_hwid = user_record.get("hwid")

            if not db_hwid:
                # Bind HWID automatically on first login
                patch_url = f"{SUPABASE_URL}/rest/v1/users?id=eq.{user_record['id']}"
                patch_response = requests.patch(patch_url, json={"hwid": current_hwid}, headers=headers, timeout=10)
                if patch_response.status_code not in (200, 204):
                    self.root.after(0, lambda: self.login_failed("Failed to bind device ID."))
                    return
            elif db_hwid != current_hwid:
                self.root.after(0, lambda: self.login_failed("This account is bound to another device."))
                return

            # Retrieve info
            user_id = user_record["id"]
            expires_info = expires_str.split("T")[0] if expires_str else "Permanent"
            role = user_record.get("role", "user")
            self.root.after(0, lambda: self.login_success(user_id, username, expires_info, role))

        except Exception as e:
            self.root.after(0, lambda: self.login_failed(f"Login failed: {e}"))

    def login_failed(self, message):
        self.btn_login.config(state=tk.NORMAL)
        self.lbl_status.config(text=message, fg=STOP_RED)

    def login_success(self, user_id, username, expires_info, role):
        self.lbl_status.config(text="Success! Loading...", fg="#12B76A")
        password = self.entry_pass.get().strip()
        self.save_session(username, password)
        self.root.after(500, lambda: self.on_success(user_id, username, expires_info, role))


class AnvViberManager:
    def __init__(self, root, user_id, username, expires_info, role="user"):
        self.root = root
        self.user_id = user_id
        self.username = username
        self.expires_info = expires_info
        self.role = role
        
        self.root.title("ANV Viber Manager")
        self.root.geometry("860x600")
        self.root.configure(bg=BG_MAIN)
        self.root.resizable(False, False)

        # Base paths
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.profiles_dir = os.path.join(self.script_dir, "viber_profiles", self.username)
        os.makedirs(self.profiles_dir, exist_ok=True)

        self.selected_profiles = []
        self.viber_path = self.detect_viber_path()
        self.running_processes = {}

        # Set style
        self.setup_styles()
        # Build UI
        self.build_ui()
        # Load Profiles
        self.load_profiles()
        # Start checking process loop
        self.check_running_processes()
        # Start remote sync and command loops
        self.start_remote_sync_loop()

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        
        # Configure overall widget styling
        style.configure(".", background=BG_MAIN, foreground=TEXT_MAIN, borderwidth=0)
        style.configure("TFrame", background=BG_MAIN)
        
        # Treeview styling (Profile List)
        style.configure("Treeview", 
                        background=BG_CARD, 
                        fieldbackground=BG_CARD, 
                        foreground=TEXT_MAIN,
                        rowheight=32,
                        borderwidth=0,
                        font=("Segoe UI", 10))
        
        style.configure("Treeview.Heading",
                        background=BG_SIDEBAR,
                        foreground=TEXT_MAIN,
                        font=("Segoe UI", 10, "bold"),
                        borderwidth=0)
        style.map("Treeview", background=[("selected", VIBER_PURPLE)])
        
        # Button styles
        style.configure("Primary.TButton", 
                        background=VIBER_PURPLE, 
                        foreground="white", 
                        font=("Segoe UI", 10, "bold"),
                        borderwidth=0, 
                        focusthickness=0)
        style.map("Primary.TButton", background=[("active", VIBER_HOVER)])

        style.configure("Stop.TButton", 
                        background=STOP_RED, 
                        foreground="white", 
                        font=("Segoe UI", 10, "bold"),
                        borderwidth=0, 
                        focusthickness=0)
        style.map("Stop.TButton", background=[("active", STOP_HOVER)])

        style.configure("Secondary.TButton", 
                        background=BTN_DARK, 
                        foreground=TEXT_MAIN, 
                        font=("Segoe UI", 10),
                        borderwidth=0,
                        focusthickness=0)
        style.map("Secondary.TButton", background=[("active", BTN_DARK_HOVER)])

        style.configure("Vertical.TScrollbar", gripcount=0, background=BG_CARD, troughcolor=BG_MAIN)

    def detect_viber_path(self):
        if sys.platform.startswith("win"):
            user_profile = os.environ.get("USERPROFILE", "C:\\")
            paths = [
                os.path.join(user_profile, "AppData", "Local", "Viber", "Viber.exe"),
                "C:\\Program Files\\Viber\\Viber.exe",
                "C:\\Program Files (x86)\\Viber\\Viber.exe"
            ]
            for path in paths:
                if os.path.exists(path):
                    return path
            return None
        else:
            try:
                path = subprocess.check_output(["which", "viber"], text=True).strip()
                if path:
                    return path
            except subprocess.CalledProcessError:
                pass
            
            home = os.path.expanduser("~")
            paths = [
                "/usr/bin/viber",
                "/opt/viber/Viber",
                "/snap/bin/viber",
                os.path.join(home, "Downloads", "viber.AppImage"),
                os.path.join(home, "Downloads", "Viber.AppImage")
            ]
            for path in paths:
                if os.path.exists(path):
                    return path
            return None

    def build_ui(self):
        # 1. Left Sidebar Frame (Controls & Actions)
        sidebar = tk.Frame(self.root, bg=BG_SIDEBAR, width=220)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        # Sidebar Title
        title_lbl = tk.Label(sidebar, text="ANV VIBER", font=("Segoe UI", 16, "bold"), bg=BG_SIDEBAR, fg=VIBER_PURPLE)
        title_lbl.pack(pady=(25, 2))
        subtitle_lbl = tk.Label(sidebar, text="MANAGER TOOL", font=("Segoe UI", 8, "bold"), bg=BG_SIDEBAR, fg=TEXT_MUTED)
        subtitle_lbl.pack(pady=(0, 10))

        # User Info Panel
        user_info_frame = tk.Frame(sidebar, bg=BG_MAIN, bd=0)
        user_info_frame.pack(fill=tk.X, padx=15, pady=(0, 15), ipady=6)
        
        lbl_hello = tk.Label(user_info_frame, text=f"👤 {self.username}", font=("Segoe UI", 9, "bold"), bg=BG_MAIN, fg=TEXT_MAIN, anchor=tk.W)
        lbl_hello.pack(fill=tk.X, padx=8, pady=(4, 2))
        
        lbl_expiry = tk.Label(user_info_frame, text=f"🔑 Exp: {self.expires_info}", font=("Segoe UI", 8), bg=BG_MAIN, fg=TEXT_MUTED, anchor=tk.W)
        lbl_expiry.pack(fill=tk.X, padx=8, pady=(0, 4))

        lbl_logout = tk.Label(user_info_frame, text="🚪 Sign Out", font=("Segoe UI", 8, "underline"), bg=BG_MAIN, fg=STOP_RED, cursor="hand2", anchor=tk.W)
        lbl_logout.pack(fill=tk.X, padx=8, pady=(4, 0))
        lbl_logout.bind("<Button-1>", lambda e: self.perform_logout())

        # Action Buttons Container
        actions_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
        actions_frame.pack(fill=tk.X, padx=15)

        btn_create = ttk.Button(actions_frame, text="➕ Create Profile", style="Secondary.TButton", command=self.create_profile)
        btn_create.pack(fill=tk.X, pady=6, ipady=5)

        self.btn_delete = ttk.Button(actions_frame, text="❌ Delete Profile", style="Secondary.TButton", command=self.delete_profiles, state=tk.DISABLED)
        self.btn_delete.pack(fill=tk.X, pady=6, ipady=5)

        # Separator line
        sep = tk.Frame(actions_frame, bg=BORDER_COLOR, height=1)
        sep.pack(fill=tk.X, pady=15)

        self.btn_export = ttk.Button(actions_frame, text="📤 Export Profile(s)", style="Secondary.TButton", command=self.export_profile, state=tk.DISABLED)
        self.btn_export.pack(fill=tk.X, pady=6, ipady=5)

        btn_import = ttk.Button(actions_frame, text="📥 Import Profile(s)", style="Secondary.TButton", command=self.import_profile)
        btn_import.pack(fill=tk.X, pady=6, ipady=5)

        # Add Admin Control Panel button if user is Admin
        if self.role == "admin":
            btn_manage_users = ttk.Button(actions_frame, text="👥 Manage Users", style="Primary.TButton", command=self.open_user_management)
            btn_manage_users.pack(fill=tk.X, pady=(15, 6), ipady=5)

        # Viber Path config section in Sidebar Footer
        path_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
        path_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=(0, 10))

        self.lbl_path = tk.Label(path_frame, text="Viber Path (Detected)" if self.viber_path else "Viber Path (Not Found)", 
                                 font=("Segoe UI", 9, "bold"), bg=BG_SIDEBAR, fg="#12B76A" if self.viber_path else STOP_RED, anchor=tk.W)
        self.lbl_path.pack(fill=tk.X, pady=(0, 4))

        self.viber_path_var = tk.StringVar(value=self.viber_path or "")
        self.viber_path_var.trace_add("write", self.on_path_entry_change)

        self.entry_path = tk.Entry(path_frame, textvariable=self.viber_path_var, bg=BG_MAIN, fg=TEXT_MAIN, 
                                   insertbackground=TEXT_MAIN, font=("Segoe UI", 9), bd=1, relief=tk.FLAT)
        self.entry_path.pack(fill=tk.X, pady=(0, 6), ipady=3)

        btn_row = tk.Frame(path_frame, bg=BG_SIDEBAR)
        btn_row.pack(fill=tk.X)

        btn_auto = ttk.Button(btn_row, text="Auto Find", style="Secondary.TButton", command=self.auto_detect_viber)
        btn_auto.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4), ipady=2)

        btn_browse = ttk.Button(btn_row, text="Browse...", style="Secondary.TButton", command=self.browse_viber_path)
        btn_browse.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(4, 0), ipady=2)

        # 2. Right Main Frame (Table and Execution controls)
        main_content = tk.Frame(self.root, bg=BG_MAIN)
        main_content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Header controls inside main content
        table_controls = tk.Frame(main_content, bg=BG_MAIN)
        table_controls.pack(fill=tk.X, padx=25, pady=(20, 10))

        tk.Label(table_controls, text="PROFILES LIST", font=("Segoe UI", 12, "bold"), bg=BG_MAIN, fg=TEXT_MAIN).pack(side=tk.LEFT)

        # Selection Control Buttons
        btn_select_all = ttk.Button(table_controls, text="☑ Select All", style="Secondary.TButton", command=self.select_all_profiles)
        btn_select_all.pack(side=tk.RIGHT, padx=5)

        btn_deselect = ttk.Button(table_controls, text="☐ Deselect All", style="Secondary.TButton", command=self.deselect_all_profiles)
        btn_deselect.pack(side=tk.RIGHT, padx=5)

        # Table Card Frame (for rounded clean look)
        table_card = tk.Frame(main_content, bg=BG_CARD, bd=0, highlightthickness=0)
        table_card.pack(fill=tk.BOTH, expand=True, padx=25, pady=10)

        scrollbar = ttk.Scrollbar(table_card)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Treeview configured with specified columns
        self.tree = ttk.Treeview(
            table_card, 
            columns=("select", "stt", "name", "phone", "status", "action"), 
            show="headings", 
            yscrollcommand=scrollbar.set, 
            selectmode="extended"
        )
        self.tree.heading("select", text="", anchor=tk.CENTER)
        self.tree.heading("stt", text="STT", anchor=tk.CENTER)
        self.tree.heading("name", text="Profile Name", anchor=tk.CENTER)
        self.tree.heading("phone", text="Phone", anchor=tk.CENTER)
        self.tree.heading("status", text="Status", anchor=tk.CENTER)
        self.tree.heading("action", text="Action", anchor=tk.CENTER)

        self.tree.column("select", width=50, minwidth=50, stretch=False, anchor=tk.CENTER)
        self.tree.column("stt", width=50, minwidth=50, stretch=False, anchor=tk.CENTER)
        self.tree.column("name", width=140, minwidth=100, stretch=True, anchor=tk.CENTER)
        self.tree.column("phone", width=140, minwidth=100, stretch=True, anchor=tk.CENTER)
        self.tree.column("status", width=95, minwidth=90, stretch=False, anchor=tk.CENTER)
        self.tree.column("action", width=90, minwidth=90, stretch=False, anchor=tk.CENTER)

        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_profile_select)
        self.tree.bind("<Double-1>", lambda event: self.launch_selected_profiles())
        self.tree.bind("<Button-1>", self.on_table_click)

        scrollbar.config(command=self.tree.yview)

        # Bottom Action Bar (Launch / Stop buttons)
        action_bar = tk.Frame(main_content, bg=BG_MAIN)
        action_bar.pack(fill=tk.X, padx=25, pady=(10, 25))

        self.btn_launch = ttk.Button(action_bar, text="🚀 LAUNCH SELECTED", style="Primary.TButton", command=self.launch_selected_profiles, state=tk.DISABLED)
        self.btn_launch.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=8)

        self.btn_stop = ttk.Button(action_bar, text="🛑 STOP SELECTED", style="Stop.TButton", command=self.stop_selected_profiles, state=tk.DISABLED)
        self.btn_stop.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0), ipady=8)

    def open_user_management(self):
        UserManagementWindow(self.root, SUPABASE_URL, SUPABASE_KEY, self)

    def perform_logout(self):
        confirm = messagebox.askyesno("Confirm Sign Out", "Are you sure you want to sign out and clear saved login details?")
        if not confirm:
            return
        
        # Clear session file
        session_file = os.path.join(self.script_dir, "session.json")
        try:
            if os.path.exists(session_file):
                os.remove(session_file)
        except Exception:
            pass

        # Destroy main root and restart login window
        self.root.destroy()
        
        # Start a new login window
        global login_root
        login_root = tk.Tk()
        login_app = LoginWindow(login_root, on_success=start_main_app)
        login_root.mainloop()

    def browse_viber_path(self):
        filetypes = [("Executables", "*.exe")] if sys.platform.startswith("win") else [("All Files", "*")]
        path = filedialog.askopenfilename(title="Select Viber Executable", filetypes=filetypes)
        if path:
            self.viber_path_var.set(path)

    def on_path_entry_change(self, *args):
        path = self.viber_path_var.get().strip()
        if os.path.exists(path) and os.path.isfile(path):
            self.viber_path = path
            self.lbl_path.config(text="Viber Path (Detected)", fg="#12B76A")
        else:
            self.viber_path = None
            self.lbl_path.config(text="Viber Path (Not Found)", fg=STOP_RED)
        self.on_profile_select(None)

    def auto_detect_viber(self):
        path = self.detect_viber_path()
        if path:
            self.viber_path_var.set(path)
            messagebox.showinfo("Success", f"Automatically located Viber at:\n{path}")
        else:
            messagebox.showwarning("Not Found", "Could not automatically locate Viber. Please select manually.")

    def get_profile_phone(self, name):
        profile_path = os.path.join(self.profiles_dir, name)
        data_dir = os.path.join(profile_path, "data")
        
        viber_pc_dir = None
        if os.path.exists(os.path.join(data_dir, "Roaming", "ViberPC")):
            viber_pc_dir = os.path.join(data_dir, "Roaming", "ViberPC")
        elif os.path.exists(os.path.join(data_dir, "Home", ".ViberPC")):
            viber_pc_dir = os.path.join(data_dir, "Home", ".ViberPC")
            
        if viber_pc_dir and os.path.exists(viber_pc_dir):
            for sub in os.listdir(viber_pc_dir):
                sub_path = os.path.join(viber_pc_dir, sub)
                if os.path.isdir(sub_path):
                    clean_sub = sub.replace("+", "")
                    if clean_sub.isdigit() and len(clean_sub) >= 9:
                        if os.path.exists(os.path.join(sub_path, "Backgrounds")) or \
                           os.path.exists(os.path.join(sub_path, "Temporary")) or \
                           os.path.exists(os.path.join(sub_path, "QmlUrlCache")) or \
                           os.path.exists(os.path.join(sub_path, "viber.db")):
                            return f"+{clean_sub}"
        return "—"

    def load_profiles(self):
        selected_names = [self.tree.item(item, "values")[2] for item in self.tree.selection() if len(self.tree.item(item, "values")) > 2]

        for item in self.tree.get_children():
            self.tree.delete(item)

        if os.path.exists(self.profiles_dir):
            for index, name in enumerate(sorted(os.listdir(self.profiles_dir))):
                profile_path = os.path.join(self.profiles_dir, name)
                if os.path.isdir(profile_path):
                    status = "● Running" if name in self.running_processes else "○ Idle"
                    phone = self.get_profile_phone(name)
                    action_text = "■   ✏   🗑" if name in self.running_processes else "▶   ✏   🗑"
                    
                    item_id = self.tree.insert("", tk.END, values=(
                        "☐",
                        str(index + 1),
                        name,
                        phone,
                        status,
                        action_text
                    ))
                    if name in selected_names:
                        self.tree.selection_add(item_id)
        
        self.update_selection_visuals()

    def update_selection_visuals(self):
        selected_ids = self.tree.selection()
        for index, item in enumerate(self.tree.get_children()):
            values = list(self.tree.item(item, "values"))
            if len(values) >= 6:
                is_selected = item in selected_ids
                values[0] = "☒" if is_selected else "☐"
                values[1] = str(index + 1)
                self.tree.item(item, values=values)

    def on_profile_select(self, event):
        self.update_selection_visuals()
        
        selected_items = self.tree.selection()
        self.selected_profiles = [self.tree.item(item, "values")[2] for item in selected_items if len(self.tree.item(item, "values")) > 2]
        
        count = len(self.selected_profiles)
        
        if count > 0:
            self.btn_delete.config(state=tk.NORMAL)
            self.btn_export.config(state=tk.NORMAL)
            
            if self.viber_path:
                has_idle = any(name not in self.running_processes for name in self.selected_profiles)
                self.btn_launch.config(state=tk.NORMAL if has_idle else tk.DISABLED, 
                                       text=f"🚀 LAUNCH ({count})" if count > 1 else "🚀 LAUNCH VIBER")
                
                has_running = any(name in self.running_processes for name in self.selected_profiles)
                self.btn_stop.config(state=tk.NORMAL if has_running else tk.DISABLED, 
                                     text=f"🛑 STOP ({count})" if count > 1 else "🛑 STOP VIBER")
            else:
                self.btn_launch.config(state=tk.DISABLED)
                self.btn_stop.config(state=tk.DISABLED)
        else:
            self.btn_delete.config(state=tk.DISABLED)
            self.btn_export.config(state=tk.DISABLED)
            self.btn_launch.config(state=tk.DISABLED, text="🚀 LAUNCH SELECTED")
            self.btn_stop.config(state=tk.DISABLED, text="🛑 STOP SELECTED")

    def on_table_click(self, event):
        region = self.tree.identify_region(event.x, event.y)
        if region == "cell":
            item = self.tree.identify_row(event.y)
            column = self.tree.identify_column(event.x)
            
            values = self.tree.item(item, "values")
            if not values or len(values) <= 2:
                return
            name = values[2]
            
            if column == "#4":  # Phone column clicked
                phone = values[3]
                if phone and phone != "—":
                    self.root.clipboard_clear()
                    self.root.clipboard_append(phone)
                    self.root.update()
                    self.lbl_path.config(text=f"Copied {phone}!", fg="#12B76A")
                    self.root.after(2000, lambda: self.lbl_path.config(
                        text="Viber Path (Detected)" if self.viber_path else "Viber Path (Not Found)", 
                        fg="#12B76A" if self.viber_path else STOP_RED
                    ))
                return "break"
            elif column == "#6":  # Actions column clicked
                bbox = self.tree.bbox(item, column)
                if bbox:
                    x_cell = event.x - bbox[0]
                    cell_width = bbox[2]
                    third = cell_width / 3
                    
                    if x_cell < third:
                        is_running = name in self.running_processes
                        if is_running:
                            self.stop_single_profile(name)
                        else:
                            self.launch_single_profile(name)
                    elif x_cell < 2 * third:
                        self.rename_profile(name)
                    else:
                        self.delete_single_profile(name)
                return "break"
            else:
                if item in self.tree.selection():
                    self.tree.selection_remove(item)
                else:
                    self.tree.selection_add(item)
                self.on_profile_select(None)
                return "break"

    def launch_single_profile(self, name):
        original_selection = self.selected_profiles.copy()
        self.selected_profiles = [name]
        self.launch_selected_profiles()
        self.restore_selection_by_names(original_selection)

    def stop_single_profile(self, name):
        original_selection = self.selected_profiles.copy()
        self.selected_profiles = [name]
        self.stop_selected_profiles()
        self.restore_selection_by_names(original_selection)

    def delete_single_profile(self, name):
        original_selection = self.selected_profiles.copy()
        self.selected_profiles = [name]
        self.delete_profiles()
        self.restore_selection_by_names(original_selection)

    def restore_selection_by_names(self, names):
        self.tree.selection_remove(*self.tree.selection())
        for item in self.tree.get_children():
            val = self.tree.item(item, "values")
            if val and len(val) > 2 and val[2] in names:
                self.tree.selection_add(item)
        self.on_profile_select(None)

    def rename_profile(self, old_name):
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Profile Name")
        dialog.geometry("320x160")
        dialog.configure(bg=BG_SIDEBAR)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.wait_visibility()
        dialog.grab_set()

        lbl = tk.Label(dialog, text=f"Rename '{old_name}' to:", bg=BG_SIDEBAR, fg=TEXT_MAIN, font=("Segoe UI", 10, "bold"))
        lbl.pack(pady=(20, 5))

        entry = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, font=("Segoe UI", 10), bd=1, relief=tk.FLAT)
        entry.pack(pady=5, padx=25, fill=tk.X)
        entry.insert(0, old_name)
        entry.focus_set()

        def confirm():
            new_name = entry.get().strip()
            new_name = "".join(c for c in new_name if c.isalnum() or c in ("-", "_", " ")).strip()
            if not new_name:
                messagebox.showerror("Error", "Invalid name!", parent=dialog)
                return
            if new_name == old_name:
                dialog.destroy()
                return
            
            old_path = os.path.join(self.profiles_dir, old_name)
            new_path = os.path.join(self.profiles_dir, new_name)
            
            if os.path.exists(new_path):
                messagebox.showerror("Error", "A profile with this name already exists!", parent=dialog)
                return
            
            if old_name in self.running_processes:
                self.stop_single_profile(old_name)
                
            try:
                os.rename(old_path, new_path)
                dialog.destroy()
                self.load_profiles()
                self.on_profile_select(None)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to rename profile: {e}", parent=dialog)

        btn_ok = ttk.Button(dialog, text="Save Change", style="Primary.TButton", command=confirm)
        btn_ok.pack(pady=15)

    def select_all_profiles(self):
        for item in self.tree.get_children():
            self.tree.selection_add(item)
        self.on_profile_select(None)

    def deselect_all_profiles(self):
        self.tree.selection_remove(*self.tree.selection())
        self.on_profile_select(None)

    def create_profile(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Create Profile")
        dialog.geometry("320x160")
        dialog.configure(bg=BG_SIDEBAR)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.wait_visibility()
        dialog.grab_set()

        lbl = tk.Label(dialog, text="Profile Name:", bg=BG_SIDEBAR, fg=TEXT_MAIN, font=("Segoe UI", 10, "bold"))
        lbl.pack(pady=(20, 5))

        entry = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, font=("Segoe UI", 10), bd=1, relief=tk.FLAT)
        entry.pack(pady=5, padx=25, fill=tk.X)
        entry.focus_set()

        def confirm():
            name = entry.get().strip()
            name = "".join(c for c in name if c.isalnum() or c in ("-", "_", " ")).strip()
            if not name:
                messagebox.showerror("Error", "Invalid name! Alphanumeric, spaces, - and _ allowed.", parent=dialog)
                return
            
            target_path = os.path.join(self.profiles_dir, name)
            if os.path.exists(target_path):
                messagebox.showerror("Error", "Profile already exists!", parent=dialog)
                return
            
            os.makedirs(os.path.join(target_path, "data"), exist_ok=True)
            dialog.destroy()
            self.load_profiles()

        btn_ok = ttk.Button(dialog, text="Create", style="Primary.TButton", command=confirm)
        btn_ok.pack(pady=15)

    def delete_profiles(self):
        if not self.selected_profiles:
            return
        
        count = len(self.selected_profiles)
        confirm = messagebox.askyesno(
            "Confirm Delete", 
            f"Are you sure you want to permanently delete {count} profile(s)?\nThis will wipe all login data and chat histories!"
        )
        
        if confirm:
            profiles_to_delete = self.selected_profiles.copy()
            for name in profiles_to_delete:
                if name in self.running_processes:
                    self.stop_single_profile(name)
                
                target_path = os.path.join(self.profiles_dir, name)
                
                if not sys.platform.startswith("win"):
                    tmp_dir = os.path.join(target_path, "data", "Tmp")
                    if os.path.exists(tmp_dir):
                        try:
                            for item in os.listdir(tmp_dir):
                                if item.startswith(".mount_"):
                                    mount_path = os.path.join(tmp_dir, item)
                                    subprocess.call(["fusermount", "-u", "-z", mount_path])
                                    subprocess.call(["umount", "-l", mount_path])
                        except Exception:
                            pass

                try:
                    shutil.rmtree(target_path)
                except Exception as e:
                    messagebox.showerror("Error", f"Could not delete '{name}': {e}")
            
            self.selected_profiles = []
            self.load_profiles()
            self.on_profile_select(None)

    def launch_selected_profiles(self):
        if not self.selected_profiles or not self.viber_path:
            return

        for name in self.selected_profiles:
            if name in self.running_processes:
                continue

            profile_path = os.path.join(self.profiles_dir, name)
            data_dir = os.path.join(profile_path, "data")
            os.makedirs(data_dir, exist_ok=True)

            env = os.environ.copy()

            tmp_dir = os.path.join(data_dir, "Tmp")
            os.makedirs(tmp_dir, exist_ok=True)
            env["TEMP"] = os.path.abspath(tmp_dir)
            env["TMP"] = os.path.abspath(tmp_dir)

            if sys.platform.startswith("win"):
                userprofile_dir = os.path.join(data_dir, "UserProfile")
                roaming_dir = os.path.join(data_dir, "Roaming")
                local_dir = os.path.join(data_dir, "Local")

                os.makedirs(userprofile_dir, exist_ok=True)
                os.makedirs(os.path.join(roaming_dir, "ViberPC"), exist_ok=True)
                os.makedirs(os.path.join(local_dir, "Viber"), exist_ok=True)

                env["USERPROFILE"] = os.path.abspath(userprofile_dir)
                env["APPDATA"] = os.path.abspath(roaming_dir)
                env["LOCALAPPDATA"] = os.path.abspath(local_dir)
                
                try:
                    proc = subprocess.Popen([self.viber_path], env=env, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                    self.running_processes[name] = proc
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to start '{name}': {e}")
            else:
                home_dir = os.path.join(data_dir, "Home")
                os.makedirs(home_dir, exist_ok=True)
                
                config_dir = os.path.join(home_dir, ".config")
                local_share_dir = os.path.join(home_dir, ".local", "share")
                os.makedirs(os.path.join(config_dir, "ViberPC"), exist_ok=True)
                os.makedirs(os.path.join(local_share_dir, "viberpc"), exist_ok=True)

                env["HOME"] = os.path.abspath(home_dir)
                env["XDG_CONFIG_HOME"] = os.path.abspath(config_dir)
                env["XDG_DATA_HOME"] = os.path.abspath(local_share_dir)
                env["TMPDIR"] = os.path.abspath(tmp_dir)

                try:
                    proc = subprocess.Popen([self.viber_path], env=env, start_new_session=True)
                    self.running_processes[name] = proc
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to start '{name}': {e}")
        
        self.load_profiles()
        self.on_profile_select(None)

    def stop_selected_profiles(self):
        if not self.selected_profiles:
            return

        count = len(self.selected_profiles)
        confirm = messagebox.askyesno(
            "Confirm Stop",
            f"Are you sure you want to stop {count} running Viber profile(s)?"
        )
        if not confirm:
            return

        for name in self.selected_profiles:
            pids = self.get_profile_pids(name)
            for pid in pids:
                try:
                    if sys.platform.startswith("win"):
                        import signal
                        os.kill(pid, signal.SIGTERM)
                    else:
                        import signal
                        os.kill(pid, signal.SIGKILL)
                except Exception:
                    pass
            
            proc = self.running_processes.get(name)
            if proc and isinstance(proc, subprocess.Popen):
                try:
                    proc.kill()
                except Exception:
                    pass
            
            if name in self.running_processes:
                del self.running_processes[name]

        self.load_profiles()
        self.on_profile_select(None)

    def check_running_processes(self):
        changed = False
        if os.path.exists(self.profiles_dir):
            for name in os.listdir(self.profiles_dir):
                profile_path = os.path.join(self.profiles_dir, name)
                if os.path.isdir(profile_path):
                    pids = self.get_profile_pids(name)
                    is_running = len(pids) > 0
                    
                    if is_running and name not in self.running_processes:
                        self.running_processes[name] = True
                        changed = True
                    elif not is_running and name in self.running_processes:
                        del self.running_processes[name]
                        changed = True
        
        if changed:
            self.load_profiles()
            self.on_profile_select(None)
            
        self.root.after(1000, self.check_running_processes)

    def get_profile_pids(self, name):
        pids = []
        profile_path = os.path.join(self.profiles_dir, name)
        data_dir = os.path.join(profile_path, "data")
        
        if sys.platform.startswith("win"):
            proc = self.running_processes.get(name)
            if proc and isinstance(proc, subprocess.Popen) and proc.poll() is None:
                pids.append(proc.pid)
        else:
            home_dir = os.path.abspath(os.path.join(data_dir, "Home"))
            if os.path.exists('/proc'):
                for pid_str in os.listdir('/proc'):
                    if pid_str.isdigit():
                        try:
                            with open(os.path.join('/proc', pid_str, 'environ'), 'rb') as f:
                                env_data = f.read()
                            env_vars = env_data.split(b'\x00')
                            for var in env_vars:
                                if var.startswith(b'HOME='):
                                    home_val = var[5:].decode('utf-8', errors='ignore')
                                    if os.path.abspath(home_val) == home_dir:
                                        pids.append(int(pid_str))
                                        break
                        except Exception:
                            continue
        return pids

    def export_profile(self):
        if not self.selected_profiles:
            return
        
        if len(self.selected_profiles) == 1:
            target_name = self.selected_profiles[0]
            save_path = filedialog.asksaveasfilename(
                title=f"Export Profile '{target_name}'",
                initialfile=f"{target_name}.viberprofile",
                filetypes=[("Viber Profile", "*.viberprofile")],
                defaultextension=".viberprofile"
            )
            
            if not save_path:
                return
            self._do_export(target_name, save_path)
        else:
            save_dir = filedialog.askdirectory(title=f"Select Directory to Export {len(self.selected_profiles)} Profiles")
            if not save_dir:
                return
            
            success_count = 0
            for name in self.selected_profiles:
                save_path = os.path.join(save_dir, f"{name}.viberprofile")
                if self._do_export(name, save_path, quiet=True):
                    success_count += 1
            
            messagebox.showinfo("Export Complete", f"Successfully exported {success_count} / {len(self.selected_profiles)} profiles to:\n{save_dir}")

    def _do_export(self, target_name, save_path, quiet=False):
        profile_path = os.path.join(self.profiles_dir, target_name)
        data_dir = os.path.join(profile_path, "data")
        
        viber_pc_dir = None
        if os.path.exists(os.path.join(data_dir, "Roaming", "ViberPC")):
            viber_pc_dir = os.path.join(data_dir, "Roaming", "ViberPC")
        elif os.path.exists(os.path.join(data_dir, "Home", ".ViberPC")):
            viber_pc_dir = os.path.join(data_dir, "Home", ".ViberPC")
        
        if not viber_pc_dir or not os.listdir(viber_pc_dir):
            if not quiet:
                messagebox.showerror("Export Failed", f"No Viber session data found for '{target_name}'. Run it at least once.")
            return False

        try:
            with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(viber_pc_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, viber_pc_dir)
                        zipf.write(file_path, rel_path)
            if not quiet:
                messagebox.showinfo("Export Successful", f"Profile exported successfully to:\n{save_path}")
            return True
        except Exception as e:
            if not quiet:
                messagebox.showerror("Export Failed", f"An error occurred exporting '{target_name}': {e}")
            return False

    def import_profile(self):
        import_paths = filedialog.askopenfilenames(
            title="Import Profiles",
            filetypes=[("Viber Profile", "*.viberprofile")]
        )
        
        if not import_paths:
            return
        
        success_count = 0
        for import_path in import_paths:
            default_name = os.path.splitext(os.path.basename(import_path))[0]
            default_name = "".join(c for c in default_name if c.isalnum() or c in ("-", "_", " "))
            
            target_path = os.path.join(self.profiles_dir, default_name)
            
            final_name = default_name
            counter = 1
            while os.path.exists(target_path):
                final_name = f"{default_name}_{counter}"
                target_path = os.path.join(self.profiles_dir, final_name)
                counter += 1
                
            data_dir = os.path.join(target_path, "data")
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

            try:
                with zipfile.ZipFile(import_path, 'r') as zipf:
                    zipf.extractall(viber_pc_dest)
                success_count += 1
            except Exception as e:
                shutil.rmtree(target_path, ignore_errors=True)
                messagebox.showerror("Import Failed", f"Could not extract zip for '{default_name}': {e}")
        
        self.load_profiles()
        self.on_profile_select(None)
        if success_count > 0:
            messagebox.showinfo("Import Complete", f"Successfully imported {success_count} profile(s)!")

    # ==========================================
    # DATABASE & TELEGRAM SYNC SYSTEM
    # ==========================================
    def start_remote_sync_loop(self):
        if SUPABASE_URL == "https://hqbsupczeujqgrkvrdjx.supabase.co" and SUPABASE_KEY == "sb_publishable_249FmOz7LjCvA6-dAlTHkg_mngyhFt9" and self.user_id == "00000000-0000-0000-0000-000000000000":
            # Bypass background sync loop for offline bypass mode
            return

        if SUPABASE_URL == "https://your-project.supabase.co" or not SUPABASE_URL:
            return

        def sync_worker():
            headers = {
                "apikey": SUPABASE_KEY,
                "Authorization": f"Bearer {SUPABASE_KEY}",
                "Content-Type": "application/json"
            }
            while True:
                try:
                    local_profiles = []
                    if os.path.exists(self.profiles_dir):
                        for name in os.listdir(self.profiles_dir):
                            if os.path.isdir(os.path.join(self.profiles_dir, name)):
                                status = "running" if name in self.running_processes else "idle"
                                phone = self.get_profile_phone(name)
                                local_profiles.append({
                                    "user_id": self.user_id,
                                    "profile_name": name,
                                    "phone_number": phone,
                                    "status": status,
                                    "updated_at": datetime.utcnow().isoformat() + "Z"
                                })

                    # Push local profile statuses to db
                    if local_profiles:
                        del_url = f"{SUPABASE_URL}/rest/v1/client_profiles?user_id=eq.{self.user_id}"
                        requests.delete(del_url, headers=headers, timeout=10)
                        
                        post_url = f"{SUPABASE_URL}/rest/v1/client_profiles"
                        requests.post(post_url, json=local_profiles, headers=headers, timeout=10)

                    # Check for remote commands
                    cmd_url = f"{SUPABASE_URL}/rest/v1/remote_commands?user_id=eq.{self.user_id}&status=eq.pending"
                    cmd_resp = requests.get(cmd_url, headers=headers, timeout=10)
                    if cmd_resp.status_code == 200:
                        commands = cmd_resp.json()
                        for cmd in commands:
                            threading.Thread(target=self.process_remote_command, args=(cmd, headers), daemon=True).start()

                except Exception:
                    pass
                time.sleep(15)

        threading.Thread(target=sync_worker, daemon=True).start()

    def process_remote_command(self, cmd, headers):
        cmd_id = cmd["id"]
        command_type = cmd["command"]
        profile_name = cmd["profile_name"]

        # Mark command as processing
        patch_url = f"{SUPABASE_URL}/rest/v1/remote_commands?id=eq.{cmd_id}"
        requests.patch(patch_url, json={"status": "processing"}, headers=headers, timeout=10)

        try:
            if command_type == "UPLOAD_PROFILE":
                profile_path = os.path.join(self.profiles_dir, profile_name)
                if not os.path.exists(profile_path):
                    raise FileNotFoundError(f"Profile '{profile_name}' not found locally.")

                # Package profile
                zip_path = os.path.join(self.script_dir, f"{profile_name}_temp.zip")
                data_dir = os.path.join(profile_path, "data")
                viber_pc_dir = None
                if os.path.exists(os.path.join(data_dir, "Roaming", "ViberPC")):
                    viber_pc_dir = os.path.join(data_dir, "Roaming", "ViberPC")
                elif os.path.exists(os.path.join(data_dir, "Home", ".ViberPC")):
                    viber_pc_dir = os.path.join(data_dir, "Home", ".ViberPC")

                if not viber_pc_dir or not os.listdir(viber_pc_dir):
                    raise FileNotFoundError("No Viber data found inside the profile.")

                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(viber_pc_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_path, viber_pc_dir)
                            zipf.write(file_path, rel_path)

                # AES Encrypt the zip file before uploading to Telegram Bot
                key = get_profile_key(self.user_id, profile_name)
                encrypt_file(zip_path, key)

                # Upload to Telegram Bot
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
                with open(zip_path, 'rb') as f:
                    files = {'document': (f"{profile_name}.viberprofile", f)}
                    data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': f"Backup Profile: {profile_name} (User ID: {self.user_id})"}
                    resp = requests.post(url, data=data, files=files, timeout=60)
                
                if os.path.exists(zip_path):
                    os.remove(zip_path)

                if resp.status_code != 200:
                    raise Exception(f"Telegram upload failed: {resp.text}")

                file_id = resp.json()["result"]["document"]["file_id"]

                # Complete command
                requests.patch(patch_url, json={"status": "completed", "telegram_file_id": file_id}, headers=headers, timeout=10)

            elif command_type == "DOWNLOAD_PROFILE":
                file_id = cmd.get("telegram_file_id")
                if not file_id:
                    raise ValueError("Download command is missing 'telegram_file_id'.")

                # Get file path from Telegram
                get_file_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
                file_info_resp = requests.get(get_file_url, timeout=20)
                if file_info_resp.status_code != 200:
                    raise Exception(f"Failed to query file path from Telegram: {file_info_resp.text}")

                file_path = file_info_resp.json()["result"]["file_path"]
                download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"

                zip_dest = os.path.join(self.script_dir, f"{profile_name}_temp_down.zip")
                with requests.get(download_url, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    with open(zip_dest, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)

                # AES Decrypt the zip file after downloading
                key = get_profile_key(self.user_id, profile_name)
                decrypt_file(zip_dest, key)

                if profile_name in self.running_processes:
                    self.stop_single_profile(profile_name)

                target_path = os.path.join(self.profiles_dir, profile_name)
                shutil.rmtree(target_path, ignore_errors=True)
                data_dir = os.path.join(target_path, "data")
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

                with zipfile.ZipFile(zip_dest, 'r') as zipf:
                    zipf.extractall(viber_pc_dest)

                if os.path.exists(zip_dest):
                    os.remove(zip_dest)

                # Complete command
                requests.patch(patch_url, json={"status": "completed"}, headers=headers, timeout=10)

                self.root.after(0, self.load_profiles)

        except Exception as e:
            requests.patch(patch_url, json={"status": "failed"}, headers=headers, timeout=10)


class UserManagementWindow:
    def __init__(self, parent, supabase_url, supabase_key, main_app):
        self.parent = parent
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.main_app = main_app
        
        self.window = tk.Toplevel(parent)
        self.window.title("ANV Viber - User Management Panel")
        self.window.geometry("840x520")
        self.window.configure(bg=BG_MAIN)
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.wait_visibility()
        self.window.grab_set()

        self.headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json"
        }

        self.all_users = []
        self.build_ui()
        self.load_users()

    def build_ui(self):
        # Header title
        title_frame = tk.Frame(self.window, bg=BG_SIDEBAR, height=50)
        title_frame.pack(fill=tk.X)
        title_lbl = tk.Label(title_frame, text="👥 CLIENTS MANAGEMENT PANEL", font=("Segoe UI", 12, "bold"), bg=BG_SIDEBAR, fg=VIBER_PURPLE)
        title_lbl.pack(side=tk.LEFT, padx=20, pady=10)

        # Filters Bar
        filter_bar = tk.Frame(self.window, bg=BG_SIDEBAR, bd=0)
        filter_bar.pack(fill=tk.X, padx=20, pady=(10, 0), ipady=5)

        # Search box
        tk.Label(filter_bar, text="Search Username:", font=("Segoe UI", 9, "bold"), bg=BG_SIDEBAR, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(15, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self.apply_filters)
        self.entry_search = tk.Entry(filter_bar, textvariable=self.search_var, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, font=("Segoe UI", 9), bd=1, relief=tk.FLAT, width=22)
        self.entry_search.pack(side=tk.LEFT, padx=5, ipady=2)

        # Status filter dropdown
        tk.Label(filter_bar, text="Status:", font=("Segoe UI", 9, "bold"), bg=BG_SIDEBAR, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(20, 5))
        self.filter_status_var = tk.StringVar(value="All")
        self.combo_filter_status = ttk.Combobox(filter_bar, textvariable=self.filter_status_var, values=["All", "active", "blocked"], state="readonly", width=10)
        self.combo_filter_status.pack(side=tk.LEFT, padx=5)
        self.combo_filter_status.bind("<<ComboboxSelected>>", self.apply_filters)

        # Main Split Container
        content_frame = tk.Frame(self.window, bg=BG_MAIN)
        content_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(10, 15))

        # Right control panel sidebar
        ctrl_frame = tk.Frame(content_frame, bg=BG_SIDEBAR, width=180)
        ctrl_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))
        ctrl_frame.pack_propagate(False)

        # Control Panel Buttons
        btn_add = ttk.Button(ctrl_frame, text="➕ Add User", style="Primary.TButton", command=self.add_user)
        btn_add.pack(fill=tk.X, padx=15, pady=(20, 8), ipady=4)

        self.btn_edit = ttk.Button(ctrl_frame, text="✏ Edit User", style="Secondary.TButton", command=self.edit_user, state=tk.DISABLED)
        self.btn_edit.pack(fill=tk.X, padx=15, pady=6, ipady=4)

        self.btn_view_profiles = ttk.Button(ctrl_frame, text="📂 View Profiles", style="Secondary.TButton", command=self.view_client_profiles, state=tk.DISABLED)
        self.btn_view_profiles.pack(fill=tk.X, padx=15, pady=6, ipady=4)

        self.btn_reset_hwid = ttk.Button(ctrl_frame, text="🔄 Reset HWID", style="Secondary.TButton", command=self.reset_hwid, state=tk.DISABLED)
        self.btn_reset_hwid.pack(fill=tk.X, padx=15, pady=6, ipady=4)

        sep = tk.Frame(ctrl_frame, bg=BORDER_COLOR, height=1)
        sep.pack(fill=tk.X, padx=15, pady=12)

        self.btn_delete = ttk.Button(ctrl_frame, text="🗑 Delete User", style="Stop.TButton", command=self.delete_user, state=tk.DISABLED)
        self.btn_delete.pack(fill=tk.X, padx=15, pady=6, ipady=4)

        # Left Table Frame
        table_frame = tk.Frame(content_frame, bg=BG_CARD)
        table_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(table_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(
            table_frame,
            columns=("stt", "username", "hwid", "status", "role", "expires"),
            show="headings",
            yscrollcommand=scrollbar.set,
            selectmode="browse"
        )
        self.tree.heading("stt", text="STT", anchor=tk.CENTER)
        self.tree.heading("username", text="Username", anchor=tk.CENTER)
        self.tree.heading("hwid", text="HWID (Device)", anchor=tk.CENTER)
        self.tree.heading("status", text="Status", anchor=tk.CENTER)
        self.tree.heading("role", text="Role", anchor=tk.CENTER)
        self.tree.heading("expires", text="Expires At", anchor=tk.CENTER)

        self.tree.column("stt", width=50, minwidth=50, stretch=False, anchor=tk.CENTER)
        self.tree.column("username", width=120, anchor=tk.CENTER)
        self.tree.column("hwid", width=130, anchor=tk.CENTER)
        self.tree.column("status", width=90, anchor=tk.CENTER)
        self.tree.column("role", width=80, anchor=tk.CENTER)
        self.tree.column("expires", width=130, anchor=tk.CENTER)

        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        scrollbar.config(command=self.tree.yview)

    def load_users(self):
        try:
            url = f"{self.supabase_url}/rest/v1/users?order=username.asc"
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                self.all_users = resp.json()
                self.apply_filters()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to retrieve user list: {e}", parent=self.window)

    def apply_filters(self, *args):
        # Clear Treeview
        for item in self.tree.get_children():
            self.tree.delete(item)

        search_query = self.search_var.get().strip().lower()
        status_filter = self.filter_status_var.get()

        index = 1
        for row in self.all_users:
            username = row.get("username", "")
            status = row.get("status", "active")
            
            # Text Filter
            if search_query and search_query not in username.lower():
                continue
            
            # Status Filter
            if status_filter != "All" and status != status_filter:
                continue

            hwid_disp = row.get("hwid")[:12] + "..." if row.get("hwid") else "Unbound"
            exp_disp = row.get("expires_at").split("T")[0] if row.get("expires_at") else "Permanent"

            self.tree.insert("", tk.END, iid=row["id"], values=(
                str(index),
                username,
                hwid_disp,
                status,
                row.get("role", "user"),
                exp_disp
            ))
            index += 1

        self.on_select(None)

    def on_select(self, event):
        selected = self.tree.selection()
        if selected:
            self.btn_edit.config(state=tk.NORMAL)
            self.btn_view_profiles.config(state=tk.NORMAL)
            self.btn_reset_hwid.config(state=tk.NORMAL)
            self.btn_delete.config(state=tk.NORMAL)
        else:
            self.btn_edit.config(state=tk.DISABLED)
            self.btn_view_profiles.config(state=tk.DISABLED)
            self.btn_reset_hwid.config(state=tk.DISABLED)
            self.btn_delete.config(state=tk.DISABLED)

    def add_user(self):
        dialog = tk.Toplevel(self.window)
        dialog.title("Add New User")
        dialog.geometry("340x260")
        dialog.configure(bg=BG_SIDEBAR)
        dialog.resizable(False, False)
        dialog.transient(self.window)
        dialog.wait_visibility()
        dialog.grab_set()

        tk.Label(dialog, text="Username:", bg=BG_SIDEBAR, fg=TEXT_MAIN, font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, padx=30, pady=(15, 2))
        entry_user = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, bd=1, relief=tk.FLAT)
        entry_user.pack(fill=tk.X, padx=30, ipady=3)

        tk.Label(dialog, text="Password:", bg=BG_SIDEBAR, fg=TEXT_MAIN, font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, padx=30, pady=(10, 2))
        entry_pass = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, bd=1, relief=tk.FLAT)
        entry_pass.pack(fill=tk.X, padx=30, ipady=3)

        tk.Label(dialog, text="Expiry (YYYY-MM-DD) or empty for permanent:", bg=BG_SIDEBAR, fg=TEXT_MAIN, font=("Segoe UI", 9)).pack(anchor=tk.W, padx=30, pady=(10, 2))
        entry_exp = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, bd=1, relief=tk.FLAT)
        entry_exp.pack(fill=tk.X, padx=30, ipady=3)

        def save():
            username = entry_user.get().strip()
            password = entry_pass.get().strip()
            exp = entry_exp.get().strip()

            if not username or not password:
                messagebox.showerror("Error", "Username and Password cannot be empty!", parent=dialog)
                return

            hashed_pass = hashlib.sha256(password.encode()).hexdigest()
            payload = {
                "username": username,
                "password_hash": hashed_pass,
                "status": "active",
                "role": "user"
            }

            if exp:
                try:
                    datetime.strptime(exp, "%Y-%m-%d")
                    payload["expires_at"] = exp + "T23:59:59+00:00"
                except ValueError:
                    messagebox.showerror("Error", "Invalid Expiry Date Format! Use YYYY-MM-DD.", parent=dialog)
                    return

            try:
                url = f"{self.supabase_url}/rest/v1/users"
                resp = requests.post(url, headers=self.headers, json=payload, timeout=10)
                if resp.status_code in (200, 201, 204):
                    dialog.destroy()
                    self.load_users()
                    messagebox.showinfo("Success", f"User '{username}' created successfully!", parent=self.window)
                else:
                    messagebox.showerror("Error", f"Failed to save user: {resp.text}", parent=dialog)
            except Exception as e:
                messagebox.showerror("Error", f"Error: {e}", parent=dialog)

        btn_save = ttk.Button(dialog, text="Create User", style="Primary.TButton", command=save)
        btn_save.pack(pady=20, ipady=4, padx=30, fill=tk.X)

    def edit_user(self):
        user_id = self.tree.selection()[0]
        values = self.tree.item(user_id, "values")
        username = values[1]
        current_status = values[3]
        current_role = values[4]
        current_expiry = values[5]

        dialog = tk.Toplevel(self.window)
        dialog.title(f"Edit User - {username}")
        dialog.geometry("340x360")
        dialog.configure(bg=BG_SIDEBAR)
        dialog.resizable(False, False)
        dialog.transient(self.window)
        dialog.wait_visibility()
        dialog.grab_set()

        # Edit Username
        tk.Label(dialog, text="Username:", bg=BG_SIDEBAR, fg=TEXT_MAIN, font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, padx=30, pady=(15, 2))
        entry_user = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, bd=1, relief=tk.FLAT)
        entry_user.pack(fill=tk.X, padx=30, ipady=3)
        entry_user.insert(0, username)

        # Edit Password
        tk.Label(dialog, text="New Password (leave empty to keep current):", bg=BG_SIDEBAR, fg=TEXT_MAIN, font=("Segoe UI", 9, "bold")).pack(anchor=tk.W, padx=30, pady=(10, 2))
        entry_pass = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, bd=1, relief=tk.FLAT)
        entry_pass.pack(fill=tk.X, padx=30, ipady=3)

        # Expiry
        tk.Label(dialog, text="Expiry (YYYY-MM-DD) or empty for permanent:", bg=BG_SIDEBAR, fg=TEXT_MAIN).pack(anchor=tk.W, padx=30, pady=(10, 2))
        entry_exp = tk.Entry(dialog, bg=BG_MAIN, fg=TEXT_MAIN, insertbackground=TEXT_MAIN, bd=1, relief=tk.FLAT)
        entry_exp.pack(fill=tk.X, padx=30, ipady=3)
        if current_expiry != "Permanent":
            entry_exp.insert(0, current_expiry)

        # Status Combobox
        tk.Label(dialog, text="Status:", bg=BG_SIDEBAR, fg=TEXT_MAIN).pack(anchor=tk.W, padx=30, pady=(10, 2))
        combo_status = ttk.Combobox(dialog, values=["active", "blocked"], state="readonly")
        combo_status.pack(fill=tk.X, padx=30)
        combo_status.set(current_status)

        # Role Combobox
        tk.Label(dialog, text="Role:", bg=BG_SIDEBAR, fg=TEXT_MAIN).pack(anchor=tk.W, padx=30, pady=(10, 2))
        combo_role = ttk.Combobox(dialog, values=["user", "admin"], state="readonly")
        combo_role.pack(fill=tk.X, padx=30)
        combo_role.set(current_role)

        def update():
            new_username = entry_user.get().strip()
            password = entry_pass.get().strip()
            exp = entry_exp.get().strip()
            status = combo_status.get()
            role = combo_role.get()

            if not new_username:
                messagebox.showerror("Error", "Username cannot be empty!", parent=dialog)
                return

            payload = {
                "username": new_username,
                "status": status,
                "role": role,
                "expires_at": None
            }

            if password:
                hashed_pass = hashlib.sha256(password.encode()).hexdigest()
                payload["password_hash"] = hashed_pass

            if exp:
                try:
                    datetime.strptime(exp, "%Y-%m-%d")
                    payload["expires_at"] = exp + "T23:59:59+00:00"
                except ValueError:
                    messagebox.showerror("Error", "Invalid Expiry Format! Use YYYY-MM-DD.", parent=dialog)
                    return

            try:
                url = f"{self.supabase_url}/rest/v1/users?id=eq.{user_id}"
                resp = requests.patch(url, headers=self.headers, json=payload, timeout=10)
                if resp.status_code in (200, 204):
                    dialog.destroy()
                    self.load_users()
                    messagebox.showinfo("Success", "User updated successfully!", parent=self.window)
                else:
                    messagebox.showerror("Error", f"Failed to update user: {resp.text}", parent=dialog)
            except Exception as e:
                messagebox.showerror("Error", f"Error: {e}", parent=dialog)

        btn_update = ttk.Button(dialog, text="Save Changes", style="Primary.TButton", command=update)
        btn_update.pack(pady=20, ipady=4, padx=30, fill=tk.X)

    def view_client_profiles(self):
        user_id = self.tree.selection()[0]
        values = self.tree.item(user_id, "values")
        username = values[1]

        ClientProfilesViewWindow(self.window, user_id, username, self.supabase_url, self.supabase_key, self.main_app)

    def reset_hwid(self):
        user_id = self.tree.selection()[0]
        values = self.tree.item(user_id, "values")
        username = values[1]

        confirm = messagebox.askyesno("Confirm Reset", f"Are you sure you want to reset device ID (HWID) for '{username}'?", parent=self.window)
        if confirm:
            try:
                url = f"{self.supabase_url}/rest/v1/users?id=eq.{user_id}"
                resp = requests.patch(url, headers=self.headers, json={"hwid": None}, timeout=10)
                if resp.status_code in (200, 204):
                    self.load_users()
                    messagebox.showinfo("Success", f"HWID reset successfully for '{username}'!", parent=self.window)
                else:
                    messagebox.showerror("Error", f"Failed to reset HWID: {resp.text}", parent=self.window)
            except Exception as e:
                messagebox.showerror("Error", f"Error: {e}", parent=self.window)

    def delete_user(self):
        user_id = self.tree.selection()[0]
        values = self.tree.item(user_id, "values")
        username = values[1]
        role = values[4]

        if role == "admin":
            messagebox.showerror("Error", "You cannot delete an Administrator account!", parent=self.window)
            return

        confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete user '{username}'?", parent=self.window)
        if confirm:
            try:
                url = f"{self.supabase_url}/rest/v1/users?id=eq.{user_id}"
                resp = requests.delete(url, headers=self.headers, timeout=10)
                if resp.status_code in (200, 204):
                    self.load_users()
                    messagebox.showinfo("Success", f"User '{username}' deleted successfully!", parent=self.window)
                else:
                    messagebox.showerror("Error", f"Failed to delete user: {resp.text}", parent=self.window)
            except Exception as e:
                messagebox.showerror("Error", f"Error: {e}", parent=self.window)


class ClientProfilesViewWindow:
    def __init__(self, parent, client_id, client_username, supabase_url, supabase_key, main_app_root):
        self.parent = parent
        self.client_id = client_id
        self.client_username = client_username
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.main_app_root = main_app_root
        
        self.window = tk.Toplevel(parent)
        self.window.title(f"Viber Profiles - {client_username}")
        self.window.geometry("540x410")
        self.window.configure(bg=BG_MAIN)
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.wait_visibility()
        self.window.grab_set()

        self.headers = {
            "apikey": self.supabase_key,
            "Authorization": f"Bearer {self.supabase_key}",
            "Content-Type": "application/json"
        }

        self.build_ui()
        self.load_profiles()

    def build_ui(self):
        title_frame = tk.Frame(self.window, bg=BG_SIDEBAR, height=45)
        title_frame.pack(fill=tk.X)
        title_lbl = tk.Label(title_frame, text=f"📂 PROFILES OF {self.client_username.upper()}", font=("Segoe UI", 11, "bold"), bg=BG_SIDEBAR, fg=VIBER_PURPLE)
        title_lbl.pack(side=tk.LEFT, padx=15, pady=8)

        # Content container
        content = tk.Frame(self.window, bg=BG_MAIN)
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # Bottom Control Panel
        bottom_panel = tk.Frame(content, bg=BG_MAIN)
        bottom_panel.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        self.btn_pull = ttk.Button(bottom_panel, text="📥 Pull Profile to Admin", style="Primary.TButton", command=self.pull_profile, state=tk.DISABLED)
        self.btn_pull.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5), ipady=5)

        self.btn_push = ttk.Button(bottom_panel, text="📤 Push Profile to Client", style="Secondary.TButton", command=self.push_profile)
        self.btn_push.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0), ipady=5)

        # Profile list Table Card
        table_card = tk.Frame(content, bg=BG_CARD)
        table_card.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(table_card)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(
            table_card,
            columns=("stt", "name", "phone", "status"),
            show="headings",
            yscrollcommand=scrollbar.set,
            selectmode="browse"
        )
        self.tree.heading("stt", text="STT", anchor=tk.CENTER)
        self.tree.heading("name", text="Profile Name", anchor=tk.CENTER)
        self.tree.heading("phone", text="Phone Number", anchor=tk.CENTER)
        self.tree.heading("status", text="Status", anchor=tk.CENTER)

        self.tree.column("stt", width=50, minwidth=50, stretch=False, anchor=tk.CENTER)
        self.tree.column("name", width=160, anchor=tk.CENTER)
        self.tree.column("phone", width=160, anchor=tk.CENTER)
        self.tree.column("status", width=100, anchor=tk.CENTER)

        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)
        scrollbar.config(command=self.tree.yview)

    def load_profiles(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            url = f"{self.supabase_url}/rest/v1/client_profiles?user_id=eq.{self.client_id}&order=profile_name.asc"
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                for idx, row in enumerate(resp.json()):
                    self.tree.insert("", tk.END, values=(
                        str(idx + 1),
                        row["profile_name"],
                        row.get("phone_number") or "—",
                        row.get("status") or "idle"
                    ))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch profiles: {e}", parent=self.window)

    def on_select(self, event):
        if self.tree.selection():
            self.btn_pull.config(state=tk.NORMAL)
        else:
            self.btn_pull.config(state=tk.DISABLED)

    def pull_profile(self):
        selected = self.tree.selection()
        if not selected:
            return
        
        values = self.tree.item(selected[0], "values")
        profile_name = values[1]

        # Confirm command
        confirm = messagebox.askyesno(
            "Confirm Remote Pull",
            f"Are you sure you want to request profile '{profile_name}' from {self.client_username}?\n"
            f"This will command the client tool to upload the profile zip to Telegram and pull it to this machine.",
            parent=self.window
        )
        if not confirm:
            return

        # Show a beautiful progress dialog
        progress = tk.Toplevel(self.window)
        progress.title("Remote Profile Pulling")
        progress.geometry("380x140")
        progress.configure(bg=BG_SIDEBAR)
        progress.resizable(False, False)
        progress.transient(self.window)
        progress.wait_visibility()
        progress.grab_set()

        lbl_status = tk.Label(progress, text="Sending pull request to client...", bg=BG_SIDEBAR, fg=TEXT_MAIN, font=("Segoe UI", 10, "bold"))
        lbl_status.pack(pady=(25, 10))

        bar = ttk.Progressbar(progress, mode="indeterminate", length=280)
        bar.pack(pady=5)
        bar.start(10)

        # Worker thread
        def pull_worker():
            try:
                # 1. Send remote upload command to client
                cmd_payload = {
                    "user_id": self.client_id,
                    "command": "UPLOAD_PROFILE",
                    "profile_name": profile_name,
                    "status": "pending"
                }
                cmd_url = f"{self.supabase_url}/rest/v1/remote_commands"
                resp = requests.post(cmd_url, headers=self.headers, json=cmd_payload, timeout=10)
                if resp.status_code not in (200, 201, 204):
                    raise Exception(f"Failed to post command: {resp.text}")

                # 2. Query matching command to get its ID
                get_url = f"{self.supabase_url}/rest/v1/remote_commands?user_id=eq.{self.client_id}&profile_name=eq.{profile_name}&command=eq.UPLOAD_PROFILE&order=created_at.desc"
                get_resp = requests.get(get_url, headers=self.headers, timeout=10)
                if get_resp.status_code != 200 or not get_resp.json():
                    raise Exception("Failed to retrieve command ID.")

                cmd_record = get_resp.json()[0]
                cmd_id = cmd_record["id"]

                # 3. Poll command until complete
                start_time = time.time()
                timeout = 60 # 60 seconds timeout
                telegram_file_id = None
                
                while time.time() - start_time < timeout:
                    time.sleep(2)
                    lbl_status.config(text="Waiting for client to process and upload zip...")
                    
                    poll_url = f"{self.supabase_url}/rest/v1/remote_commands?id=eq.{cmd_id}"
                    poll_resp = requests.get(poll_url, headers=self.headers, timeout=10)
                    if poll_resp.status_code == 200:
                        recs = poll_resp.json()
                        if recs:
                            status = recs[0].get("status")
                            if status == "completed":
                                telegram_file_id = recs[0].get("telegram_file_id")
                                break
                            elif status == "failed":
                                raise Exception("Client reported failure packaging the profile.")
                
                if not telegram_file_id:
                    raise TimeoutError("Timeout waiting for client response.")

                lbl_status.config(text="Downloading profile zip from Telegram...")
                
                # 4. Request file path from Telegram Bot
                get_file_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={telegram_file_id}"
                file_info_resp = requests.get(get_file_url, timeout=20)
                if file_info_resp.status_code != 200:
                    raise Exception(f"Telegram query failed: {file_info_resp.text}")

                telegram_path = file_info_resp.json()["result"]["file_path"]
                download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{telegram_path}"

                # 5. Download stream
                script_dir = os.path.dirname(os.path.abspath(__file__))
                zip_dest = os.path.join(script_dir, f"{profile_name}_remote_down.zip")
                with requests.get(download_url, stream=True, timeout=60) as r:
                    r.raise_for_status()
                    with open(zip_dest, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            f.write(chunk)

                # AES Decrypt the downloaded zip file before extraction
                key = get_profile_key(self.client_id, profile_name)
                decrypt_file(zip_dest, key)

                lbl_status.config(text="Extracting profile locally...")

                # 6. Stop and delete local profile if it exists
                dest_profile_dir = os.path.join(self.main_app_root.profiles_dir, profile_name)
                
                # Use main app methods via main_app_root to stop processes safely
                if hasattr(self.main_app_root, "running_processes") and profile_name in self.main_app_root.running_processes:
                    self.main_app_root.stop_single_profile(profile_name)

                shutil.rmtree(dest_profile_dir, ignore_errors=True)
                data_dir = os.path.join(dest_profile_dir, "data")
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

                with zipfile.ZipFile(zip_dest, 'r') as zipf:
                    zipf.extractall(viber_pc_dest)

                if os.path.exists(zip_dest):
                    os.remove(zip_dest)

                # Clean up command database record
                del_cmd_url = f"{self.supabase_url}/rest/v1/remote_commands?id=eq.{cmd_id}"
                requests.delete(del_cmd_url, headers=self.headers, timeout=10)

                # Success
                progress.destroy()
                # Reload Admin main profile list
                if hasattr(self.main_app_root, "load_profiles"):
                    self.main_app_root.load_profiles()

                messagebox.showinfo("Success", f"Profile '{profile_name}' successfully downloaded, decrypted, and imported to your machine!", parent=self.window)

            except Exception as e:
                progress.destroy()
                messagebox.showerror("Error", f"Failed to pull remote profile:\n{e}", parent=self.window)

        threading.Thread(target=pull_worker, daemon=True).start()

    def push_profile(self):
        # 1. Fetch Admin's local profiles
        local_profiles = []
        if os.path.exists(self.main_app_root.profiles_dir):
            for name in os.listdir(self.main_app_root.profiles_dir):
                if os.path.isdir(os.path.join(self.main_app_root.profiles_dir, name)):
                    local_profiles.append(name)

        if not local_profiles:
            messagebox.showerror("Error", "You do not have any local profiles to push!", parent=self.window)
            return

        # 2. Open Profile selection dialog
        dialog = tk.Toplevel(self.window)
        dialog.title("Select Profile to Push")
        dialog.geometry("320x170")
        dialog.configure(bg=BG_SIDEBAR)
        dialog.resizable(False, False)
        dialog.transient(self.window)
        dialog.wait_visibility()
        dialog.grab_set()

        tk.Label(dialog, text="Select Local Profile to Push:", bg=BG_SIDEBAR, fg=TEXT_MAIN, font=("Segoe UI", 9, "bold")).pack(pady=(20, 5))
        combo_profile = ttk.Combobox(dialog, values=sorted(local_profiles), state="readonly")
        combo_profile.pack(fill=tk.X, padx=30, pady=5)
        combo_profile.current(0)

        def confirm_push():
            selected_profile = combo_profile.get()
            dialog.destroy()

            # Verify local profile ViberPC data
            profile_path = os.path.join(self.main_app_root.profiles_dir, selected_profile)
            data_dir = os.path.join(profile_path, "data")
            viber_pc_dir = None
            if os.path.exists(os.path.join(data_dir, "Roaming", "ViberPC")):
                viber_pc_dir = os.path.join(data_dir, "Roaming", "ViberPC")
            elif os.path.exists(os.path.join(data_dir, "Home", ".ViberPC")):
                viber_pc_dir = os.path.join(data_dir, "Home", ".ViberPC")

            if not viber_pc_dir or not os.listdir(viber_pc_dir):
                messagebox.showerror("Push Failed", f"Profile '{selected_profile}' does not have any Viber login data to push!", parent=self.window)
                return

            # Confirm push to client
            confirm_act = messagebox.askyesno(
                "Confirm Remote Push",
                f"Are you sure you want to push your local profile '{selected_profile}' to {self.client_username}?\n"
                f"This will OVERWRITE the profile on the client machine if it already exists!",
                parent=self.window
            )
            if not confirm_act:
                return

            # Show progress window
            progress = tk.Toplevel(self.window)
            progress.title("Remote Profile Pushing")
            progress.geometry("380x140")
            progress.configure(bg=BG_SIDEBAR)
            progress.resizable(False, False)
            progress.transient(self.window)
            progress.wait_visibility()
            progress.grab_set()

            lbl_status = tk.Label(progress, text="Zipping and encrypting local profile...", bg=BG_SIDEBAR, fg=TEXT_MAIN, font=("Segoe UI", 10, "bold"))
            lbl_status.pack(pady=(25, 10))

            bar = ttk.Progressbar(progress, mode="indeterminate", length=280)
            bar.pack(pady=5)
            bar.start(10)

            # Threaded execution
            def push_worker():
                zip_path = os.path.join(self.main_app_root.script_dir, f"{selected_profile}_push_temp.zip")
                try:
                    # 1. Package local profile
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        for root, dirs, files in os.walk(viber_pc_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                rel_path = os.path.relpath(file_path, viber_pc_dir)
                                zipf.write(file_path, rel_path)

                    # AES Encrypt the zip file before uploading
                    key = get_profile_key(self.client_id, selected_profile)
                    encrypt_file(zip_path, key)

                    # 2. Upload to Telegram Bot
                    lbl_status.config(text="Uploading secure zip to Telegram...")
                    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
                    with open(zip_path, 'rb') as f:
                        files = {'document': (f"{selected_profile}.viberprofile", f)}
                        data = {'chat_id': TELEGRAM_CHAT_ID, 'caption': f"Push Profile: {selected_profile} to User ID: {self.client_id}"}
                        resp = requests.post(url, data=data, files=files, timeout=60)
                    
                    if os.path.exists(zip_path):
                        os.remove(zip_path)

                    if resp.status_code != 200:
                        raise Exception(f"Telegram upload failed: {resp.text}")

                    telegram_file_id = resp.json()["result"]["document"]["file_id"]

                    # 3. Create remote command for client to download it
                    cmd_payload = {
                        "user_id": self.client_id,
                        "command": "DOWNLOAD_PROFILE",
                        "profile_name": selected_profile,
                        "telegram_file_id": telegram_file_id,
                        "status": "pending"
                    }
                    cmd_url = f"{self.supabase_url}/rest/v1/remote_commands"
                    post_resp = requests.post(cmd_url, headers=self.headers, json=cmd_payload, timeout=10)
                    if post_resp.status_code not in (200, 201, 204):
                        raise Exception(f"Failed to post download command: {post_resp.text}")

                    # 4. Fetch command ID to poll
                    get_url = f"{self.supabase_url}/rest/v1/remote_commands?user_id=eq.{self.client_id}&profile_name=eq.{selected_profile}&command=eq.DOWNLOAD_PROFILE&order=created_at.desc"
                    get_resp = requests.get(get_url, headers=self.headers, timeout=10)
                    if get_resp.status_code != 200 or not get_resp.json():
                        raise Exception("Failed to retrieve command ID.")

                    cmd_record = get_resp.json()[0]
                    cmd_id = cmd_record["id"]

                    # 5. Poll command status
                    start_time = time.time()
                    timeout = 60 # 60 seconds timeout
                    success = False
                    
                    while time.time() - start_time < timeout:
                        time.sleep(2)
                        lbl_status.config(text="Waiting for client to download and decrypt profile...")
                        
                        poll_url = f"{self.supabase_url}/rest/v1/remote_commands?id=eq.{cmd_id}"
                        poll_resp = requests.get(poll_url, headers=self.headers, timeout=10)
                        if poll_resp.status_code == 200:
                            recs = poll_resp.json()
                            if recs:
                                status = recs[0].get("status")
                                if status == "completed":
                                    success = True
                                    break
                                elif status == "failed":
                                    raise Exception("Client reported failure importing the profile.")

                    if not success:
                        raise TimeoutError("Timeout waiting for client to process download.")

                    # Delete command record from database
                    del_cmd_url = f"{self.supabase_url}/rest/v1/remote_commands?id=eq.{cmd_id}"
                    requests.delete(del_cmd_url, headers=self.headers, timeout=10)

                    # Reload profiles view list
                    self.load_profiles()

                    progress.destroy()
                    messagebox.showinfo("Success", f"Profile '{selected_profile}' pushed and decrypted on client machine successfully!", parent=self.window)

                except Exception as e:
                    if os.path.exists(zip_path):
                        os.remove(zip_path)
                    progress.destroy()
                    messagebox.showerror("Error", f"Failed to push remote profile:\n{e}", parent=self.window)

            threading.Thread(target=push_worker, daemon=True).start()

        btn_confirm = ttk.Button(dialog, text="Push Profile", style="Primary.TButton", command=confirm_push)
        btn_confirm.pack(pady=15, ipady=3, padx=30, fill=tk.X)


def start_main_app(user_id, username, expires_info, role):
    global login_root
    login_root.destroy()

    main_root = tk.Tk()
    app = AnvViberManager(main_root, user_id, username, expires_info, role)
    main_root.mainloop()


if __name__ == "__main__":
    login_root = tk.Tk()
    login_app = LoginWindow(login_root, on_success=start_main_app)
    login_root.mainloop()
