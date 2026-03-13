from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import webbrowser
import tkinter as tk
from tkinter import ttk

from .. import analysis
from .. import storage
from .. import tray
from ..config import AppConfig
from ..paths import Paths


@dataclass
class _UiElements:
    root: tk.Tk
    notebook: ttk.Notebook
    tab_logs: ttk.Frame
    tab_pattern: ttk.Frame
    logs_toolbar: ttk.Frame
    pattern_toolbar: ttk.Frame
    logs_tree: ttk.Treeview
    logs_filter_var: tk.StringVar
    logs_filter_entry: ttk.Entry
    logs_count: ttk.Label
    pattern_tree: ttk.Treeview
    summary_message: ttk.Label
    summary_median: ttk.Label
    summary_total: ttk.Label
    summary_remaining: ttk.Label
    summary_events: ttk.Label
    summary_games: ttk.Label


def _set_tree(tree: ttk.Treeview, rows: list[dict]) -> None:
    tree.delete(*tree.get_children())
    for row in rows:
        tree.insert(
            "",
            "end",
            values=(
                row["hour"],
                row["total"],
                row["today"],
                f"{row['avg']:.2f}",
                f"{row['prob']:.1f}",
            ),
        )


def _set_logs_tree(tree: ttk.Treeview, rows: list[dict]) -> None:
    tree.delete(*tree.get_children())
    for row in rows:
        tree.insert(
            "",
            "end",
            values=(
                row["timestamp"],
                row["kind"],
                row["title"],
                row["creator"],
                row["thread_id"],
            ),
        )


def _set_summary(
    summary_message: ttk.Label,
    summary_median: ttk.Label,
    summary_total: ttk.Label,
    summary_remaining: ttk.Label,
    summary_events: ttk.Label,
    summary_games: ttk.Label,
    summary: dict,
) -> None:
    if "message" in summary:
        summary_message.config(text=summary["message"])
    else:
        summary_message.config(text="")

    summary_median.config(
        text=f"Median total uploads per day: {summary['median_daily']}"
    )
    summary_total.config(
        text=f"Total uploads today so far: {summary['total_uploads_today']}"
    )
    summary_remaining.config(
        text=f"Estimated remaining uploads today: {summary['remaining_estimate']}"
    )
    summary_events.config(
        text=f"Total upload events (30 days): {summary.get('total_upload_events', 0)}"
    )
    oldest = summary.get("oldest_timestamp")
    total_games = summary.get("total_games_logged", 0)
    if total_games and oldest:
        summary_games.config(text=f"Total games logged since {oldest}: {total_games}")
    else:
        summary_games.config(text="Total games logged: 0")


def _create_table_panel(parent: ttk.Frame) -> ttk.Treeview:
    container = ttk.Frame(parent)
    container.pack(fill="both", expand=True)

    columns = ("hour", "total", "today", "avg", "prob")
    tree = ttk.Treeview(container, columns=columns, show="headings", height=20)

    tree.heading("hour", text="Hour")
    tree.heading("total", text="Total uploads")
    tree.heading("today", text="Today uploads")
    tree.heading("avg", text="Avg per day")
    tree.heading("prob", text="Probability (%)")

    tree.column("hour", width=80, anchor="center")
    tree.column("total", width=120, anchor="e")
    tree.column("today", width=120, anchor="e")
    tree.column("avg", width=100, anchor="e")
    tree.column("prob", width=120, anchor="e")

    scrollbar_y = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar_y.set)

    tree.grid(row=0, column=0, sticky="nsew")
    scrollbar_y.grid(row=0, column=1, sticky="ns")

    container.columnconfigure(0, weight=1)
    container.rowconfigure(0, weight=1)

    return tree


def _create_logs_panel(parent: ttk.Frame) -> ttk.Treeview:
    container = ttk.Frame(parent)
    container.pack(fill="both", expand=True)

    columns = ("timestamp", "kind", "title", "creator", "thread_id")
    tree = ttk.Treeview(container, columns=columns, show="headings", height=20)

    tree.heading("timestamp", text="Time")
    tree.heading("kind", text="Type")
    tree.heading("title", text="Title")
    tree.heading("creator", text="Creator")
    tree.heading("thread_id", text="ID")

    tree.column("timestamp", width=150, anchor="center")
    tree.column("kind", width=80, anchor="center")
    tree.column("title", width=360, anchor="w")
    tree.column("creator", width=180, anchor="w")
    tree.column("thread_id", width=80, anchor="e")

    scrollbar_y = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
    scrollbar_x = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=scrollbar_y.set, xscrollcommand=scrollbar_x.set)

    tree.grid(row=0, column=0, sticky="nsew")
    scrollbar_y.grid(row=0, column=1, sticky="ns")
    scrollbar_x.grid(row=1, column=0, sticky="ew")

    container.columnconfigure(0, weight=1)
    container.rowconfigure(0, weight=1)

    return tree


