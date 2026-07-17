#!/usr/bin/env python3
"""
main.py — ANV Viber Manager entry point.
Starts the login window; on success, launches the main application window.
"""
import tkinter as tk

from gui.login_window import LoginWindow
from gui.main_window import AnvViberManager

# Module-level handle so perform_logout() can destroy the active login window
login_root: tk.Tk | None = None


def start_main_app(user_id: str, username: str, expires_info: str, role: str) -> None:
    """Called by LoginWindow on successful authentication."""
    global login_root
    if login_root is not None:
        login_root.destroy()
        login_root = None

    main_root = tk.Tk()
    AnvViberManager(main_root, user_id, username, expires_info, role)
    main_root.mainloop()


def restart_login() -> None:
    """Called by AnvViberManager.perform_logout() to re-show the login screen."""
    global login_root
    login_root = tk.Tk()
    LoginWindow(login_root, on_success=start_main_app)
    login_root.mainloop()


if __name__ == "__main__":
    restart_login()
