"""QR Mode panel with admin/manager authentication."""

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
        title_label.set_markup('<span size="x-large">QR Mode</span>')
        title_label.set_halign(Gtk.Align.START)
        main_box.pack_start(title_label, False, False, 0)

        # Content area - horizontal layout with icon on left, options on right
        content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=40)
        content_box.set_halign(Gtk.Align.CENTER)
        content_box.set_valign(Gtk.Align.CENTER)

        # Left side - QR code icon and instruction
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        left_box.set_valign(Gtk.Align.CENTER)

        # QR code icon (large)
        qr_icon = Gtk.Image()
        qr_icon.set_from_pixbuf(self._gtk.PixbufFromIcon("qr", self._gtk.img_width * 4.5, self._gtk.img_height * 4.5))
        left_box.pack_start(qr_icon, False, False, 0)

        # Instruction label
        instruction = Gtk.Label(label="Please Present Your Machine QR Code")
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

        # Toggle button for Manual/Auto mode
        self.mode_toggle = Gtk.ToggleButton(label="Manual")
        self.mode_toggle.set_size_request(300, 80)
        self.mode_toggle.get_style_context().add_class("color4")  # Green for manual
        self.mode_toggle.set_active(False)  # Default to manual
        self.mode_toggle.connect("toggled", self.on_mode_toggle)
        right_box.pack_start(self.mode_toggle, False, False, 0)

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
            logging.info("QR Mode: Registered keybinding handler 'handle_card_token_scan'")
        else:
            logging.warning("QR Mode: Keybinding system not available")

        GLib.idle_add(self._check_auth)

    def _check_auth(self):
        """Check authentication after panel is displayed."""
        logging.info("QR Mode protected: _check_auth called")

        def on_auth_success(api_key, role):
            logging.info(f"QR Mode access granted to {role}")
            self.elevated_api_key = api_key

        def on_auth_cancel():
            logging.info("QR Mode access denied - going back")
            self._screen._menu_go_back(None, home=False)

        logging.info("QR Mode protected: calling escalate_screen.escalate")
        self._screen.escalate_screen.escalate(
            ["admin", "manager"],
            success_callback=on_auth_success,
            cancel_callback=on_auth_cancel
        )

        return False

    def on_mode_toggle(self, toggle_btn):
        """Handle toggle between Manual and Auto modes."""
        if toggle_btn.get_active():
            # Auto mode (magenta)
            toggle_btn.set_label("Auto")
            toggle_btn.get_style_context().remove_class("color4")
            toggle_btn.get_style_context().add_class("color2")
        else:
            # Manual mode (green)
            toggle_btn.set_label("Manual")
            toggle_btn.get_style_context().remove_class("color2")
            toggle_btn.get_style_context().add_class("color4")

    def on_card_token_scanned(self, buffer_contents):
        """Handle accumulated keyboard input from HID device."""
        logging.info(f"QR Mode: on_card_token_scanned called with: '{buffer_contents}'")
        from ks_includes.hid_parser import parse_hid_input

        parsed = parse_hid_input(buffer_contents)
        logging.info(f"QR Mode: Parsed as type='{parsed['type']}', content='{parsed['content']}'")

        # QR mode expects QR codes
        if parsed["type"] == "qr":
            qr_content = parsed["content"].strip()
            if not qr_content:
                self._screen.show_popup_message("QR code is empty", level=3)
                return

            # Check if in manual or auto mode
            is_manual = not self.mode_toggle.get_active()  # False = Manual, True = Auto

            if is_manual:
                self._show_qr_confirmation(qr_content)
            else:
                self._send_qr_to_moonraker(qr_content)
        elif parsed["type"] == "card":
            self._screen.show_popup_message("Please scan a QR code, not a card", level=2)
        else:
            self._screen.show_popup_message(f"Invalid input: {buffer_contents}", level=3)

    def _show_qr_confirmation(self, qr_content):
        """Show confirmation dialog for manual mode."""
        label = Gtk.Label(label=f"Send QR code to printer?\n\n{qr_content}")
        label.set_line_wrap(True)

        buttons = [
            {
                "name": _("Confirm"),
                "response": Gtk.ResponseType.OK,
                "style": "dialog-info",
            },
            {
                "name": _("Cancel"),
                "response": Gtk.ResponseType.CANCEL,
                "style": "dialog-error",
            },
        ]

        self._gtk.Dialog(
            "Confirm QR Code",
            buttons,
            label,
            self._on_qr_confirmation_response,
            qr_content
        )

    def _on_qr_confirmation_response(self, dialog, response_id, qr_content):
        """Handle confirmation dialog response."""
        self._gtk.remove_dialog(dialog)

        if response_id == Gtk.ResponseType.OK:
            # User confirmed - send to Moonraker
            self._send_qr_to_moonraker(qr_content)
        else:
            # User cancelled
            logging.info("QR code scan cancelled by user")
            self._screen.show_popup_message("QR code scan cancelled", level=2)

    def _send_qr_to_moonraker(self, qr_content):
        """Send QR code content to Moonraker gcode endpoint."""
        import urllib.request
        import json

        url = f"http://127.0.0.1:7125/printer/gcode/script"

        try:
            # Use elevated API key from escalate_screen
            api_key = self.elevated_api_key or self._screen.apiclient.api_key
            headers = {
                "X-Api-Key": api_key,
                "Content-Type": "application/json"
            }

            # Send QR content as gcode script
            payload = {"script": qr_content}
            data = json.dumps(payload).encode('utf-8')

            req = urllib.request.Request(url, data=data, headers=headers, method='POST')
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read().decode('utf-8'))

                logging.info(f"QR code sent successfully: {qr_content}")
                self._screen.show_popup_message("QR code sent to printer", level=1)

        except urllib.error.HTTPError as e:
            error_msg = e.read().decode('utf-8')
            logging.error(f"QR send HTTP error: {e.code} - {error_msg}")
            self._screen.show_popup_message(f"Failed to send QR code: {e.code}", level=3)
        except Exception as e:
            logging.exception(f"QR send error: {e}")
            self._screen.show_popup_message(f"Error sending QR code: {str(e)}", level=3)
