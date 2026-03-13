from __future__ import annotations

from pathlib import Path
import tkinter as _tk
from tkinter import messagebox as _messagebox
from tkinter import ttk

from ..paths import Paths


def prompt_db_restore(paths: Paths, backups: list[Path]) -> Path | None:
    """Show a dialog to pick a DB backup to restore.

    Returns the selected backup Path or None if cancelled. Raises TclError if
    the environment can't create a Tk root (caller should handle).
    """
    root = _tk.Tk()
    root.title("Database Restore")
    root.geometry("540x320")

    ttk.Label(root, text="Database appears unhealthy. Choose a backup to restore:").pack(
        anchor="w", padx=8, pady=8
    )

    listbox = _tk.Listbox(root, height=10, width=80, selectmode=_tk.SINGLE)
    for b in backups:
        listbox.insert(_tk.END, f"{b.name} — {b.stat().st_size} bytes")
    listbox.pack(fill="both", expand=True, padx=8, pady=4)

    result: dict[str, Path | None] = {"choice": None}

    def on_restore() -> None:
        sel = listbox.curselection()
        if not sel:
            _messagebox.showwarning("No selection", "Please select a backup to restore.")
            return
        result["choice"] = backups[sel[0]]
        root.destroy()

    def on_cancel() -> None:
        result["choice"] = None
        root.destroy()

    btn_frame = ttk.Frame(root)
    btn_frame.pack(fill="x", padx=8, pady=8)
    ttk.Button(btn_frame, text="Restore Selected", command=on_restore).pack(side="right", padx=6)
    ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side="right")

    root.mainloop()
    return result["choice"]


def show_restore_result(success: bool, backup: Path | None) -> None:
    """Show a confirmation or error dialog after an attempted restore."""
    try:
        root = _tk.Tk()
        root.withdraw()
        if success:
            msg = f"Database restored from {backup.name}" if backup else "Database restored successfully."
            _messagebox.showinfo("Restore Successful", msg)
        else:
            _messagebox.showerror(
                "Restore Failed",
                "Failed to restore the database from the selected backup.",
            )
        root.destroy()
    except Exception:
        pass
