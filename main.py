"""
main.py — Entry point for ANV Viber Manager (Local Version).
"""
import tkinter as tk
from gui.dashboard import Dashboard


def start_app():
    root = tk.Tk()
    # Launch Dashboard directly as the main window
    Dashboard(root)
    root.mainloop()


if __name__ == "__main__":
    start_app()
