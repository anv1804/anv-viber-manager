"""
main.py — Entry point for ANV Viber Manager.
"""
import sys
import tkinter as tk
from gui.login import LoginWindow


def start_app():
    root = tk.Tk()
    root.withdraw()

    def on_login_success(user_id, username, expires_info, role):
        root.withdraw()
        app_win = tk.Toplevel()
        app_win.protocol("WM_DELETE_WINDOW", lambda: _quit(app_win))
        from gui.dashboard import Dashboard
        Dashboard(app_win, user_id, username, expires_info, role)
        app_win.mainloop()

    def _quit(win):
        win.destroy()
        root.quit()

    LoginWindow(root, on_login_success)
    root.mainloop()


if __name__ == "__main__":
    start_app()
