"""
gui/main_window_ui.py
MainWindowUI — handles all Tkinter layout, widgets, styling, and search/filter GUI
elements for the main window, separating design from coordination logic.
"""
import sys
import tkinter as tk
from tkinter import ttk

from config import (
    BG_MAIN, BG_SIDEBAR, BG_CARD, TEXT_MAIN, TEXT_MUTED,
    VIBER_PURPLE, VIBER_HOVER, STOP_RED, STOP_HOVER,
    BTN_DARK, BTN_DARK_HOVER, BORDER_COLOR,
)

from PIL import ImageTk
import gui.icons as icons

def setup_styles():
    s = ttk.Style()
    s.theme_use("clam")
    s.configure(".", background=BG_MAIN, foreground=TEXT_MAIN, borderwidth=0)
    s.configure("TFrame", background=BG_MAIN)

    s.configure(
        "Treeview",
        background=BG_CARD, fieldbackground=BG_CARD, foreground=TEXT_MAIN,
        rowheight=32, borderwidth=0, font=("DejaVu Sans, Ubuntu", 10),
    )
    s.configure(
        "Treeview.Heading",
        background=BG_SIDEBAR, foreground=TEXT_MAIN,
        font=("DejaVu Sans, Ubuntu", 10, "bold"), borderwidth=0,
    )
    s.map("Treeview", background=[("selected", VIBER_PURPLE)])

    s.configure(
        "Primary.TButton",
        background=VIBER_PURPLE, foreground="white",
        font=("DejaVu Sans, Ubuntu", 10, "bold"), borderwidth=0, focusthickness=0,
    )
    s.map("Primary.TButton", background=[("active", VIBER_HOVER)])

    s.configure(
        "Stop.TButton",
        background=STOP_RED, foreground="white",
        font=("DejaVu Sans, Ubuntu", 10, "bold"), borderwidth=0, focusthickness=0,
    )
    s.map("Stop.TButton", background=[("active", STOP_HOVER)])

    s.configure(
        "Secondary.TButton",
        background=BTN_DARK, foreground=TEXT_MAIN,
        font=("DejaVu Sans, Ubuntu", 10), borderwidth=0, focusthickness=0,
    )
    s.map("Secondary.TButton", background=[("active", BTN_DARK_HOVER)])

    s.configure("Vertical.TScrollbar", gripcount=0, background=BG_CARD, troughcolor=BG_MAIN)


