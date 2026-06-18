"""Protected token management panel that requires admin or manager authentication."""

import logging
import requests
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
        title_label.set_markup('<span size="x-large">Token Management</span>')
        title_label.set_halign(Gtk.Align.START)
        main_box.pack_start(title_label, False, False, 0)

        # Content area - horizontal layout with icon on left, toggles on right
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=40)
        content_box.set_halign(Gtk.Align.CENTER)
        content_box.set_valign(Gtk.Align.CENTER)

        # Left side - coin icon and instruction
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        left_box.set_valign(Gtk.Align.CENTER)

        # Coin icon (large)
        coin_icon = Gtk.Image()
        coin_icon.set_from_pixbuf(self._gtk.PixbufFromIcon("coin", self._gtk.img_width * 4.5, self._gtk.img_height * 4.5))
        left_box.pack_start(coin_icon, False, False, 0)

        # Instruction label
        instruction = Gtk.Label(label="Tap Your NFC Token to Proceed")
        instruction.set_justify(Gtk.Justification.CENTER)
        left_box.pack_start(instruction, False, False, 0)

        content_box.pack_start(left_box, True, True, 0)

        # Right side - toggle buttons
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        right_box.set_valign(Gtk.Align.CENTER)

        # Options label
        options_label = Gtk.Label()
        options_label.set_markup('<span size="large">Options</span>')
        options_label.set_halign(Gtk.Align.START)
        right_box.pack_start(options_label, False, False, 0)

        # Toggle button for Register/De-register mode
        self.mode_toggle = Gtk.ToggleButton(label="Register")
        self.mode_toggle.set_size_request(300, 80)
        self.mode_toggle.get_style_context().add_class("color4")  # Green
        self.mode_toggle.connect("toggled", self.on_mode_toggle)
        right_box.pack_start(self.mode_toggle, False, False, 0)

        # Toggle button for Infinite/Single-use mode
        self.use_toggle = Gtk.ToggleButton(label="Single-use")
        self.use_toggle.set_size_request(300, 80)
        self.use_toggle.get_style_context().add_class("color3")  # Cyan for single-use
        self.use_toggle.set_active(True)  # Default to single-use
        self.use_toggle.connect("toggled", self.on_use_toggle)
        right_box.pack_start(self.use_toggle, False, False, 0)

        content_box.pack_start(right_box, False, False, 0)

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
            logging.info("Token management: Registered keybinding handler 'handle_card_token_scan'")
        else:
            logging.warning("Token management: Keybinding system not available")

        GLib.idle_add(self._check_auth)

    def _check_auth(self):
        """Check authentication after panel is displayed."""
        logging.info("Token management protected: _check_auth called")

        def on_auth_success(api_key, role):
            logging.info(f"Token management access granted to {role}")
            self.elevated_api_key = api_key

        def on_auth_cancel():
            logging.info("Token management access denied - going back")
            self._screen._menu_go_back(None, home=False)

        logging.info("Token management protected: calling escalate_screen.escalate")
        self._screen.escalate_screen.escalate(
            ["admin", "manager"],
            success_callback=on_auth_success,
            cancel_callback=on_auth_cancel
        )

        return False

    def on_mode_toggle(self, toggle_btn):
        """Handle toggle between Register and De-register modes."""
        if toggle_btn.get_active():
            # De-register mode (magenta/red)
            toggle_btn.set_label("De-register")
            toggle_btn.get_style_context().remove_class("color4")
            toggle_btn.get_style_context().add_class("color2")
        else:
            # Register mode (green)
            toggle_btn.set_label("Register")
            toggle_btn.get_style_context().remove_class("color2")
            toggle_btn.get_style_context().add_class("color4")

    def on_use_toggle(self, toggle_btn):
        """Handle toggle between Infinite and Single-use modes."""
        if toggle_btn.get_active():
            # Single-use mode (cyan)
            toggle_btn.set_label("Single-use")
            toggle_btn.get_style_context().remove_class("color1")
            toggle_btn.get_style_context().add_class("color3")
        else:
            # Infinite mode (orange)
            toggle_btn.set_label("Infinite")
            toggle_btn.get_style_context().remove_class("color3")
            toggle_btn.get_style_context().add_class("color1")

    def on_card_token_scanned(self, buffer_contents):
        """Handle accumulated keyboard input from HID device."""
        logging.info(f"Token management: on_card_token_scanned called with: '{buffer_contents}'")
        from ks_includes.hid_parser import parse_hid_input

        parsed = parse_hid_input(buffer_contents)
        logging.info(f"Token management: Parsed as type='{parsed['type']}', content='{parsed['content']}'")

        # Accept any card/token scan (they're all NFC tags)
        if parsed["type"] == "qr":
            self._screen.show_popup_message("Please scan a card/token, not a QR code", level=2)
            return
        elif parsed["type"] == "unknown":
            self._screen.show_popup_message(f"Invalid input: {buffer_contents}", level=3)
            return

        # Extract the ID from the scanned card/token
        card_id = parsed["content"].strip()
        if not card_id:
            self._screen.show_popup_message("Card/Token ID is empty", level=3)
            return

        # Check current toggle states
        is_register = not self.mode_toggle.get_active()  # False = Register, True = De-register
        is_single_use = self.use_toggle.get_active()     # True = Single-use, False = Infinite

        if is_register:
            self._register_token(card_id, is_single_use)
        else:
            self._deregister_token(card_id)

    def _register_token(self, card_id, is_single_use):
        """Register a new token via API."""
        try:
            # Use the authenticated API key from escalate screen
            url = f"{self._screen.apiclient.endpoint}/access/card/register"
            headers = {"X-Api-Key": self.elevated_api_key or self._screen.apiclient.api_key}

            # Register NFC token card that executes COIN_INSERT gcode
            payload = {
                "card_id": card_id,
                "role": "token",
                "name": f"Token {card_id}",
                "request_path": "/printer/gcode/script",
                "request_body": {"script": "COIN_INSERT"},
                "once": is_single_use  # True for single-use, False for infinite
            }

            response = requests.post(url, json=payload, headers=headers, timeout=5)
            response.raise_for_status()
            result = response.json()

            if "result" in result:
                token_type = "Single-use" if is_single_use else "Infinite"
                self._screen.show_popup_message(
                    f"{token_type} token registered\nID: {result['result']['card_id']}",
                    level=1
                )
            else:
                self._screen.show_popup_message("Token registered (no ID returned)", level=1)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                self._screen.show_popup_message("Permission denied: Admin access required", level=3)
            elif e.response.status_code == 400:
                error_data = e.response.json() if e.response.text else {}
                message = error_data.get("error", {}).get("message", "Invalid request")
                self._screen.show_popup_message(f"Registration failed: {message}", level=3)
            else:
                self._screen.show_popup_message(f"API error: {e.response.status_code}", level=3)
        except Exception as e:
            logging.error(f"Token registration error: {e}")
            self._screen.show_popup_message(f"Registration failed: {str(e)}", level=3)

    def _deregister_token(self, token_id):
        """De-register (delete) a token via API."""
        try:
            url = f"{self._screen.apiclient.endpoint}/access/card/delete"
            headers = {"X-Api-Key": self.elevated_api_key or self._screen.apiclient.api_key}
            payload = {"card_id": token_id}

            response = requests.post(url, json=payload, headers=headers, timeout=5)
            response.raise_for_status()
            result = response.json()

            if "result" in result:
                self._screen.show_popup_message(f"Token de-registered: {result['result']['deleted']}", level=1)
            else:
                self._screen.show_popup_message("Token de-registered", level=1)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                self._screen.show_popup_message("Permission denied: Admin access required", level=3)
            elif e.response.status_code == 400:
                self._screen.show_popup_message("Token not found or invalid", level=3)
            else:
                self._screen.show_popup_message(f"API error: {e.response.status_code}", level=3)
        except Exception as e:
            logging.error(f"Token de-registration error: {e}")
            self._screen.show_popup_message(f"De-registration failed: {str(e)}", level=3)
