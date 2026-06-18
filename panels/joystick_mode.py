"""Joystick Mode panel with admin/manager authentication."""

import logging
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

from ks_includes.screen_panel import ScreenPanel


class Panel(ScreenPanel):
    def __init__(self, screen, title):
        super().__init__(screen, title)

        # Store elevated API key after authentication
        self.elevated_api_key = None

        # Main container
        main_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=20,
            margin=40
        )

        # Title
        title_label = Gtk.Label()
        title_label.set_markup('<span size="x-large">Joystick Mode</span>')
        title_label.set_halign(Gtk.Align.START)
        main_box.pack_start(title_label, False, False, 0)

        # Content area - centered single box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content_box.set_halign(Gtk.Align.CENTER)
        content_box.set_valign(Gtk.Align.CENTER)

        # Joystick icon (large)
        joystick_icon = Gtk.Image()
        joystick_icon.set_from_pixbuf(self._gtk.PixbufFromIcon("joystick", self._gtk.img_width * 4.5, self._gtk.img_height * 4.5))
        content_box.pack_start(joystick_icon, False, False, 0)

        # Instruction label
        instruction = Gtk.Label(label="Insert Token and Control With Joystick and Button")
        instruction.set_justify(Gtk.Justification.CENTER)
        content_box.pack_start(instruction, False, False, 0)

        main_box.pack_start(content_box, True, True, 0)

        self.content.add(main_box)

    def activate(self):
        """Called every time the panel is shown - trigger auth check."""
        # Register keybinding handler
        if hasattr(self._screen, 'keybinding_system') and self._screen.keybinding_system:
            self._screen.keybinding_system.register_handler(
                "handle_card_token_scan",
                self.on_card_token_scanned
            )
            logging.info("Joystick Mode: Registered keybinding handler 'handle_card_token_scan'")
        else:
            logging.warning("Joystick Mode: Keybinding system not available")

        GLib.idle_add(self._check_auth)

    def _check_auth(self):
        """Check authentication after panel is displayed."""
        logging.info("Joystick Mode protected: _check_auth called")

        def on_auth_success(api_key, role):
            logging.info(f"Joystick Mode access granted to {role}")
            self.elevated_api_key = api_key

        def on_auth_cancel():
            logging.info("Joystick Mode access denied - going back")
            self._screen._menu_go_back(None, home=False)

        logging.info("Joystick Mode protected: calling escalate_screen.escalate")
        self._screen.escalate_screen.escalate(
            ["admin", "manager"],
            success_callback=on_auth_success,
            cancel_callback=on_auth_cancel
        )

        return False

    def on_card_token_scanned(self, buffer_contents):
        """Handle accumulated keyboard input from HID device."""
        logging.info(f"Joystick Mode: on_card_token_scanned called with: '{buffer_contents}'")
        from ks_includes.hid_parser import parse_hid_input

        parsed = parse_hid_input(buffer_contents)
        logging.info(f"Joystick Mode: Parsed as type='{parsed['type']}', content='{parsed['content']}'")

        # Joystick mode expects NFC cards/tokens
        if parsed["type"] == "card":
            card_id = parsed["content"].strip()
            if not card_id:
                self._screen.show_popup_message("Card ID is empty", level=3)
                return

            # Authenticate the card via Moonraker API
            self._authenticate_card(card_id)
        elif parsed["type"] == "qr":
            self._screen.show_popup_message("Please insert a token, not scan a QR code", level=2)
        else:
            self._screen.show_popup_message(f"Invalid input: {buffer_contents}", level=3)

    def _authenticate_card(self, card_id):
        """Authenticate card via Moonraker API."""
        import urllib.request
        import json

        url = f"http://127.0.0.1:7125/access/card?card_id={card_id}&type=auth"

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))

                if 'result' in data:
                    card_role = data['result']['type']
                    api_key = data['result']['api_key']

                    logging.info(f"Card authenticated with role: {card_role}")

                    # For joystick mode, only "token" role is valid
                    if card_role == "token":
                        self.elevated_api_key = api_key
                        self._enable_joystick_control()
                        self._screen.show_popup_message("Token accepted - Joystick enabled", level=1)
                    else:
                        self._screen.show_popup_message(f"Invalid card type: {card_role}", level=3)
                else:
                    self._screen.show_popup_message("Card authentication failed", level=3)

        except urllib.error.HTTPError as e:
            error_msg = e.read().decode('utf-8')
            logging.error(f"Card authentication HTTP error: {e.code} - {error_msg}")
            self._screen.show_popup_message("Card not found or invalid", level=3)
        except Exception as e:
            logging.exception(f"Card authentication error: {e}")
            self._screen.show_popup_message(f"Authentication error: {str(e)}", level=3)

    def _enable_joystick_control(self):
        """Enable joystick and button controls after successful authentication."""
        # TODO: Implement joystick control
        # - Listen for joystick movement events
        # - Send gcode commands for X/Y/Z movement
        # - Listen for button press to control claw
        logging.info("Joystick control enabled")
