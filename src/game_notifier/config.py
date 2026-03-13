from dataclasses import dataclass
from pathlib import Path
import json


def _config_error(msg: str) -> None:
    """Show a visible error dialog (or stderr) then exit cleanly."""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Game Notifier — Config Error", msg)
        root.destroy()
    except Exception:
        pass
    raise SystemExit(msg)


@dataclass(frozen=True)
class AppConfig:
    api_url_initial: str
    api_url_poll: str
    base_delay: int = 120
    max_backoff: int = 300
    request_timeout: int = 10
    retry_after_default: int = 60
    log_max_bytes: int = 5 * 1024 * 1024
    log_backup_count: int = 3
    # Display / notification text — override in config.json for any source
    app_name: str = "Game Notifier"
    item_label_new: str = "new item(s)"
    item_label_updated: str = "updated item(s)"
    tray_count_label: str = "New items"
    # API adapter — field names must match your API response structure
    response_path: tuple[str, ...] = ("msg", "data")
    field_id: str = "thread_id"
    field_timestamp: str = "ts"
    field_title: str = "title"
    field_creator: str | None = "creator"
    item_url_template: str = ""
    cache_buster_unit: str | None = "ms"
    # DB recovery and backup options
    db_auto_restore: bool = False
    db_restore_prompt: bool = True
    db_backup_max: int = 5


def load_config(path: Path) -> AppConfig:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        _config_error(
            f"Config file not found: {path}\n"
            "Copy config/config_example.json to config/config.json and fill in your API URLs."
        )
    except json.JSONDecodeError as e:
        _config_error(f"Config file is not valid JSON: {path}\n{e}")

    if "API_URL90" in data and "API_URL15" in data:
        api_initial = data["API_URL90"]
        api_poll = data["API_URL15"]
    elif "API_URL" in data:
        # Legacy config fallback
        api_initial = data["API_URL"]
        api_poll = data["API_URL"]
    else:
        _config_error(
            f"Config error in {path}: must define 'API_URL90'/'API_URL15' (or legacy 'API_URL')."
        )

    try:
        return AppConfig(
        api_url_initial=api_initial,
        api_url_poll=api_poll,
        base_delay=int(data.get("BASE_DELAY", 120)),
        max_backoff=int(data.get("MAX_BACKOFF", 300)),
        request_timeout=int(data.get("REQUEST_TIMEOUT", 10)),
        retry_after_default=int(data.get("RETRY_AFTER_DEFAULT", 60)),
        log_max_bytes=int(data.get("LOG_MAX_BYTES", 5 * 1024 * 1024)),
        log_backup_count=int(data.get("LOG_BACKUP_COUNT", 3)),
        app_name=str(data.get("APP_NAME", "Game Notifier")),
        item_label_new=str(data.get("ITEM_LABEL_NEW", "new item(s)")),
        item_label_updated=str(data.get("ITEM_LABEL_UPDATED", "updated item(s)")),
        tray_count_label=str(data.get("TRAY_COUNT_LABEL", "New items")),
        response_path=tuple(data.get("RESPONSE_PATH", ["msg", "data"])),
        field_id=str(data.get("FIELD_ID", "thread_id")),
        field_timestamp=str(data.get("FIELD_TIMESTAMP", "ts")),
        field_title=str(data.get("FIELD_TITLE", "title")),
        field_creator=data.get("FIELD_CREATOR", "creator"),
        item_url_template=str(data.get("ITEM_URL_TEMPLATE", "")),
        cache_buster_unit=data.get("CACHE_BUSTER_UNIT", "ms"),
        db_auto_restore=bool(data.get("DB_AUTO_RESTORE", False)),
        db_restore_prompt=bool(data.get("DB_RESTORE_PROMPT", True)),
        db_backup_max=int(data.get("DB_BACKUP_MAX", 5)),
        )
    except (ValueError, TypeError) as e:
        _config_error(f"Config value error in {path}: {e}")