def build_ui_layout(app):
    # Cache to prevent garbage collection of ImageTk objects
    app.icons = {
        "user": ImageTk.PhotoImage(icons.get_user_icon(TEXT_MAIN)),
        "key": ImageTk.PhotoImage(icons.get_key_icon(TEXT_MUTED)),
        "logout": ImageTk.PhotoImage(icons.get_logout_icon(STOP_RED)),
        "create": ImageTk.PhotoImage(icons.get_create_icon(TEXT_MAIN)),
        "delete": ImageTk.PhotoImage(icons.get_delete_icon(STOP_RED)),
        "export": ImageTk.PhotoImage(icons.get_export_icon(TEXT_MAIN)),
        "import": ImageTk.PhotoImage(icons.get_import_icon(TEXT_MAIN)),
        "users": ImageTk.PhotoImage(icons.get_users_icon(TEXT_MAIN)),
        "sync": ImageTk.PhotoImage(icons.get_sync_icon("white")),
        "folder": ImageTk.PhotoImage(icons.get_folder_icon(TEXT_MUTED)),
        "search": ImageTk.PhotoImage(icons.get_search_icon(TEXT_MUTED)),
        "x": ImageTk.PhotoImage(icons.get_delete_icon(TEXT_MUTED)),
    }

    # ── Sidebar ────────────────────────────────────────────────────
    sidebar = tk.Frame(app.root, bg=BG_SIDEBAR, width=220)
    sidebar.pack(side=tk.LEFT, fill=tk.Y)
    sidebar.pack_propagate(False)

    tk.Label(sidebar, text="ANV VIBER", font=("DejaVu Sans, Ubuntu, Segoe UI", 16, "bold"),
             bg=BG_SIDEBAR, fg=VIBER_PURPLE).pack(pady=(25, 2))
    tk.Label(sidebar, text="MANAGER TOOL", font=("DejaVu Sans, Ubuntu, Segoe UI", 8, "bold"),
             bg=BG_SIDEBAR, fg=TEXT_MUTED).pack(pady=(0, 10))

    # User info panel
    info = tk.Frame(sidebar, bg=BG_MAIN)
    info.pack(fill=tk.X, padx=15, pady=(0, 15), ipady=6)
    
    lbl_user = tk.Label(info, text=f" {app.username}", image=app.icons["user"], compound=tk.LEFT,
                        font=("DejaVu Sans, Ubuntu, Segoe UI", 9, "bold"), bg=BG_MAIN, fg=TEXT_MAIN, anchor=tk.W)
    lbl_user.pack(fill=tk.X, padx=8, pady=(4, 2))
    
    lbl_exp = tk.Label(info, text=f" Exp: {app.expires_info}", image=app.icons["key"], compound=tk.LEFT,
                       font=("DejaVu Sans, Ubuntu, Segoe UI", 8), bg=BG_MAIN, fg=TEXT_MUTED, anchor=tk.W)
    lbl_exp.pack(fill=tk.X, padx=8, pady=(0, 4))
    
    lbl_logout = tk.Label(info, text=" Sign Out", image=app.icons["logout"], compound=tk.LEFT,
                          font=("DejaVu Sans, Ubuntu, Segoe UI", 8, "underline"), bg=BG_MAIN, fg=STOP_RED, cursor="hand2", anchor=tk.W)
    lbl_logout.pack(fill=tk.X, padx=8, pady=(4, 0))
    lbl_logout.bind("<Button-1>", lambda e: app.perform_logout())

    # Action buttons
    actions = tk.Frame(sidebar, bg=BG_SIDEBAR)
    actions.pack(fill=tk.X, padx=15)

    ttk.Button(actions, text=" Create Profile", image=app.icons["create"], compound=tk.LEFT,
               style="Secondary.TButton", command=app.create_profile).pack(fill=tk.X, pady=6, ipady=5)

    app.btn_delete = ttk.Button(actions, text=" Delete Profile", image=app.icons["delete"], compound=tk.LEFT,
                                 style="Secondary.TButton", command=app.delete_profiles, state=tk.DISABLED)
    app.btn_delete.pack(fill=tk.X, pady=6, ipady=5)

    tk.Frame(actions, bg=BORDER_COLOR, height=1).pack(fill=tk.X, pady=15)

    app.btn_export = ttk.Button(actions, text=" Export Profile(s)", image=app.icons["export"], compound=tk.LEFT,
                                 style="Secondary.TButton", command=app.export_profile, state=tk.DISABLED)
    app.btn_export.pack(fill=tk.X, pady=6, ipady=5)

    ttk.Button(actions, text=" Import Profile(s)", image=app.icons["import"], compound=tk.LEFT,
               style="Secondary.TButton", command=app.import_profile).pack(fill=tk.X, pady=6, ipady=5)

    tk.Frame(actions, bg=BORDER_COLOR, height=1).pack(fill=tk.X, pady=15)

    if app.role == "admin":
        ttk.Button(actions, text=" Manage Users", image=app.icons["users"], compound=tk.LEFT,
                   style="Secondary.TButton", command=app._open_user_management).pack(fill=tk.X, pady=6, ipady=5)

    # Viber Path input at bottom of sidebar
    path_frame = tk.Frame(sidebar, bg=BG_SIDEBAR)
    path_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=20)

    app.lbl_path = tk.Label(
        path_frame,
        text="Viber Path (Detected)" if app.viber_path else "Viber Path (Not Found)",
        font=("DejaVu Sans, Ubuntu, Segoe UI", 8, "bold"), bg=BG_SIDEBAR,
        fg="#12B76A" if app.viber_path else STOP_RED, anchor=tk.W,
    )
    app.lbl_path.pack(fill=tk.X, pady=(0, 4))

    entry_path_frame = tk.Frame(path_frame, bg=BG_SIDEBAR)
    entry_path_frame.pack(fill=tk.X)

    app.viber_path_var = tk.StringVar(value=app.viber_path or "")
    app.viber_path_var.trace_add("write", app._on_path_change)
    entry_path = tk.Entry(
        entry_path_frame, textvariable=app.viber_path_var, bg=BG_MAIN, fg=TEXT_MAIN,
        insertbackground=TEXT_MAIN, font=("DejaVu Sans, Ubuntu, Segoe UI", 9), bd=0, relief=tk.FLAT,
    )
    entry_path.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=4, padx=5) # custom padding

    btn_browse = tk.Label(entry_path_frame, image=app.icons["folder"], bg=BG_MAIN, cursor="hand2")
    btn_browse.pack(side=tk.RIGHT, fill=tk.Y, padx=(1, 0))
    btn_browse.bind("<Button-1>", lambda e: app._browse_viber_path())

    btn_auto = tk.Label(path_frame, text=" Auto Detect Viber", image=app.icons["search"], compound=tk.LEFT,
                        font=("DejaVu Sans, Ubuntu, Segoe UI", 8, "underline"),
                        bg=BG_SIDEBAR, fg=VIBER_PURPLE, cursor="hand2", anchor=tk.W)
    btn_auto.pack(fill=tk.X, pady=(5, 0))
    btn_auto.bind("<Button-1>", lambda e: app._auto_detect_viber())

    # ── Main content ───────────────────────────────────────────────
    main_content = tk.Frame(app.root, bg=BG_MAIN)
    main_content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    top_bar = tk.Frame(main_content, bg=BG_MAIN)
    top_bar.pack(fill=tk.X, padx=25, pady=(20, 6))
    tk.Label(top_bar, text="PROFILES LIST", font=("DejaVu Sans, Ubuntu, Segoe UI", 12, "bold"),
             bg=BG_MAIN, fg=TEXT_MAIN).pack(side=tk.LEFT)
    ttk.Button(top_bar, text=" Select All", style="Secondary.TButton",
               command=app.select_all_profiles).pack(side=tk.RIGHT, padx=5)
    ttk.Button(top_bar, text=" Deselect All", style="Secondary.TButton",
               command=app.deselect_all_profiles).pack(side=tk.RIGHT, padx=5)
    ttk.Button(top_bar, text=" Sync All", image=app.icons["sync"], compound=tk.LEFT,
               style="Primary.TButton", command=app.sync_all_profiles).pack(side=tk.RIGHT, padx=(0, 10))

    # ── Filter / Search Bar ────────────────────────────────────────
    filter_bar = tk.Frame(main_content, bg=BG_SIDEBAR)
    filter_bar.pack(fill=tk.X, padx=25, pady=(0, 6))

    tk.Label(filter_bar, image=app.icons["search"], bg=BG_SIDEBAR).pack(side=tk.LEFT, padx=(10, 2), pady=5)

    app._filter_name = tk.StringVar()
    app._filter_name.trace_add("write", lambda *_: app._apply_filter())
    tk.Entry(filter_bar, textvariable=app._filter_name, bg=BG_MAIN, fg=TEXT_MAIN,
             insertbackground=TEXT_MAIN, font=("DejaVu Sans, Ubuntu, Segoe UI", 9), bd=0, relief=tk.FLAT,
             width=14).pack(side=tk.LEFT, ipady=4, padx=(0, 4))
    tk.Label(filter_bar, text="Tên", font=("DejaVu Sans, Ubuntu, Segoe UI", 8), bg=BG_SIDEBAR,
             fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 10))

    tk.Label(filter_bar, image=app.icons["user"], bg=BG_SIDEBAR).pack(side=tk.LEFT, padx=(4, 2))
    app._filter_phone = tk.StringVar()
    app._filter_phone.trace_add("write", lambda *_: app._apply_filter())
    tk.Entry(filter_bar, textvariable=app._filter_phone, bg=BG_MAIN, fg=TEXT_MAIN,
             insertbackground=TEXT_MAIN, font=("DejaVu Sans, Ubuntu, Segoe UI", 9), bd=0, relief=tk.FLAT,
             width=14).pack(side=tk.LEFT, ipady=4, padx=(0, 4))
    tk.Label(filter_bar, text="SĐT", font=("DejaVu Sans, Ubuntu, Segoe UI", 8), bg=BG_SIDEBAR,
             fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(0, 10))

    tk.Label(filter_bar, text="Trạng thái:", font=("DejaVu Sans, Ubuntu, Segoe UI", 8, "bold"), bg=BG_SIDEBAR,
             fg=TEXT_MUTED).pack(side=tk.LEFT, padx=(4, 4))
    app._filter_status = tk.StringVar(value="Tất cả")
    status_combo = ttk.Combobox(
        filter_bar, textvariable=app._filter_status,
        values=["Tất cả", "Running", "Idle"],
        state="readonly", width=10,
    )
    status_combo.pack(side=tk.LEFT, ipady=2)
    status_combo.bind("<<ComboboxSelected>>", lambda *_: app._apply_filter())

    btn_clear = tk.Label(filter_bar, text=" Xóa", image=app.icons["x"], compound=tk.LEFT,
                         font=("DejaVu Sans, Ubuntu, Segoe UI", 8, "underline"),
                         bg=BG_SIDEBAR, fg=TEXT_MUTED, cursor="hand2")
    btn_clear.pack(side=tk.LEFT, padx=(12, 0))
    btn_clear.bind("<Button-1>", lambda _: app._clear_filter())

    table_card = tk.Frame(main_content, bg=BG_CARD)
    table_card.pack(fill=tk.BOTH, expand=True, padx=25, pady=(0, 6))

    scrollbar = ttk.Scrollbar(table_card)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    app.tree = ttk.Treeview(
        table_card,
        columns=("select", "stt", "name", "phone", "status", "action"),
        show="headings",
        yscrollcommand=scrollbar.set,
        selectmode="extended",
    )
    for col, text, width, stretch in [
        ("select", "Sel",         50,  False),
        ("stt",    "STT",         50,  False),
        ("name",   "Profile Name",140, True),
        ("phone",  "Phone",       140, True),
        ("status", "Status",       95, False),
        ("action", "Action",       90, False),
    ]:
        app.tree.heading(col, text=text, anchor=tk.CENTER)
        app.tree.column(col, width=width, minwidth=width, stretch=stretch, anchor=tk.CENTER)

    app.tree.pack(fill=tk.BOTH, expand=True)
    app.tree.bind("<<TreeviewSelect>>", app._on_profile_select)
    app.tree.bind("<Double-1>", lambda e: app.launch_selected_profiles())
    app.tree.bind("<Button-1>", app._on_table_click)
    scrollbar.config(command=app.tree.yview)

    # Bottom action bar
    action_bar = tk.Frame(main_content, bg=BG_MAIN)
    action_bar.pack(fill=tk.X, padx=25, pady=(10, 25))

    app.icons["launch"] = ImageTk.PhotoImage(icons.get_play_icon("white"))
    app.btn_launch = ttk.Button(
        action_bar, text=" LAUNCH SELECTED", image=app.icons["launch"], compound=tk.LEFT,
        style="Primary.TButton", command=app.launch_selected_profiles, state=tk.DISABLED,
    )
    app.btn_launch.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10), ipady=8)

    app.icons["stop"] = ImageTk.PhotoImage(icons.get_stop_icon("white"))
    app.btn_stop = ttk.Button(
        action_bar, text=" STOP SELECTED", image=app.icons["stop"], compound=tk.LEFT,
        style="Stop.TButton", command=app.stop_selected_profiles, state=tk.DISABLED,
    )
    app.btn_stop.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0), ipady=8)
