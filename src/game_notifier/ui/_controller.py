from __future__ import annotations

import queue
import threading
import time
import tkinter as tk
from tkinter import ttk
from pathlib import Path

from .. import analysis
from ..config import AppConfig
from ..paths import Paths, get_paths
from ._builder import _build_ui, _set_tree, _set_summary, _LogsView


class _UiController:
    def __init__(self, paths: Paths, config: AppConfig | None = None) -> None:
        self._paths = paths
        self._config = config
        self._queue: queue.Queue[tuple[str, str | None]] = queue.Queue()
        self._ready = threading.Event()
        self._pattern_cache: dict = {
            "rows": [],
            "summary": {},
            "log_mtime": None,
            "data_mtime": None,
            "computed_at": 0.0,
        }
        self._pattern_inflight = False
        self._pattern_cache_ttl = 60
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait()

    def _run(self) -> None:
        root = tk.Tk()
        elements = _build_ui(root)
        root.title(self._config.app_name if self._config else "Game Notifier")
        root.withdraw()
        root.protocol("WM_DELETE_WINDOW", root.withdraw)

        view = _LogsView(self._paths, self._config, elements, limit=100)

        def refresh_pattern() -> None:
            def get_mtime(path: Path) -> float | None:
                return path.stat().st_mtime if path.exists() else None

            db_mtime = get_mtime(self._paths.db_file)
            now = time.time()

            cache = self._pattern_cache
            if (
                cache["rows"]
                and cache["log_mtime"] == db_mtime
                and cache["data_mtime"] == db_mtime
                and (now - cache["computed_at"]) < self._pattern_cache_ttl
            ):
                _set_tree(elements.pattern_tree, cache["rows"])
                _set_summary(
                    elements.summary_message,
                    elements.summary_median,
                    elements.summary_total,
                    elements.summary_remaining,
                    elements.summary_events,
                    elements.summary_games,
                    cache["summary"],
                )
                return

            if self._pattern_inflight:
                return

            loading_summary = {
                "median_daily": 0,
                "total_uploads_today": 0,
                "remaining_estimate": 0,
                "total_upload_events": 0,
                "total_games_logged": 0,
                "oldest_timestamp": None,
                "message": "Loading upload pattern...",
            }
            _set_tree(elements.pattern_tree, [])
            _set_summary(
                elements.summary_message,
                elements.summary_median,
                elements.summary_total,
                elements.summary_remaining,
                elements.summary_events,
                elements.summary_games,
                loading_summary,
            )

            self._pattern_inflight = True

            def worker() -> None:
                try:
                    rows, summary = analysis.analyze_upload_frequencies_data(
                        self._paths.backup_dir,
                        db_file=self._paths.db_file,
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

                def apply_result() -> None:
                    self._pattern_cache = {
                        "rows": rows,
                        "summary": summary,
                        "log_mtime": db_mtime,
                        "data_mtime": db_mtime,
                        "computed_at": time.time(),
                    }
                    self._pattern_inflight = False
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

                root.after(0, apply_result)

            threading.Thread(target=worker, daemon=True).start()

        def show_tab(tab_name: str) -> None:
            root.deiconify()
            root.lift()
            root.focus_force()
            if tab_name == "logs":
                elements.notebook.select(elements.tab_logs)
                view.refresh_logs()
            elif tab_name == "pattern":
                elements.notebook.select(elements.tab_pattern)
                refresh_pattern()

        def poll_queue() -> None:
            while True:
                try:
                    command, payload = self._queue.get_nowait()
                except queue.Empty:
                    break

                if command == "show" and payload:
                    show_tab(payload)
                elif command == "refresh_logs":
                    view.refresh_logs()
                elif command == "refresh_pattern":
                    refresh_pattern()

            root.after(100, poll_queue)

        # Wire up toolbar buttons
        ttk.Button(elements.logs_toolbar, text="Refresh", command=view.refresh_logs).pack(side="right", padx=8, pady=6)
        ttk.Button(elements.logs_toolbar, text="Open Thread", command=view.open_selected_thread).pack(side="right", padx=8, pady=6)
        ttk.Button(elements.logs_toolbar, text="Mark Read", command=view.mark_selected_read).pack(side="right", padx=8, pady=6)
        ttk.Button(elements.logs_toolbar, text="Delete", command=view.delete_selected).pack(side="right", padx=8, pady=6)
        ttk.Button(elements.logs_toolbar, text="Clear All", command=view.clear_all_notifications).pack(side="right", padx=8, pady=6)
        ttk.Button(elements.logs_toolbar, text="Load more", command=view.load_more).pack(side="right", padx=8, pady=6)
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

        self._ready.set()
        poll_queue()
        root.mainloop()

    def open_logs(self) -> None:
        self._queue.put(("show", "logs"))

    def open_pattern(self) -> None:
        self._queue.put(("show", "pattern"))


_controller: _UiController | None = None


def _get_controller(paths: Paths | None = None, config: AppConfig | None = None) -> _UiController:
    global _controller
    if _controller is None:
        _controller = _UiController(paths or get_paths(), config)
    return _controller
