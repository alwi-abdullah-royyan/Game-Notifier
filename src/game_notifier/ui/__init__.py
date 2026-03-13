from __future__ import annotations

# Public API — all callers use `from . import ui; ui.open_logs(...)` unchanged.

from ..config import AppConfig
from ..paths import Paths
from ._controller import _get_controller
from ._dialogs import prompt_db_restore, show_restore_result
from ._standalone import run_standalone


def open_logs(paths: Paths | None = None, config: AppConfig | None = None) -> None:
    _get_controller(paths, config).open_logs()


def open_pattern(paths: Paths | None = None, config: AppConfig | None = None) -> None:
    _get_controller(paths, config).open_pattern()


__all__ = [
    "open_logs",
    "open_pattern",
    "run_standalone",
    "prompt_db_restore",
    "show_restore_result",
]
