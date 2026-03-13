from __future__ import annotations

from typing import Callable, Optional
import threading

from PIL import Image
from pystray import Icon, MenuItem, Menu

# Module-level reference to the running tray controller (if any)
_INSTANCE: "TrayController" | None = None


def register_tray(instance: "TrayController") -> None:
    global _INSTANCE
    _INSTANCE = instance


def get_tray() -> "TrayController" | None:
    return _INSTANCE


def _wrap_callback(fn: Callable[[], None], logger) -> Callable[[Icon, MenuItem], None]:
    def _handler(icon: Icon, item: MenuItem) -> None:
        try:
            fn()
        except Exception:
            if logger is not None:
                logger.error("Tray handler failed", exc_info=True)
    return _handler


class TrayController:
    def __init__(
        self,
        default_icon,
        alert_icon,
        get_missed: Callable[[], int],
        on_read_logs: Callable[[], None],
        on_clear: Callable[[], None],
        on_analyze: Callable[[], None],
        on_quit: Callable[[], None],
        on_restore_db: Callable[[], None] | None = None,
        logger=None,
        name: str = "GameNotifier",
        title: str = "Game Notifier",
        count_label: str = "New items",
    ) -> None:
        self._default_icon = default_icon
        self._alert_icon = alert_icon
        self._get_missed = get_missed
        self._on_read_logs = on_read_logs
        self._on_clear = on_clear
        self._on_analyze = on_analyze
        self._on_quit = on_quit
        self._on_restore_db = on_restore_db
        self._logger = logger
        self._name = name
        self._title = title
        self._count_label = count_label
        self._icon: Optional[Icon] = None

    def _build_menu(self) -> Menu:
        return Menu(
            MenuItem(
                lambda text: f"{self._count_label}: {self._get_missed()}",
                None,
                enabled=False,
            ),
            MenuItem("read log", _wrap_callback(self._on_read_logs, self._logger)),
            MenuItem(
                "Clear notification", _wrap_callback(self._on_clear, self._logger)
            ),
            MenuItem("Restore DB...", _wrap_callback(self._on_restore_db, self._logger)) if self._on_restore_db is not None else None,
            MenuItem(
                "read update/upload pattern",
                _wrap_callback(self._on_analyze, self._logger),
            ),
            MenuItem("Quit", self._handle_quit),
        )

    def _handle_quit(self, icon: Icon, item: MenuItem) -> None:
        try:
            self._on_quit()
        finally:
            icon.stop()

    def start(self) -> None:
        self._started = threading.Event()

        def setup() -> None:
            try:
                icon_image = Image.open(self._default_icon)
            except Exception:
                if self._logger is not None:
                    self._logger.error(
                        f"Failed to load tray icon '{self._default_icon}'",
                        exc_info=True,
                    )
                self._started.set()
                return
            self._icon = Icon(self._name, icon=icon_image, title=self._title)
            try:
                register_tray(self)
            except Exception:
                pass
            self._icon.menu = self._build_menu()
            self._started.set()  # signal setup done before blocking .run()
            self._icon.run()

        threading.Thread(target=setup, daemon=True).start()
        self._started.wait(timeout=5)

    def update(self) -> None:
        if not self._icon:
            return
        try:
            icon_image = Image.open(
                self._alert_icon if self._get_missed() else self._default_icon
            )
            self._icon.icon = icon_image
            self._icon.menu = self._build_menu()
            self._icon.update_menu()
        except Exception:
            if self._logger is not None:
                self._logger.error("Tray update failed", exc_info=True)
