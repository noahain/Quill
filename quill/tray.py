"""System tray icon management for the Quill application."""

import logging
from pathlib import Path
from PIL import Image, ImageDraw
import pystray

logger = logging.getLogger("quill.tray")

ICON_SIZE = 64
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"


def _load_icon():
    """Load the tray icon from assets/icon.ico, falling back to a generated square."""
    icon_path = ASSETS_DIR / "icon.ico"
    if icon_path.is_file():
        try:
            logger.debug("Loading tray icon from %s", icon_path)
            return Image.open(icon_path).resize((ICON_SIZE, ICON_SIZE))
        except Exception:
            logger.warning("Failed to load icon from %s, using fallback", icon_path)
    return _generate_icon()


def _generate_icon():
    """Generate a simple fallback tray icon."""
    image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    dc = ImageDraw.Draw(image)
    margin = ICON_SIZE // 6
    dc.rounded_rectangle(
        (margin, margin, ICON_SIZE - margin, ICON_SIZE - margin),
        radius=margin,
        fill=(0, 212, 255, 255),
    )
    return image


class TrayManager:
    """Manages the system tray icon and menu for the Quill application."""

    def __init__(self, on_settings, on_exit):
        self._on_settings = on_settings
        self._on_exit = on_exit
        self._icon = None

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem("Settings", self._on_settings),
            pystray.MenuItem("Exit", self._on_exit),
        )

    def start(self):
        if self._icon:
            logger.debug("Tray already running, skipping start")
            return
        logger.info("Starting tray icon…")
        self._icon = pystray.Icon("Quill")
        self._icon.icon = _load_icon()
        self._icon.menu = self._build_menu()
        self._icon.title = "Quill - Idle"
        self._icon.run()

    def update_title(self, title: str):
        if self._icon:
            logger.debug("Tray title → %s", title)
            self._icon.title = title

    def notify(self, message: str, title: str = "Quill"):
        if self._icon:
            logger.info("Tray notification: [%s] %s", title, message)
            self._icon.notify(message, title)

    def stop(self):
        if self._icon:
            logger.info("Stopping tray icon…")
            self._icon.stop()
            self._icon = None
