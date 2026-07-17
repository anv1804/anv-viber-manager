"""
gui/push_history.py
PushHistoryWindow — Shows push history logs queried from remote_commands,
with date filters, search, and daily summary statistics.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date

import requests

from config import (
    BG_MAIN, BG_SIDEBAR, BG_CARD, TEXT_MAIN, TEXT_MUTED,
    VIBER_PURPLE, BORDER_COLOR,
)
import services.supabase as db


class PushHistoryWindow:
    def __init__(self, parent: tk.Widget, user_map: dict):
        self.parent = parent
        self.user_map = user_map  # Map user_id -> username for easier display

        self.window = tk.Toplevel(parent)
        self.window.title("ANV Viber - Push History Log")
        self.window.geometry("800x500")
        self.window.configure(bg=BG_MAIN)
        self.window.resizable(False, False)
        self.window.transient(parent)
        self.window.wait_visibility()
        self.window.grab_set()

        self.headers = db.make_headers()
        self.all_history: list[dict] = []

        self._build_ui()
        self._load_history()

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self.window, bg=BG_SIDEBAR, height=50)
        hdr.pack(fill=tk.X)
        tk.Label(hdr, text="📜 REMOTE PUSH HISTORY LOG",
                 font=("Segoe UI", 12, "bold"), bg=BG_SIDEBAR, fg=VIBER_PURPLE,
                 ).pack(side=tk.LEFT, padx=20, pady=10)

        # Filters Bar
        bar = tk.Frame(self.window, bg=BG_SIDEBAR)
        bar.pack(fill=tk.X, padx=20, pady=(10, 0), ipady=6)

        # Date filter
        tk.Label(bar, text="From Date (YYYY-MM-DD):", font=("Segoe UI", 9, "bold"),
                 bg=BG_SIDEBAR, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(15, 5))
        
        self.date_from_var = tk.StringVar(value=date.today().isoformat())
        self.entry_from = tk.Entry(bar, textvariable=self.date_from_var, bg=BG_MAIN, fg=TEXT_MAIN,
                                   insertbackground=TEXT_MAIN, font=("Segoe UI", 9), bd=0, relief=tk.FLAT, width=12)
        self.entry_from.pack(side=tk.LEFT, padx=5, ipady=2)

        tk.Label(bar, text="To Date (YYYY-MM-DD):", font=("Segoe UI", 9, "bold"),
                 bg=BG_SIDEBAR, fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(15, 5))
        
        self.date_to_var = tk.StringVar(value=date.today().isoformat())
        self.entry_to = tk.Entry(bar, textvariable=self.date_to_var, bg=BG_MAIN, fg=TEXT_MAIN,
                                 insertbackground=TEXT_MAIN, font=("Segoe UI", 9), bd=0, relief=tk.FLAT, width=12)
        self.entry_to.pack(side=tk.LEFT, padx=5, ipady=2)

        ttk.Button(bar, text="🔍 Filter", style="Primary.TButton", command=self._apply_date_filter).pack(side=tk.LEFT, padx=15)

        # Main Table
        table_frame = tk.Frame(self.window, bg=BG_CARD)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        sb = ttk.Scrollbar(table_frame)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

        self.tree = ttk.Treeview(
            table_frame,
            columns=("stt", "time", "client", "profile", "status"),
            show="headings", yscrollcommand=sb.set, selectmode="none"
        )
        for col, text, width in [
            ("stt",     "STT",         50),
            ("time",    "Time (UTC)",  180),
            ("client",  "Target Client", 150),
            ("profile", "Profile Name", 260),
            ("status",  "Status",      120),
        ]:
            self.tree.heading(col, text=text, anchor=tk.CENTER)
            self.tree.column(col, width=width, anchor=tk.CENTER)

        self.tree.pack(fill=tk.BOTH, expand=True)
        sb.config(command=self.tree.yview)

        # Footer Stats Summary
        self.summary_frame = tk.Frame(self.window, bg=BG_SIDEBAR)
        self.summary_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=20, pady=(0, 15), ipady=8)

        self.lbl_stats = tk.Label(
            self.summary_frame,
            text="Total Success: 0 | Total Failed: 0",
            font=("Segoe UI", 10, "bold"), bg=BG_SIDEBAR, fg=TEXT_MAIN
        )
        self.lbl_stats.pack(padx=20, side=tk.LEFT)

    def _load_history(self):
        try:
            # Query remote commands where command is 'DOWNLOAD_PROFILE' (which represents pushes)
            url = f"{db.SUPABASE_URL}/rest/v1/remote_commands?command=eq.DOWNLOAD_PROFILE&order=created_at.desc"
            resp = requests.get(url, headers=self.headers, timeout=10)
            if resp.status_code == 200:
                self.all_history = resp.json()
            else:
                self.all_history = []
            self._apply_date_filter()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch history: {e}", parent=self.window)

    def _apply_date_filter(self):
        # Clear table
        for item in self.tree.get_children():
            self.tree.delete(item)

        from_str = self.date_from_var.get().strip()
        to_str = self.date_to_var.get().strip()

        try:
            # Parse limits
            from_date = datetime.strptime(from_str, "%Y-%m-%d").date() if from_str else None
            to_date = datetime.strptime(to_str, "%Y-%m-%d").date() if to_str else None
        except ValueError:
            messagebox.showerror("Invalid Date", "Please enter date in YYYY-MM-DD format.", parent=self.window)
            return

        success_count = 0
        failed_count = 0
        display_idx = 1

        for row in self.all_history:
            created_str = row.get("created_at") or ""
            if not created_str:
                continue
            
            # Format time '2026-07-17T05:27:23.291709+00:00'
            try:
                dt = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                row_date = dt.date()
                time_disp = dt.strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                time_disp = created_str.split(".")[0]
                try:
                    row_date = datetime.strptime(created_str.split("T")[0], "%Y-%m-%d").date()
                except Exception:
                    continue

            # Apply filters bounds
            if from_date and row_date < from_date:
                continue
            if to_date and row_date > to_date:
                continue

            user_id = row.get("user_id")
            client_name = self.user_map.get(user_id, f"Client ({user_id[:6]})")
            profile_name = row.get("profile_name", "—")
            status = row.get("status") or "pending"

            # Parse stats
            if status == "completed":
                status_disp = "✅ Success"
                success_count += 1
            elif status == "failed":
                status_disp = "❌ Failed"
                failed_count += 1
            else:
                status_disp = "⏳ Pending"

            self.tree.insert("", tk.END, values=(
                str(display_idx),
                time_disp,
                client_name,
                profile_name,
                status_disp,
            ))
            display_idx += 1

        self.lbl_stats.config(
            text=f"📊 Daily Summary:   Total Pushes: {display_idx - 1}   |   ✅ Success: {success_count}   |   ❌ Failed: {failed_count}"
        )
