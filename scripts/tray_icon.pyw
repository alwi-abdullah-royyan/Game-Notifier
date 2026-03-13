from pathlib import Path
import threading

from pystray import Icon, MenuItem as item, Menu
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ICON_PATH = ROOT / "assets" / "1.ico"


def start_tray_icon(stop_event):
    def on_exit(icon, item):
        stop_event.set()
        icon.stop()

    def setup():
        icon_image = Image.open(ICON_PATH)

        icon = Icon(
            "GameNotifier",
            icon=icon_image,
            menu=Menu(item("Exit", on_exit)),
        )
        icon.run()

    threading.Thread(target=setup, daemon=True).start()