def _build_ui(root: tk.Tk) -> _UiElements:
    root.title("Game Notifier")
    root.geometry("900x600")
    root.minsize(800, 500)

    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

    tab_logs = ttk.Frame(notebook)
    tab_pattern = ttk.Frame(notebook)

    notebook.add(tab_logs, text="Logs")
    notebook.add(tab_pattern, text="Upload Pattern")

    logs_toolbar = ttk.Frame(tab_logs)
    logs_toolbar.pack(fill="x")

    pattern_toolbar = ttk.Frame(tab_pattern)
    pattern_toolbar.pack(fill="x")

    logs_filter_var = tk.StringVar()
    ttk.Label(logs_toolbar, text="Search:").pack(side="left", padx=8, pady=6)
    logs_filter_entry = ttk.Entry(logs_toolbar, textvariable=logs_filter_var, width=30)
    logs_filter_entry.pack(side="left", padx=4, pady=6)
    logs_count = ttk.Label(logs_toolbar, text="")
    logs_count.pack(side="left", padx=8, pady=6)

    logs_tree = _create_logs_panel(tab_logs)
    pattern_tree = _create_table_panel(tab_pattern)

    summary_frame = ttk.Frame(tab_pattern)
    summary_frame.pack(fill="x", padx=10, pady=8)
    summary_message = ttk.Label(summary_frame, text="")
    summary_median = ttk.Label(summary_frame, text="Median total uploads per day: -")
    summary_total = ttk.Label(summary_frame, text="Total uploads today so far: -")
    summary_remaining = ttk.Label(
        summary_frame, text="Estimated remaining uploads today: -"
    )
    summary_events = ttk.Label(summary_frame, text="Total upload events (30 days): -")
    summary_games = ttk.Label(summary_frame, text="Total games logged since -: -")

    summary_message.pack(anchor="w")
    summary_median.pack(anchor="w")
    summary_total.pack(anchor="w")
    summary_remaining.pack(anchor="w")
    summary_events.pack(anchor="w")
    summary_games.pack(anchor="w")

    return _UiElements(
        root=root,
        notebook=notebook,
        tab_logs=tab_logs,
        tab_pattern=tab_pattern,
        logs_toolbar=logs_toolbar,
        pattern_toolbar=pattern_toolbar,
        logs_tree=logs_tree,
        logs_filter_var=logs_filter_var,
        logs_filter_entry=logs_filter_entry,
        logs_count=logs_count,
        pattern_tree=pattern_tree,
        summary_message=summary_message,
        summary_median=summary_median,
        summary_total=summary_total,
        summary_remaining=summary_remaining,
        summary_events=summary_events,
        summary_games=summary_games,
    )


def _format_notification_row(r: dict) -> dict:
    """Convert a raw DB notification dict into a display row."""
    ts = r.get("ts") or 0
    timestamp = datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
    return {
        "timestamp": timestamp,
        "kind": r.get("label", ""),
        "title": r.get("title", ""),
        "creator": r.get("creator", ""),
        "thread_id": r.get("id", ""),
    }


class _LogsView:
    """Shared logs-tab logic: data load, filter, and row actions.

    Used by both _UiController (threaded, tray-connected) and run_standalone.
    All methods must be called from the Tk main thread.
    """

    def __init__(
        self,
        paths: Paths,
        config: AppConfig | None,
        elements: _UiElements,
        limit: int = 100,
    ) -> None:
        self._paths = paths
        self._config = config
        self._elements = elements
        self._limit = limit
        self._all_rows: list[dict] = []

    def refresh_logs(self) -> None:
        try:
            rows = storage.get_recent_notifications(self._paths.db_file, limit=self._limit)
            self._all_rows = [_format_notification_row(r) for r in rows]
        except Exception as e:
            self._all_rows = []
            print(f"Failed to read notifications from DB: {e}")
        self.apply_filter()

    def apply_filter(self) -> None:
        query = self._elements.logs_filter_var.get().strip().lower()
        if not query:
            filtered = self._all_rows
        else:
            filtered = [
                row
                for row in self._all_rows
                if query in row["title"].lower()
                or query in row["creator"].lower()
                or query in row["thread_id"]
                or query in row["kind"].lower()
                or query in row["timestamp"]
            ]
        _set_logs_tree(self._elements.logs_tree, filtered)
        self._elements.logs_count.config(
            text=f"{len(filtered)} of {len(self._all_rows)}"
        )

    def clear_filter(self) -> None:
        self._elements.logs_filter_var.set("")
        self.apply_filter()

    def open_selected_thread(self) -> None:
        selection = self._elements.logs_tree.selection()
        if not selection:
            return
        values = self._elements.logs_tree.item(selection[0], "values")
        if len(values) < 5:
            return
        thread_id = values[4]
        if not thread_id:
            return
        template = self._config.item_url_template if self._config else ""
        if template:
            webbrowser.open(template.format(id=thread_id))

    def mark_selected_read(self) -> None:
        sel = self._elements.logs_tree.selection()
        if not sel:
            return
        for item_id in sel:
            vals = self._elements.logs_tree.item(item_id, "values")
            if len(vals) >= 5:
                nid = vals[4]
                try:
                    storage.mark_notification_seen(self._paths.db_file, nid)
                except Exception:
                    pass
        self.refresh_logs()
        self._update_tray()

    def delete_selected(self) -> None:
        sel = self._elements.logs_tree.selection()
        if not sel:
            return
        for item_id in sel:
            vals = self._elements.logs_tree.item(item_id, "values")
            if len(vals) >= 5:
                nid = vals[4]
                try:
                    storage.delete_notification(self._paths.db_file, nid)
                except Exception:
                    pass
        self.refresh_logs()
        self._update_tray()

    def clear_all_notifications(self) -> None:
        try:
            storage.clear_notifications_db(self._paths.db_file)
        except Exception:
            pass
        self.refresh_logs()
        self._update_tray()

    def load_more(self) -> None:
        self._limit += 100
        self.refresh_logs()

    def _update_tray(self) -> None:
        t = tray.get_tray()
        if t is not None:
            try:
                t.update()
            except Exception:
                pass
