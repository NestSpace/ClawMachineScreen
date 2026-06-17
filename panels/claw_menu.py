import logging
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from ks_includes.screen_panel import ScreenPanel


class Panel(ScreenPanel):
    def __init__(self, screen, title, items=None):
        super().__init__(screen, title)

        # Create grid for buttons
        grid = Gtk.Grid(
            row_homogeneous=True,
            column_homogeneous=True,
            hexpand=True,
            vexpand=True
        )

        # Create 6 large buttons with icons and labels
        buttons = [
            ("qr", "QR Scan", "color1", self.qr_scan),
            ("joystick", "Joystick", "color2", self.joystick),
            ("info", "Tutorials", "color3", self.tutorials),
            ("card", "Card Management", "color4", self.register_card),
            ("coin", "Token Management", "color1", self.register_token),
            ("settings", "Settings", "color2", self.settings),
        ]

        # Arrange in 3x2 grid (3 columns, 2 rows)
        for i, (icon, label, style, callback) in enumerate(buttons):
            row = i // 3
            col = i % 3
            btn = self._gtk.Button(icon, label, style, scale=1.5)
            btn.connect("clicked", callback)
            grid.attach(btn, col, row, 1, 1)

        self.content.add(grid)

    def qr_scan(self, widget):
        logging.info("QR Scan clicked")
        self._screen.show_popup_message("QR Scan feature coming soon")

    def joystick(self, widget):
        logging.info("Joystick clicked")
        self._screen.show_popup_message("Joystick control coming soon")

    def tutorials(self, widget):
        logging.info("Tutorials clicked")
        self._screen.show_popup_message("Tutorials coming soon")

    def register_card(self, widget):
        logging.info("Card Management clicked")
        self._screen.show_panel("card_management", "Card Management", remove_all=False)

    def register_token(self, widget):
        logging.info("Token Management clicked")
        self._screen.show_panel("token_management", "Token Management", remove_all=False)

    def settings(self, widget):
        logging.info("Settings clicked")
        self._screen.show_panel("settings_protected", remove_all=False)
