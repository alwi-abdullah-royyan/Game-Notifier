from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .. import analysis
from ..config import AppConfig
from ..paths import Paths, get_paths
from ._builder import _build_ui, _set_tree, _set_summary, _LogsView


def run_standalone(
    tab: str = "logs",
    paths: Paths | None = None,
    config: AppConfig | None = None,
) -> None:
    paths = paths or get_paths()
    root = tk.Tk()
    elements = _build_ui(root)
    root.title(config.app_name if config else "Game Notifier")

    view = _LogsView(paths, config, elements)

    def refresh_pattern() -> None:
        try:
            rows, summary = analysis.analyze_upload_frequencies_data(
                paths.backup_dir,
                db_file=paths.db_file,
            )
        except Exception as e:
            rows, summary = [], {
                "median_daily": 0,
                "total_uploads_today": 0,
                "remaining_estimate": 0,
                "total_upload_events": 0,
                "total_games_logged": 0,
                "oldest_timestamp": None,
                "message": f"Failed to analyze upload pattern: {e}",
            }
        _set_tree(elements.pattern_tree, rows)
        _set_summary(
            elements.summary_message,
            elements.summary_median,
            elements.summary_total,
            elements.summary_remaining,
            elements.summary_events,
            elements.summary_games,
            summary,
        )

    ttk.Button(elements.logs_toolbar, text="Refresh", command=view.refresh_logs).pack(side="right", padx=8, pady=6)
    ttk.Button(elements.logs_toolbar, text="Open Thread", command=view.open_selected_thread).pack(side="right", padx=8, pady=6)
    ttk.Button(elements.logs_toolbar, text="Clear", command=view.clear_filter).pack(side="right", padx=8, pady=6)
    ttk.Button(elements.logs_toolbar, text="Filter", command=view.apply_filter).pack(side="right", padx=8, pady=6)
    ttk.Button(elements.pattern_toolbar, text="Refresh", command=refresh_pattern).pack(side="right", padx=8, pady=6)

    elements.logs_filter_entry.bind("<Return>", lambda _evt: view.apply_filter())
    elements.logs_tree.bind("<Double-1>", lambda _evt: view.open_selected_thread())
    elements.notebook.bind(
        "<<NotebookTabChanged>>",
        lambda _evt: (
            refresh_pattern()
            if elements.notebook.nametowidget(elements.notebook.select())
            == elements.tab_pattern
            else None
        ),
    )

    if tab == "pattern":
        elements.notebook.select(elements.tab_pattern)
        refresh_pattern()
    else:
        elements.notebook.select(elements.tab_logs)
        view.refresh_logs()

    root.mainloop()
