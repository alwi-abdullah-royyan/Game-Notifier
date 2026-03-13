from __future__ import annotations

import subprocess
import sys
from typing import Callable, Optional


class Notifier:
    """Cross-platform desktop notification dispatcher."""

    def show(
        self,
        title: str,
        message: str,
        duration: int = 10,
        threaded: bool = True,
        on_click: Optional[Callable[[], None]] = None,
    ) -> None:
        if sys.platform == "win32":
            _show_windows(title, message, duration=duration, threaded=threaded, on_click=on_click)
        elif sys.platform == "darwin":
            _show_macos(title, message)
        else:
            _show_linux(title, message)


def _show_windows(
    title: str,
    message: str,
    duration: int,
    threaded: bool,
    on_click: Optional[Callable[[], None]],
) -> None:
    try:
        from win10toast import ToastNotifier
        toaster = ToastNotifier()
        try:
            toaster.show_toast(
                title, message, duration=duration, threaded=threaded,
                callback_on_click=on_click,
            )
        except TypeError:
            # Older win10toast without callback_on_click.
            toaster.show_toast(title, message, duration=duration, threaded=threaded)
    except Exception:
        pass


def _show_macos(title: str, message: str) -> None:
    try:
        safe_title = title.replace("\\", "\\\\").replace('"', '\\"')
        safe_msg = message.replace("\\", "\\\\").replace('"', '\\"')
        subprocess.Popen(
            ["osascript", "-e",
             f'display notification "{safe_msg}" with title "{safe_title}"'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def _show_linux(title: str, message: str) -> None:
    try:
        subprocess.Popen(
            ["notify-send", "--", title, message],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass
