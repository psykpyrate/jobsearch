from __future__ import annotations

import csv
import ctypes
from datetime import datetime
import json
import re
import subprocess
import threading
import textwrap
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
import winsound

from job_scanner import (
    DEFAULT_DISTANCE_MILES,
    DEFAULT_HOURS_OLD,
    DEFAULT_PAY_MAX,
    DEFAULT_PAY_MIN,
    DEFAULT_RESULTS_PER_TERM,
    DEFAULT_SEARCH_TERMS,
    DEFAULT_SITES,
    DEFAULT_ZIP_CODE,
    SITE_DISPLAY_NAMES,
    JobListing,
    JobSearchConfig,
    MAX_DISTANCE_MILES,
    search_jobs,
)

APP_TITLE = "Local Job Listing Scanner"
EXPORT_FILENAME = "job_scan_results.csv"
SETTINGS_FILENAME = "job_scanner_settings.json"
STARTUP_MP3_FILENAME = "95.mp3"
DEFAULT_THEME_NAME = "Neon Pulse"
DEFAULT_TEXT_SIZE = 11
DEFAULT_DENSITY = "Comfortable"
THEMES = {
    "Neon Pulse": {
        "bg_main": "#050816",
        "bg_card": "#0b1226",
        "bg_input": "#0a1020",
        "bg_tree": "#09111f",
        "bg_header": "#101a30",
        "fg_main": "#e6f7ff",
        "fg_muted": "#8fb7d9",
        "accent_primary": "#19e3ff",
        "accent_secondary": "#ff4fd8",
        "accent_button": "#3b82ff",
        "accent_highlight": "#ffe66d",
        "row_selected": "#123a63",
    },
    "Cyber Sunset": {
        "bg_main": "#11040f",
        "bg_card": "#1b0d1d",
        "bg_input": "#160916",
        "bg_tree": "#170b16",
        "bg_header": "#261226",
        "fg_main": "#ffeef8",
        "fg_muted": "#f0a9c7",
        "accent_primary": "#ff7a18",
        "accent_secondary": "#ff3cac",
        "accent_button": "#ff5e5b",
        "accent_highlight": "#ffd166",
        "row_selected": "#542040",
    },
    "Matrix Mint": {
        "bg_main": "#03110d",
        "bg_card": "#082019",
        "bg_input": "#061813",
        "bg_tree": "#071712",
        "bg_header": "#0d2a21",
        "fg_main": "#e8fff6",
        "fg_muted": "#9cdcc2",
        "accent_primary": "#5cffb2",
        "accent_secondary": "#35f0d2",
        "accent_button": "#11a36c",
        "accent_highlight": "#c9ff6a",
        "row_selected": "#104634",
    },
    "Electric Violet": {
        "bg_main": "#090511",
        "bg_card": "#130a22",
        "bg_input": "#10081d",
        "bg_tree": "#0f091c",
        "bg_header": "#1d1231",
        "fg_main": "#f3ecff",
        "fg_muted": "#b8a8e8",
        "accent_primary": "#9b5cff",
        "accent_secondary": "#ff5de4",
        "accent_button": "#6d5efc",
        "accent_highlight": "#7afcff",
        "row_selected": "#34205f",
    },
    "Arctic Glow": {
        "bg_main": "#071018",
        "bg_card": "#0d1824",
        "bg_input": "#0a1420",
        "bg_tree": "#0b1521",
        "bg_header": "#132334",
        "fg_main": "#ecfbff",
        "fg_muted": "#93c8d8",
        "accent_primary": "#6ae8ff",
        "accent_secondary": "#6aa6ff",
        "accent_button": "#2f7ef7",
        "accent_highlight": "#7dffcf",
        "row_selected": "#173659",
    },
    "High Contrast": {
        "bg_main": "#000000",
        "bg_card": "#0b0b0b",
        "bg_input": "#000000",
        "bg_tree": "#000000",
        "bg_header": "#141414",
        "fg_main": "#ffffff",
        "fg_muted": "#d9d9d9",
        "accent_primary": "#00ffff",
        "accent_secondary": "#ffea00",
        "accent_button": "#0057ff",
        "accent_highlight": "#00ff66",
        "row_selected": "#222222",
    },
}
STATE_OPTIONS = (
    "",
    "AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD",
    "MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC",
    "SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","DC",
)
SITE_OPTIONS = (
    "linkedin",
    "indeed",
    "zip_recruiter",
    "dice",
    "usajobs",
    "brassring",
    "disney_jobs",
    "paramount_jobs",
    "warner_bros_jobs",
    "universal_jobs",
    "sony_pictures_jobs",
    "netflix_jobs",
    "glassdoor",
)
DEFAULT_AUTO_SCAN_MINUTES = 15
NOTIFICATION_TITLE = "Job Scanner"
RESULT_COLUMNS = ("title", "company", "location", "site", "pay", "posted", "term")
RESULT_COLUMN_LABELS = {
    "title": "Title",
    "company": "Company",
    "location": "Location",
    "site": "Site",
    "pay": "Pay",
    "posted": "Posted",
    "term": "Matched",
}
RESULT_COLUMN_WIDTHS = {
    "title": 280,
    "company": 180,
    "location": 180,
    "site": 110,
    "pay": 135,
    "posted": 155,
    "term": 150,
}


class JobScannerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_TITLE)
        self.settings_path = Path(__file__).with_name(SETTINGS_FILENAME)
        self.settings = self._load_settings()
        self.theme_var = tk.StringVar(value=self.settings.get("theme_name", DEFAULT_THEME_NAME))
        self.text_size_var = tk.IntVar(value=int(self.settings.get("text_size", DEFAULT_TEXT_SIZE)))
        self.density_var = tk.StringVar(value=self.settings.get("density", DEFAULT_DENSITY))
        self._set_initial_window_size()
        self.root.minsize(980, 680)

        self.zip_var = tk.StringVar(value=self.settings.get("zip_code", DEFAULT_ZIP_CODE))
        self.city_var = tk.StringVar(value=self.settings.get("city", ""))
        self.state_var = tk.StringVar(value=self.settings.get("state", ""))
        self.distance_var = tk.StringVar(value=self.settings.get("distance", ""))
        self.hours_old_var = tk.StringVar(value=self.settings.get("hours_old", ""))
        self.results_var = tk.StringVar(value=self.settings.get("results_per_term", ""))
        self.pay_min_var = tk.StringVar(value=self.settings.get("pay_min", ""))
        self.pay_max_var = tk.StringVar(value=self.settings.get("pay_max", ""))
        self.custom_url_var = tk.StringVar(value=self.settings.get("custom_url", ""))
        self.remote_only_var = tk.BooleanVar(value=bool(self.settings.get("remote_only", False)))
        self.auto_scan_var = tk.BooleanVar(value=bool(self.settings.get("auto_scan", False)))
        self.auto_scan_minutes_var = tk.StringVar(value=str(self.settings.get("auto_scan_minutes", DEFAULT_AUTO_SCAN_MINUTES)))
        self.desktop_alert_var = tk.BooleanVar(value=bool(self.settings.get("desktop_alert", True)))
        self.flash_alert_var = tk.BooleanVar(value=bool(self.settings.get("flash_alert", True)))
        self.sound_alert_var = tk.BooleanVar(value=bool(self.settings.get("sound_alert", False)))
        self.status_var = tk.StringVar(value="Ready")
        self.location_var = tk.StringVar(value="Location: not searched yet")
        self.summary_var = tk.StringVar(value="Results: 0")

        saved_sites = set(self.settings.get("sites", list(DEFAULT_SITES)))
        self.site_vars = {site: tk.BooleanVar(value=site in saved_sites) for site in SITE_OPTIONS}
        self.column_vars = {
            column: tk.BooleanVar(value=column in set(self.settings.get("visible_columns", list(RESULT_COLUMNS))))
            for column in RESULT_COLUMNS
        }
        self.results: list[JobListing] = []
        self.new_results: list[JobListing] = []
        self.displayed_results = {"all": [], "new": []}
        self.search_in_progress = False
        self.auto_scan_job: str | None = None
        self.last_scan_keys: set[str] = set()
        self.has_completed_search = False
        self.fullscreen = False
        self.sort_state = {
            "all": {
                "column": self.settings.get("sort_all_column", "posted"),
                "descending": bool(self.settings.get("sort_all_descending", True)),
            },
            "new": {
                "column": self.settings.get("sort_new_column", "posted"),
                "descending": bool(self.settings.get("sort_new_descending", True)),
            },
        }

        self._build_style()
        self._build_layout()
        self.apply_theme()
        self.update_visible_columns()
        self.root.after(150, self._set_initial_pane_layout)
        if bool(self.settings.get("fullscreen", False)):
            self.root.after(200, self.toggle_fullscreen)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)

    def _build_style(self) -> None:
        theme = self._theme()
        base_size = self.text_size_var.get()
        row_height = self._row_height(base_size)
        compact_mode = self.density_var.get() == "Compact"
        header_size = base_size + (3 if compact_mode else 6)
        sub_size = max(8, base_size - (2 if compact_mode else 1))
        self.root.configure(bg=theme["bg_main"])
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=theme["bg_main"], foreground=theme["fg_main"], fieldbackground=theme["bg_input"], font=("Segoe UI", base_size))
        style.configure("TFrame", background=theme["bg_main"])
        style.configure("Card.TFrame", background=theme["bg_card"], relief="flat")
        style.configure("TLabel", background=theme["bg_main"], foreground=theme["fg_main"], font=("Segoe UI", base_size))
        style.configure("Header.TLabel", font=("Segoe UI Semibold", header_size), foreground=theme["accent_primary"], background=theme["bg_main"])
        style.configure("Sub.TLabel", foreground=theme["fg_muted"], background=theme["bg_main"], font=("Segoe UI", sub_size))
        style.configure("TCheckbutton", background=theme["bg_main"], foreground=theme["fg_main"], font=("Segoe UI", base_size))
        style.map("TCheckbutton", foreground=[("active", theme["accent_primary"])])
        style.configure("TButton", background=theme["accent_button"], foreground="#ffffff", padding=(10, 6), borderwidth=1, focusthickness=2, focuscolor=theme["accent_primary"], font=("Segoe UI Semibold", base_size))
        style.map(
            "TButton",
            background=[("active", theme["accent_secondary"])],
            foreground=[("active", "#ffffff")],
        )
        style.configure(
            "Treeview",
            background=theme["bg_tree"],
            fieldbackground=theme["bg_tree"],
            foreground=theme["fg_main"],
            rowheight=row_height,
            bordercolor=theme["accent_primary"],
            lightcolor=theme["accent_primary"],
            darkcolor=theme["bg_tree"],
            font=("Segoe UI", base_size),
        )
        style.configure("Treeview.Heading", background=theme["bg_header"], foreground=theme["accent_highlight"], relief="flat", font=("Segoe UI Semibold", base_size))
        style.map(
            "Treeview",
            background=[("selected", theme["row_selected"])],
            foreground=[("selected", "#ffffff")],
        )
        style.map("Treeview.Heading", background=[("active", theme["bg_header"])], foreground=[("active", theme["accent_secondary"])])
        style.configure("TNotebook", background=theme["bg_card"], tabmargins=(0, 0, 0, 0))
        style.configure("TNotebook.Tab", background=theme["bg_header"], foreground=theme["fg_muted"], padding=(12, 6), font=("Segoe UI Semibold", base_size))
        style.map(
            "TNotebook.Tab",
            background=[("selected", theme["bg_card"]), ("active", theme["bg_header"])],
            foreground=[("selected", theme["accent_primary"]), ("active", theme["accent_highlight"])],
        )
        combo_field = theme["bg_header"]
        combo_text = "#ffffff"
        style.configure("TEntry", fieldbackground=theme["bg_input"], foreground=theme["fg_main"], insertcolor=theme["accent_primary"], bordercolor=theme["accent_primary"], font=("Segoe UI", base_size))
        style.configure(
            "TCombobox",
            fieldbackground=combo_field,
            background=combo_field,
            foreground=combo_text,
            arrowcolor=theme["accent_highlight"],
            bordercolor=theme["accent_primary"],
            lightcolor=theme["accent_primary"],
            darkcolor=combo_field,
            selectbackground=theme["accent_primary"],
            selectforeground="#000000",
            font=("Segoe UI", base_size),
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", combo_field), ("disabled", theme["bg_input"])],
            background=[("readonly", combo_field), ("active", combo_field)],
            foreground=[("readonly", combo_text), ("disabled", theme["fg_muted"])],
            selectbackground=[("readonly", theme["accent_primary"])],
            selectforeground=[("readonly", "#000000")],
            arrowcolor=[("readonly", theme["accent_highlight"]), ("active", theme["accent_secondary"])],
        )
        style.configure("Vertical.TScrollbar", background=theme["bg_header"], troughcolor=theme["bg_main"], arrowcolor=theme["accent_primary"])
        style.configure("Horizontal.TScrollbar", background=theme["bg_header"], troughcolor=theme["bg_main"], arrowcolor=theme["accent_primary"])

    def _theme(self) -> dict[str, str]:
        return THEMES.get(self.theme_var.get(), THEMES[DEFAULT_THEME_NAME])

    def apply_theme(self) -> None:
        self._build_style()
        theme = self._theme()
        base_size = self.text_size_var.get()
        if hasattr(self, "terms_text"):
            self.terms_text.configure(
                bg=theme["bg_input"],
                fg=theme["fg_main"],
                insertbackground=theme["accent_primary"],
                highlightbackground=theme["accent_primary"],
                highlightcolor=theme["accent_secondary"],
                font=("Segoe UI", base_size),
            )
        if hasattr(self, "detail_text"):
            self.detail_text.configure(
                bg=theme["bg_input"],
                fg=theme["fg_main"],
                insertbackground=theme["accent_primary"],
                highlightbackground=theme["accent_primary"],
                highlightcolor=theme["accent_secondary"],
                font=("Consolas", base_size),
            )
        self._refresh_tree()
        self._save_settings()

    def on_theme_changed(self, _event: object | None = None) -> None:
        self.apply_theme()

    def change_text_size(self, delta: int) -> None:
        new_size = min(18, max(9, self.text_size_var.get() + delta))
        if new_size == self.text_size_var.get():
            return
        self.text_size_var.set(new_size)
        self.apply_theme()

    def on_density_changed(self, _event: object | None = None) -> None:
        self.apply_theme()

    def _build_layout(self) -> None:
        theme = self._theme()
        compact_mode = self.density_var.get() == "Compact"
        outer = ttk.Frame(self.root)
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(
            outer,
            bg=theme["bg_main"],
            highlightthickness=0,
            bd=0,
        )
        v_scroll = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=v_scroll.set)
        canvas.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")

        wrapper = ttk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=wrapper, anchor="nw")

        def _on_wrapper_configure(_event: object | None = None) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event: object) -> None:
            width = getattr(event, "width", None)
            if width:
                canvas.itemconfigure(canvas_window, width=width)

        def _on_mousewheel(event: object) -> None:
            delta = getattr(event, "delta", 0)
            if delta:
                canvas.yview_scroll(int(-1 * (delta / 120)), "units")

        wrapper.bind("<Configure>", _on_wrapper_configure)
        canvas.bind("<Configure>", _on_canvas_configure)
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        outer_inner = ttk.Frame(wrapper, padding=8 if compact_mode else 12)
        outer_inner.pack(fill="both", expand=True)

        header = ttk.Frame(outer_inner)
        header.pack(fill="x", pady=(0, 8 if compact_mode else 14))

        ttk.Label(header, text=APP_TITLE, style="Header.TLabel").pack(side="left", anchor="w")

        header_controls = ttk.Frame(header)
        header_controls.pack(side="right", anchor="e")

        ttk.Label(header_controls, text="Theme", style="Sub.TLabel").pack(side="left", padx=(0, 6))
        theme_picker = ttk.Combobox(
            header_controls,
            textvariable=self.theme_var,
            values=tuple(THEMES.keys()),
            width=14,
            state="readonly",
        )
        theme_picker.pack(side="left", padx=(0, 10))
        theme_picker.bind("<<ComboboxSelected>>", self.on_theme_changed)
        ttk.Label(header_controls, text="Text", style="Sub.TLabel").pack(side="left", padx=(0, 6))
        ttk.Button(header_controls, text="-", command=lambda: self.change_text_size(-1), width=3).pack(side="left")
        ttk.Button(header_controls, text="+", command=lambda: self.change_text_size(1), width=3).pack(side="left", padx=(6, 10))
        ttk.Label(header_controls, text="Density", style="Sub.TLabel").pack(side="left", padx=(0, 6))
        density_picker = ttk.Combobox(
            header_controls,
            textvariable=self.density_var,
            values=("Compact", "Comfortable"),
            width=11,
            state="readonly",
        )
        density_picker.pack(side="left", padx=(0, 10))
        density_picker.bind("<<ComboboxSelected>>", self.on_density_changed)
        ttk.Button(header_controls, text="Full Screen", command=self.toggle_fullscreen).pack(side="left")

        controls = ttk.Frame(outer_inner, style="Card.TFrame", padding=8 if compact_mode else 12)
        controls.pack(fill="x", pady=(0, 10 if compact_mode else 14))

        top_controls = ttk.Frame(controls, style="Card.TFrame")
        top_controls.pack(fill="x")

        self._add_entry(top_controls, "ZIP code", self.zip_var, 0, width=12)
        self._add_entry(top_controls, "City", self.city_var, 1, width=18)
        self._add_combo(top_controls, "State", self.state_var, STATE_OPTIONS, 2, width=6)
        self._add_entry(top_controls, f"Distance (max {MAX_DISTANCE_MILES})", self.distance_var, 3, width=12)
        self._add_entry(top_controls, "Posted within hours", self.hours_old_var, 4, width=14)
        self._add_entry(top_controls, "Results per term", self.results_var, 5, width=12)
        self._add_entry(top_controls, "Pay min", self.pay_min_var, 6, width=12)
        self._add_entry(top_controls, "Pay max", self.pay_max_var, 7, width=12)
        ttk.Checkbutton(top_controls, text="Remote only", variable=self.remote_only_var).grid(
            row=0, column=8, padx=(12, 0), sticky="w"
        )
        ttk.Button(top_controls, text="Scan Jobs", command=self.start_search).grid(row=0, column=9, padx=(18, 0))
        ttk.Button(top_controls, text="Export CSV", command=self.export_results).grid(row=0, column=10, padx=(8, 0))

        auto_scan_frame = ttk.Frame(controls, style="Card.TFrame")
        auto_scan_frame.pack(fill="x", pady=(10, 0))
        ttk.Checkbutton(
            auto_scan_frame,
            text="Auto-scan every",
            variable=self.auto_scan_var,
            command=self.toggle_auto_scan,
        ).pack(side="left")
        ttk.Entry(auto_scan_frame, textvariable=self.auto_scan_minutes_var, width=6).pack(side="left", padx=(8, 6))
        ttk.Label(auto_scan_frame, text="minutes", style="Sub.TLabel").pack(side="left")
        ttk.Checkbutton(auto_scan_frame, text="Desktop alert", variable=self.desktop_alert_var).pack(side="left", padx=(18, 0))
        ttk.Checkbutton(auto_scan_frame, text="Flash alert", variable=self.flash_alert_var).pack(side="left", padx=(10, 0))
        ttk.Checkbutton(auto_scan_frame, text="Sound alert", variable=self.sound_alert_var).pack(side="left", padx=(10, 0))
        ttk.Button(auto_scan_frame, text="Test sound", command=self._play_startup_mp3).pack(side="left", padx=(10, 0))

        search_sources_frame = ttk.Frame(controls, style="Card.TFrame")
        search_sources_frame.pack(fill="x", pady=(10, 0))
        search_sources_frame.columnconfigure(0, weight=3)
        search_sources_frame.columnconfigure(1, weight=4)

        terms_frame = ttk.Frame(search_sources_frame, style="Card.TFrame")
        terms_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        ttk.Label(terms_frame, text="Search titles (OR logic; one per line or use OR). Terms must appear in the job title.", style="Sub.TLabel").pack(anchor="w")

        self.terms_text = tk.Text(
            terms_frame,
            height=4,
            bg=theme["bg_input"],
            fg=theme["fg_main"],
            insertbackground=theme["accent_primary"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=theme["accent_primary"],
            highlightcolor=theme["accent_secondary"],
            padx=10,
            pady=8,
            font=("Segoe UI", self.text_size_var.get()),
        )
        self.terms_text.pack(fill="x", pady=(6, 0))

        sites_frame = ttk.Frame(search_sources_frame, style="Card.TFrame")
        sites_frame.grid(row=0, column=1, sticky="nsew")
        ttk.Label(sites_frame, text="Job boards", style="Sub.TLabel").pack(anchor="w")
        checks = ttk.Frame(sites_frame, style="Card.TFrame")
        checks.pack(anchor="w", pady=(6, 0))
        for index, site in enumerate(SITE_OPTIONS):
            ttk.Checkbutton(
                checks,
                text=SITE_DISPLAY_NAMES.get(site, site.replace("_", " ").title()),
                variable=self.site_vars[site],
                command=self._save_settings,
            ).grid(
                row=index // 4, column=index % 4, padx=(0, 10), pady=(0, 4), sticky="w"
            )

        custom_source_frame = ttk.Frame(controls, style="Card.TFrame")
        custom_source_frame.pack(fill="x", pady=(10, 0))
        ttk.Label(custom_source_frame, text="Optional custom careers/search URL", style="Sub.TLabel").pack(anchor="w")
        ttk.Entry(custom_source_frame, textvariable=self.custom_url_var).pack(fill="x", pady=(6, 0))

        columns_frame = ttk.Frame(controls, style="Card.TFrame")
        columns_frame.pack(fill="x", pady=(10, 0))
        ttk.Label(columns_frame, text="Visible result columns", style="Sub.TLabel").pack(anchor="w")
        column_checks = ttk.Frame(columns_frame, style="Card.TFrame")
        column_checks.pack(anchor="w", pady=(6, 0))
        for index, column in enumerate(RESULT_COLUMNS):
            ttk.Checkbutton(
                column_checks,
                text=RESULT_COLUMN_LABELS[column],
                variable=self.column_vars[column],
                command=self.update_visible_columns,
            ).grid(row=0, column=index, padx=(0, 14), sticky="w")

        meta = ttk.Frame(outer_inner)
        meta.pack(fill="x", pady=(0, 6 if compact_mode else 10))
        ttk.Label(meta, textvariable=self.status_var).pack(side="left")
        ttk.Label(meta, textvariable=self.location_var).pack(side="left", padx=(18, 0))
        ttk.Label(meta, textvariable=self.summary_var).pack(side="right")

        content = ttk.Panedwindow(outer_inner, orient="horizontal")
        content.pack(fill="both", expand=True)
        self.content_pane = content
        self.content_pane.bind("<ButtonRelease-1>", self._on_pane_changed)

        table_card = ttk.Frame(content, style="Card.TFrame", padding=12)
        detail_card = ttk.Frame(content, style="Card.TFrame", padding=12)
        content.add(table_card, weight=3)
        content.add(detail_card, weight=2)
        self.table_card = table_card
        self.detail_card = detail_card

        self.notebook = ttk.Notebook(table_card)
        self.notebook.pack(fill="both", expand=True)

        all_jobs_tab = ttk.Frame(self.notebook, style="Card.TFrame")
        new_jobs_tab = ttk.Frame(self.notebook, style="Card.TFrame")
        self.notebook.add(all_jobs_tab, text="All Jobs")
        self.notebook.add(new_jobs_tab, text="New Jobs")
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        self.tree = self._build_results_tree(all_jobs_tab)
        self.new_tree = self._build_results_tree(new_jobs_tab)

        action_bar = ttk.Frame(table_card, style="Card.TFrame")
        action_bar.pack(fill="x", pady=(8, 0))
        ttk.Button(action_bar, text="Open Listing", command=self.open_selected_job).pack(side="left")
        ttk.Button(action_bar, text="Copy URL", command=self.copy_selected_url).pack(side="left", padx=(8, 0))
        ttk.Button(action_bar, text="Clear Results", command=self.clear_results).pack(side="left", padx=(8, 0))

        ttk.Label(detail_card, text="Listing details", style="Header.TLabel").pack(anchor="w")
        ttk.Label(
            detail_card,
            text="Select a result to inspect the description, salary info, and links.",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(4, 10))

        self.detail_text = tk.Text(
            detail_card,
            wrap="word",
            bg=theme["bg_input"],
            fg=theme["fg_main"],
            insertbackground=theme["accent_primary"],
            relief="flat",
            highlightthickness=1,
            highlightbackground=theme["accent_primary"],
            highlightcolor=theme["accent_secondary"],
            padx=12,
            pady=10,
            font=("Consolas", self.text_size_var.get()),
        )
        self.detail_text.pack(fill="both", expand=True)
        self.detail_text.insert("1.0", "Run a scan to load job listings.")
        self.detail_text.configure(state="disabled")
        self._bind_setting_vars()

    def _add_entry(self, parent: ttk.Frame, label: str, variable: tk.Variable, column: int, width: int) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.grid(row=0, column=column, padx=(0, 12), sticky="w")
        ttk.Label(frame, text=label, style="Sub.TLabel").pack(anchor="w")
        ttk.Entry(frame, textvariable=variable, width=width).pack(anchor="w", pady=(4, 0))

    def _build_results_tree(self, parent: ttk.Frame) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=RESULT_COLUMNS, show="headings")
        for column in RESULT_COLUMNS:
            tree.heading(
                column,
                text=RESULT_COLUMN_LABELS[column],
                command=lambda col=column, target_tree=tree: self.sort_by_column(target_tree, col),
            )
            tree.column(column, width=RESULT_COLUMN_WIDTHS[column], anchor="w")
        x_scroll = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        y_scroll = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)
        tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        tree.bind("<<TreeviewSelect>>", self.on_select)
        tree.bind("<Double-1>", self.open_selected_job)
        return tree

    def _add_combo(
        self,
        parent: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        values: tuple[str, ...],
        column: int,
        width: int,
        on_select: object | None = None,
    ) -> None:
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.grid(row=0, column=column, padx=(0, 12), sticky="w")
        ttk.Label(frame, text=label, style="Sub.TLabel").pack(anchor="w")
        combo = ttk.Combobox(frame, textvariable=variable, values=values, width=width, state="readonly")
        combo.pack(anchor="w", pady=(4, 0))
        if on_select is not None:
            combo.bind("<<ComboboxSelected>>", on_select)

    def start_search(self) -> None:
        if self.search_in_progress:
            return
        terms = self._get_search_terms()
        if not terms:
            messagebox.showerror("Missing Search Terms", "Enter at least one job title to search.")
            return

        zip_code = self.zip_var.get().strip()
        city = self.city_var.get().strip()
        state = self.state_var.get().strip().upper()
        if not zip_code and not (city and state):
            messagebox.showerror("Missing Location", "Enter either a ZIP code or both a city and state.")
            return

        sites = tuple(site for site, selected in self.site_vars.items() if selected.get())
        custom_url = self.custom_url_var.get().strip()
        if not sites and not custom_url:
            messagebox.showerror("Missing Job Boards", "Select at least one job board or enter a custom URL.")
            return

        self.search_in_progress = True
        self.status_var.set("Scanning job boards...")
        self.location_var.set("Location: resolving search area...")

        distance_miles = min(max(self._int_or_default(self.distance_var.get(), DEFAULT_DISTANCE_MILES), 1), MAX_DISTANCE_MILES)
        posted_hours = max(self._int_or_default(self.hours_old_var.get(), DEFAULT_HOURS_OLD), 1)
        results_per_term = max(self._int_or_default(self.results_var.get(), DEFAULT_RESULTS_PER_TERM), 1)
        pay_min = max(self._int_or_default(self.pay_min_var.get(), DEFAULT_PAY_MIN), 0)
        pay_max = max(self._int_or_default(self.pay_max_var.get(), DEFAULT_PAY_MAX), 0)
        if pay_max and pay_max < pay_min:
            pay_min, pay_max = pay_max, pay_min
        self.distance_var.set("" if not self.distance_var.get().strip() else str(distance_miles))
        self.hours_old_var.set("" if not self.hours_old_var.get().strip() else str(posted_hours))
        self.results_var.set("" if not self.results_var.get().strip() else str(results_per_term))
        self.pay_min_var.set("" if not self.pay_min_var.get().strip() and pay_min == 0 else str(pay_min))
        self.pay_max_var.set("" if not self.pay_max_var.get().strip() and pay_max == 0 else str(pay_max))

        config = JobSearchConfig(
            zip_code=zip_code,
            city=city,
            state=state,
            search_terms=terms,
            distance_miles=distance_miles,
            hours_old=posted_hours,
            results_per_term=results_per_term,
            sites=sites,
            remote_only=self.remote_only_var.get(),
            pay_min=pay_min,
            pay_max=pay_max,
            custom_url=custom_url,
        )
        threading.Thread(target=self._run_search, args=(config,), daemon=True).start()

    def _run_search(self, config: JobSearchConfig) -> None:
        try:
            location, results = search_jobs(config, progress_callback=self._push_status)
            self.root.after(0, lambda: self._finish_search(location.display_name, results, None))
        except Exception as exc:  # pragma: no cover - UI path
            self.root.after(0, lambda: self._finish_search("", [], exc))

    def _push_status(self, message: str) -> None:
        self.root.after(0, lambda: self.status_var.set(message))

    def _finish_search(self, location_name: str, results: list[JobListing], error: Exception | None) -> None:
        self.search_in_progress = False
        if error is not None:
            self.status_var.set("Search failed")
            self.location_var.set("Location: unavailable")
            messagebox.showerror("Job Scan Failed", str(error))
            self._schedule_auto_scan()
            return

        is_first_successful_scan = not self.has_completed_search
        new_listings = self._collect_new_listings(results)
        self.results = results
        self.new_results = new_listings
        self.has_completed_search = True
        self._refresh_tree()
        self.status_var.set("Search complete")
        self.location_var.set(f"Location: {location_name}")
        self.summary_var.set(f"Results: {len(results)}")

        if results:
            first_id = self.tree.get_children()[0]
            self.tree.selection_set(first_id)
            self.tree.focus(first_id)
            self.notebook.select(0)
            self.on_select()
        else:
            self._set_detail_text("No matching jobs found for the selected criteria.")
        if self.new_results:
            self.notebook.tab(1, text=f"New Jobs ({len(self.new_results)})")
        else:
            self.notebook.tab(1, text="New Jobs")
        if new_listings and not is_first_successful_scan:
            self._notify_new_jobs(new_listings)
        self._schedule_auto_scan()

    def _refresh_tree(self) -> None:
        self._update_sort_headings(self.tree, "all")
        self._update_sort_headings(self.new_tree, "new")
        self._populate_tree(self.tree, self.results, "all")
        self._populate_tree(self.new_tree, self.new_results, "new")

    def _update_sort_headings(self, tree: ttk.Treeview, state_key: str) -> None:
        sorted_column = self.sort_state[state_key]["column"]
        descending = self.sort_state[state_key]["descending"]
        arrow = " [v]" if descending else " [^]"
        for column, label in RESULT_COLUMN_LABELS.items():
            suffix = arrow if column == sorted_column else ""
            tree.heading(column, text=f"{label}{suffix}")

    def _populate_tree(self, tree: ttk.Treeview, listings: list[JobListing], state_key: str) -> None:
        tree.delete(*tree.get_children())
        sorted_listings = sorted(
            listings,
            key=lambda listing: self._sort_value(listing, self.sort_state[state_key]["column"]),
            reverse=self.sort_state[state_key]["descending"],
        )
        self.displayed_results[state_key] = sorted_listings
        for index, listing in enumerate(sorted_listings):
            tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    self._wrap_cell(listing.title or "Untitled", 28),
                    self._wrap_cell(listing.company or "Unknown company", 22),
                    self._wrap_cell(listing.location or "Unknown location", 22),
                    self._wrap_cell(listing.site or "Unknown", 12),
                    self._wrap_cell(self._format_salary(listing), 16),
                    self._wrap_cell(self._display_posted(listing.date_posted), 16),
                    self._wrap_cell(listing.search_term, 16),
                ),
            )

    def on_select(self, _event: object | None = None) -> None:
        listing = self._selected_listing()
        if listing is None:
            return

        salary = self._format_salary(listing)
        detail_lines = [
            f"Title: {listing.title or 'Untitled'}",
            f"Company: {listing.company or 'Unknown company'}",
            f"Location: {listing.location or 'Unknown location'}",
            f"Site: {listing.site or 'Unknown'}",
            f"Matched search: {listing.search_term}",
            f"Posted: {self._display_posted(listing.date_posted)}",
            f"Remote: {listing.is_remote or 'Unknown'}",
            f"Job type: {listing.job_type or 'Unknown'}",
            f"Salary: {salary}",
            f"Listing URL: {listing.job_url or 'Unavailable'}",
            "",
            listing.description or "No description provided by the source.",
        ]
        self._set_detail_text("\n".join(detail_lines))

    def open_selected_job(self, _event: object | None = None) -> None:
        listing = self._selected_listing()
        if listing is None or not listing.job_url:
            messagebox.showinfo("Open Listing", "Select a job listing that includes a URL.")
            return
        webbrowser.open(listing.job_url)

    def copy_selected_url(self) -> None:
        listing = self._selected_listing()
        if listing is None or not listing.job_url:
            messagebox.showinfo("Copy URL", "Select a job listing that includes a URL.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(listing.job_url)
        self.status_var.set("Copied listing URL")

    def export_results(self) -> None:
        if not self.results:
            messagebox.showinfo("Export CSV", "Run a search before exporting results.")
            return
        output_path = filedialog.asksaveasfilename(
            title="Export job scan results",
            initialfile=EXPORT_FILENAME,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not output_path:
            return

        fieldnames = list(self.results[0].to_dict().keys())
        with Path(output_path).open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for listing in self.results:
                writer.writerow(listing.to_dict())
        self.status_var.set(f"Exported {len(self.results)} results")

    def clear_results(self) -> None:
        self.results = []
        self.new_results = []
        self.displayed_results = {"all": [], "new": []}
        self.last_scan_keys = set()
        self.has_completed_search = False
        self.tree.delete(*self.tree.get_children())
        self.new_tree.delete(*self.new_tree.get_children())
        self.summary_var.set("Results: 0")
        self.location_var.set("Location: not searched yet")
        self.notebook.tab(1, text="New Jobs")
        self._set_detail_text("Run a scan to load job listings.")

    def toggle_auto_scan(self) -> None:
        if self.auto_scan_var.get():
            minutes = max(self._int_or_default(self.auto_scan_minutes_var.get(), DEFAULT_AUTO_SCAN_MINUTES), 1)
            self.auto_scan_minutes_var.set(str(minutes))
            self.status_var.set(f"Auto-scan enabled: every {minutes} minute(s)")
            self._schedule_auto_scan()
        else:
            self._cancel_auto_scan()
            self.status_var.set("Auto-scan disabled")

    def _schedule_auto_scan(self) -> None:
        self._cancel_auto_scan()
        if not self.auto_scan_var.get():
            return
        minutes = max(self._int_or_default(self.auto_scan_minutes_var.get(), DEFAULT_AUTO_SCAN_MINUTES), 1)
        self.auto_scan_minutes_var.set(str(minutes))
        delay_ms = minutes * 60 * 1000
        self.auto_scan_job = self.root.after(delay_ms, self._run_auto_scan)

    def _run_auto_scan(self) -> None:
        self.auto_scan_job = None
        if not self.auto_scan_var.get():
            return
        self.status_var.set("Auto-scan running...")
        self.start_search()

    def _cancel_auto_scan(self) -> None:
        if self.auto_scan_job is not None:
            self.root.after_cancel(self.auto_scan_job)
            self.auto_scan_job = None

    def on_close(self) -> None:
        self._cancel_auto_scan()
        self._stop_startup_mp3()
        self._save_settings()
        self.root.destroy()

    def _collect_new_listings(self, results: list[JobListing]) -> list[JobListing]:
        current_keys = {self._listing_key(listing) for listing in results}
        new_listings = [listing for listing in results if self._listing_key(listing) not in self.last_scan_keys]
        self.last_scan_keys = current_keys
        return new_listings

    def _listing_key(self, listing: JobListing) -> str:
        if listing.job_url:
            return listing.job_url.strip().lower()
        return "|".join(
            part.strip().lower()
            for part in (listing.title, listing.company, listing.location, listing.search_term, listing.site)
        )

    def _notify_new_jobs(self, listings: list[JobListing]) -> None:
        count = len(listings)
        preview = ", ".join(listing.title or "Untitled" for listing in listings[:3])
        extra = f" (+{count - 3} more)" if count > 3 else ""
        message = f"{count} new matching job{'s' if count != 1 else ''}: {preview}{extra}"
        self.status_var.set(message)
        if self.desktop_alert_var.get():
            threading.Thread(target=self._show_windows_notification, args=(message,), daemon=True).start()
        if self.sound_alert_var.get():
            self.root.after(0, self._play_new_job_sound)
        if self.flash_alert_var.get():
            self.root.after(0, self._flash_window)

    def _show_windows_notification(self, message: str) -> None:
        script = (
            "Add-Type -AssemblyName System.Windows.Forms; "
            "$notify = New-Object System.Windows.Forms.NotifyIcon; "
            "$notify.Icon = [System.Drawing.SystemIcons]::Information; "
            f"$notify.BalloonTipTitle = '{self._ps_escape(NOTIFICATION_TITLE)}'; "
            f"$notify.BalloonTipText = '{self._ps_escape(message)}'; "
            "$notify.Visible = $true; "
            "$notify.ShowBalloonTip(5000); "
            "Start-Sleep -Seconds 6; "
            "$notify.Dispose()"
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                check=False,
                capture_output=True,
                text=True,
            )
        except OSError:
            pass

    def _play_alert_sound(self) -> None:
        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            self.root.bell()
        except RuntimeError:
            pass

    def _play_new_job_sound(self) -> None:
        self._play_startup_mp3()
        self.root.after(0, self._play_alert_sound)

    def _play_startup_mp3(self) -> None:
        mp3_path = Path(__file__).with_name(STARTUP_MP3_FILENAME)
        if not mp3_path.exists():
            return
        try:
            alias = "jobscanner_startup"
            safe_path = str(mp3_path).replace('"', '""')
            ctypes.windll.winmm.mciSendStringW(f'close {alias}', None, 0, None)
            ctypes.windll.winmm.mciSendStringW(f'open "{safe_path}" type mpegvideo alias {alias}', None, 0, None)
            ctypes.windll.winmm.mciSendStringW(f'play {alias}', None, 0, None)
        except Exception:
            pass

    def _stop_startup_mp3(self) -> None:
        try:
            ctypes.windll.winmm.mciSendStringW("close jobscanner_startup", None, 0, None)
        except Exception:
            pass

    def _flash_window(self) -> None:
        try:
            hwnd = self.root.winfo_id()
        except Exception:
            self.root.bell()
            return
        try:
            class FLASHWINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_uint),
                    ("hwnd", ctypes.c_void_p),
                    ("dwFlags", ctypes.c_uint),
                    ("uCount", ctypes.c_uint),
                    ("dwTimeout", ctypes.c_uint),
                ]

            info = FLASHWINFO(
                ctypes.sizeof(FLASHWINFO),
                hwnd,
                0x00000003,
                5,
                0,
            )
            ctypes.windll.user32.FlashWindowEx(ctypes.byref(info))
        except Exception:
            self.root.bell()

    def _ps_escape(self, value: str) -> str:
        return value.replace("'", "''")

    def _get_search_terms(self) -> tuple[str, ...]:
        raw = self.terms_text.get("1.0", "end")
        terms: list[str] = []
        for line in raw.splitlines():
            for part in re.split(r"\s+\bOR\b\s+|,|;", line, flags=re.IGNORECASE):
                term = part.strip()
                if term and term not in terms:
                    terms.append(term)
        return tuple(terms)

    def _selected_listing(self) -> JobListing | None:
        active_tree, listings = self._active_tree_and_results()
        selection = active_tree.selection()
        if not selection:
            return None
        index = int(selection[0])
        if index >= len(listings):
            return None
        return listings[index]

    def _active_tree_and_results(self) -> tuple[ttk.Treeview, list[JobListing]]:
        current_tab = self.notebook.index(self.notebook.select())
        if current_tab == 1:
            return self.new_tree, self.displayed_results["new"]
        return self.tree, self.displayed_results["all"]

    def on_tab_changed(self, _event: object | None = None) -> None:
        active_tree, listings = self._active_tree_and_results()
        if not listings:
            self._set_detail_text("No jobs available in this tab yet.")
            return
        children = active_tree.get_children()
        if not children:
            self._set_detail_text("No jobs available in this tab yet.")
            return
        first_id = children[0]
        active_tree.selection_set(first_id)
        active_tree.focus(first_id)
        self.on_select()

    def sort_by_column(self, tree: ttk.Treeview, column: str) -> None:
        state_key = "new" if tree is self.new_tree else "all"
        current_column = self.sort_state[state_key]["column"]
        current_descending = self.sort_state[state_key]["descending"]
        if current_column == column:
            self.sort_state[state_key]["descending"] = not current_descending
        else:
            self.sort_state[state_key] = {"column": column, "descending": column == "posted"}

        self._refresh_tree()
        active_tree, listings = self._active_tree_and_results()
        if tree is active_tree and listings:
            children = tree.get_children()
            if children:
                first_id = children[0]
                tree.selection_set(first_id)
                tree.focus(first_id)
                self.on_select()
        self._save_settings()

    def _sort_value(self, listing: JobListing, column: str) -> tuple[int, object]:
        if column == "posted":
            return self._posted_sort_value(listing.date_posted)
        if column == "title":
            return (0, (listing.title or "").casefold())
        if column == "company":
            return (0, (listing.company or "").casefold())
        if column == "location":
            return (0, (listing.location or "").casefold())
        if column == "site":
            return (0, (listing.site or "").casefold())
        if column == "pay":
            return self._pay_sort_value(listing)
        if column == "term":
            return (0, (listing.search_term or "").casefold())
        return (0, "")

    def _posted_sort_value(self, value: str) -> tuple[int, object]:
        if not value:
            return (1, datetime.min)
        cleaned = value.strip()
        for candidate in (cleaned, cleaned.replace("Z", "+00:00")):
            try:
                return (0, datetime.fromisoformat(candidate))
            except ValueError:
                continue
        return (0, cleaned.casefold())

    def _pay_sort_value(self, listing: JobListing) -> tuple[int, int, int, str]:
        minimum = self._numeric_amount(listing.salary_min)
        maximum = self._numeric_amount(listing.salary_max)
        low = minimum if minimum is not None else (maximum if maximum is not None else -1)
        high = maximum if maximum is not None else (minimum if minimum is not None else -1)
        interval = (listing.interval or "").casefold()
        return (0 if low >= 0 else 1, low, high, interval)

    def _numeric_amount(self, value: str) -> int | None:
        digits = "".join(ch for ch in value if ch.isdigit())
        if not digits:
            return None
        try:
            return int(digits)
        except ValueError:
            return None

    def _wrap_cell(self, value: str, width: int) -> str:
        clean = " ".join(value.split())
        if not clean:
            return ""
        return textwrap.fill(clean, width=width, break_long_words=False)

    def _row_height(self, base_size: int) -> int:
        if self.density_var.get() == "Compact":
            return max(28, base_size * 3 + 6)
        return max(34, base_size * 4 + 10)

    def _display_posted(self, value: str) -> str:
        parsed = self._parse_display_datetime(value)
        if parsed is None:
            return value or "Unknown"
        now = datetime.now(parsed.tzinfo) if parsed.tzinfo else datetime.now()
        delta = now - parsed
        if delta.total_seconds() < 0:
            delta = datetime.now() - parsed.replace(tzinfo=None) if parsed.tzinfo else delta
        if 0 <= delta.total_seconds() < 86400:
            hours = max(1, int(delta.total_seconds() // 3600))
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        return parsed.date().isoformat()

    def _parse_display_datetime(self, value: str) -> datetime | None:
        clean = value.strip()
        if not clean:
            return None
        for candidate in (clean, clean.replace("Z", "+00:00"), clean.replace(" UTC", "+00:00")):
            try:
                return datetime.fromisoformat(candidate)
            except ValueError:
                continue
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(clean, fmt)
            except ValueError:
                continue
        return None

    def update_visible_columns(self) -> None:
        visible = [column for column in RESULT_COLUMNS if self.column_vars[column].get()]
        if not visible:
            self.column_vars["title"].set(True)
            visible = ["title"]
        self.tree.configure(displaycolumns=visible)
        self.new_tree.configure(displaycolumns=visible)
        self._fit_results_pane_to_columns(visible)
        self._save_settings()

    def _int_or_default(self, value: str, default: int) -> int:
        text = value.strip()
        if not text:
            return default
        return int(text)

    def _set_initial_window_size(self) -> None:
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        width = max(980, int(screen_width * 0.85))
        height = max(680, int(screen_height * 0.85))
        x_pos = max(0, (screen_width - width) // 2)
        y_pos = max(0, (screen_height - height) // 2)
        self.root.geometry(f"{width}x{height}+{x_pos}+{y_pos}")

    def toggle_fullscreen(self, _event: object | None = None) -> None:
        self.fullscreen = not self.fullscreen
        self.root.attributes("-fullscreen", self.fullscreen)
        self.root.after(100, self._set_initial_pane_layout)
        self._save_settings()

    def exit_fullscreen(self, _event: object | None = None) -> None:
        if self.fullscreen:
            self.fullscreen = False
            self.root.attributes("-fullscreen", False)
            self.root.after(100, self._set_initial_pane_layout)
            self._save_settings()

    def _set_initial_pane_layout(self) -> None:
        try:
            total_width = self.content_pane.winfo_width()
            if total_width <= 1:
                return
            minimum_detail_width = 320
            saved_ratio = self.settings.get("pane_ratio")
            if isinstance(saved_ratio, (int, float)) and 0.45 <= float(saved_ratio) <= 0.9:
                desired_table_width = int(total_width * float(saved_ratio))
            else:
                default_ratio = 0.82 if len([c for c in RESULT_COLUMNS if self.column_vars[c].get()]) == len(RESULT_COLUMNS) else 0.74
                desired_table_width = max(int(total_width * default_ratio), self._visible_column_width() + 40)
            table_width = min(desired_table_width, max(total_width - minimum_detail_width, int(total_width * 0.60)))
            self.content_pane.sashpos(0, table_width)
        except tk.TclError:
            pass

    def _visible_column_width(self) -> int:
        visible = [column for column in RESULT_COLUMNS if self.column_vars[column].get()]
        return sum(RESULT_COLUMN_WIDTHS[column] for column in visible)

    def _fit_results_pane_to_columns(self, visible: list[str]) -> None:
        self.root.after(50, self._set_initial_pane_layout)

    def _on_pane_changed(self, _event: object | None = None) -> None:
        self._save_settings()

    def _bind_setting_vars(self) -> None:
        vars_to_watch = (
            self.zip_var,
            self.city_var,
            self.state_var,
            self.distance_var,
            self.hours_old_var,
            self.results_var,
            self.pay_min_var,
            self.pay_max_var,
            self.custom_url_var,
            self.remote_only_var,
            self.auto_scan_var,
            self.auto_scan_minutes_var,
            self.desktop_alert_var,
            self.flash_alert_var,
            self.sound_alert_var,
            self.theme_var,
            self.density_var,
        )
        for variable in vars_to_watch:
            variable.trace_add("write", self._on_setting_var_changed)

    def _on_setting_var_changed(self, *_args) -> None:
        self._save_settings()

    def _load_settings(self) -> dict:
        if not self.settings_path.exists():
            return {}
        try:
            return json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_settings(self) -> None:
        try:
            pane_ratio = None
            if hasattr(self, "content_pane"):
                total_width = self.content_pane.winfo_width()
                if total_width and total_width > 1:
                    pane_ratio = self.content_pane.sashpos(0) / total_width

            payload = {
                "theme_name": self.theme_var.get(),
                "text_size": self.text_size_var.get(),
                "density": self.density_var.get(),
                "zip_code": self.zip_var.get().strip(),
                "city": self.city_var.get().strip(),
                "state": self.state_var.get().strip(),
                "distance": self.distance_var.get().strip(),
                "hours_old": self.hours_old_var.get().strip(),
                "results_per_term": self.results_var.get().strip(),
                "pay_min": self.pay_min_var.get().strip(),
                "pay_max": self.pay_max_var.get().strip(),
                "custom_url": self.custom_url_var.get().strip(),
                "remote_only": self.remote_only_var.get(),
                "auto_scan": self.auto_scan_var.get(),
                "auto_scan_minutes": self.auto_scan_minutes_var.get().strip(),
                "desktop_alert": self.desktop_alert_var.get(),
                "flash_alert": self.flash_alert_var.get(),
                "sound_alert": self.sound_alert_var.get(),
                "sites": [site for site, selected in self.site_vars.items() if selected.get()],
                "visible_columns": [column for column in RESULT_COLUMNS if self.column_vars[column].get()],
                "sort_all_column": self.sort_state["all"]["column"],
                "sort_all_descending": self.sort_state["all"]["descending"],
                "sort_new_column": self.sort_state["new"]["column"],
                "sort_new_descending": self.sort_state["new"]["descending"],
                "pane_ratio": pane_ratio,
                "fullscreen": self.fullscreen,
            }
            self.settings = payload
            self.settings_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _set_detail_text(self, text: str) -> None:
        self.detail_text.configure(state="normal")
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", text)
        self.detail_text.configure(state="disabled")

    def _format_salary(self, listing: JobListing) -> str:
        minimum = listing.salary_min
        maximum = listing.salary_max
        if minimum and maximum:
            interval = f" per {listing.interval}" if listing.interval else ""
            return f"{minimum} - {maximum}{interval}"
        if minimum:
            return minimum
        if maximum:
            return maximum
        return "Not listed"


def main() -> None:
    root = tk.Tk()
    app = JobScannerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
