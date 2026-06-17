"""Role-based escalation screen for card authentication."""

import logging
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Gdk

from ks_includes.hid_parser import parse_hid_input


class EscalateScreen:
    def __init__(self, screen):
        self.screen = screen
        self.escalate_box = None
        self.allowed_roles = []
        self.success_callback = None
        self.cancel_callback = None
        self.accumulator_buffer = ""
        self.accumulator_timeout = None
        self.ACCUMULATOR_TIMEOUT_MS = 10000  # 10s timeout for manual typing

    def escalate(self, allowed_roles, success_callback=None, cancel_callback=None):
        """
        Show escalation screen requiring card with one of the allowed roles.

        Args:
            allowed_roles: List of role strings (e.g., ["admin", "manager"])
            success_callback: Function to call on successful authentication (receives api_key and role)
            cancel_callback: Function to call if user cancels
        """
        if not allowed_roles:
            logging.error("Escalate called with empty allowed_roles")
            return

        self.allowed_roles = allowed_roles
        self.success_callback = success_callback
        self.cancel_callback = cancel_callback
        self.accumulator_buffer = ""

        logging.info(f"Escalating for roles: {allowed_roles}")

        # Create escalate overlay with opaque background
        # Use EventBox to allow background color
        event_box = Gtk.EventBox()
        event_box.set_size_request(self.screen.width, self.screen.height)

        main_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            width_request=self.screen.width,
            height_request=self.screen.height,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
        )
        main_box.get_style_context().add_class("escalate")

        # Add error-colored background for visibility
        event_box.get_style_context().add_class("error")
        event_box.add(main_box)

        # Back button in top-left corner
        back_button = Gtk.Button()
        back_button.set_image(self.screen.gtk.Image("back", self.screen.gtk.img_width * 0.6, self.screen.gtk.img_height * 0.6))
        back_button.set_relief(Gtk.ReliefStyle.NONE)
        back_button.get_style_context().add_class("error")
        back_button.connect("clicked", self._on_cancel)
        back_button.set_halign(Gtk.Align.START)
        back_button.set_valign(Gtk.Align.START)
        back_button.set_margin_top(20)
        back_button.set_margin_start(20)

        # Lock icon (large, at top)
        lock_icon = Gtk.Image()
        lock_icon.set_from_pixbuf(self.screen.gtk.PixbufFromIcon("lock", self.screen.gtk.img_width * 4.5, self.screen.gtk.img_height * 4.5))

        # Title label
        title = Gtk.Label()
        roles_text = " or ".join(allowed_roles)
        title.set_markup(f'<span size="x-large">Authentication Required</span>\n\n<span size="large">{roles_text} access needed</span>')
        title.set_justify(Gtk.Justification.CENTER)
        title.get_style_context().add_class("escalate_title")

        # Instruction label
        instruction = Gtk.Label(label="Please scan your card")
        instruction.get_style_context().add_class("escalate_instruction")

        # Pack elements
        main_box.pack_start(back_button, False, False, 0)
        main_box.pack_start(lock_icon, False, False, 3)
        main_box.pack_start(title, False, False, 0)
        main_box.pack_start(instruction, True, True, 0)

        self.escalate_box = event_box
        self.screen.overlay.add_overlay(self.escalate_box)
        self.escalate_box.show_all()

        # Connect to key press events for HID input
        self._connect_key_events()

    def _connect_key_events(self):
        """Connect to keyboard events to capture HID scanner input."""
        # screen is the KlipperScreen instance which is a Gtk.Window
        self.key_handler_id = self.screen.connect("key-press-event", self._on_key_press)

    def _disconnect_key_events(self):
        """Disconnect keyboard event handler."""
        if hasattr(self, 'key_handler_id'):
            self.screen.disconnect(self.key_handler_id)
            self.key_handler_id = None

    def _on_key_press(self, widget, event):
        """Handle key press events from HID devices."""
        if not self.escalate_box:
            return False

        keyval = event.keyval
        keyname = Gdk.keyval_name(keyval)

        # Handle Return/Enter as end of input
        if keyname in ("Return", "KP_Enter"):
            self._process_accumulated_input()
            return True

        # Try to get the unicode character from the keyval
        char = chr(Gdk.keyval_to_unicode(keyval))

        # Accumulate printable characters
        if char and char.isprintable():
            self.accumulator_buffer += char
            self._reset_accumulator_timeout()
            return True

        return False

    def _reset_accumulator_timeout(self):
        """Reset the accumulator timeout - if no input for timeout period, process buffer."""
        if self.accumulator_timeout:
            GLib.source_remove(self.accumulator_timeout)

        self.accumulator_timeout = GLib.timeout_add(
            self.ACCUMULATOR_TIMEOUT_MS,
            self._process_accumulated_input
        )

    def _process_accumulated_input(self):
        """Process the accumulated input buffer."""
        if self.accumulator_timeout:
            GLib.source_remove(self.accumulator_timeout)
            self.accumulator_timeout = None

        if not self.accumulator_buffer:
            return False

        input_data = self.accumulator_buffer
        self.accumulator_buffer = ""

        logging.debug(f"Processing HID input: {input_data[:20]}...")

        # Parse HID input
        parsed = parse_hid_input(input_data)

        if parsed["type"] != "card":
            logging.warning(f"Escalate received non-card input: {parsed['type']}")
            self._show_error("Please scan a card, not a QR code")
            return False

        card_id = parsed["content"]
        self._verify_card(card_id)

        return False

    def _verify_card(self, card_id):
        """Verify card has required role via nginx API."""
        import urllib.request
        import json

        url = f"http://127.0.0.1:7125/access/card?card_id={card_id}&type=auth"

        try:
            logging.info(f"Verifying card with roles: {self.allowed_roles}")
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))

                if 'result' in data:
                    card_role = data['result']['type']
                    api_key = data['result']['api_key']

                    logging.info(f"Card role: {card_role}")

                    if card_role in self.allowed_roles:
                        logging.info(f"Card authenticated successfully with role: {card_role}")
                        self._on_success(api_key, card_role)
                    else:
                        logging.warning(f"Card role '{card_role}' not in allowed roles: {self.allowed_roles}")
                        self._show_error(f"Access denied: {card_role} role not permitted")
                else:
                    logging.error(f"Card verification failed: {data}")
                    self._show_error("Card verification failed")

        except urllib.error.HTTPError as e:
            error_msg = e.read().decode('utf-8')
            logging.error(f"Card verification HTTP error: {e.code} - {error_msg}")
            self._show_error("Card not found or invalid")
        except Exception as e:
            logging.exception(f"Card verification error: {e}")
            self._show_error("Authentication error")

    def _on_success(self, api_key, role):
        """Handle successful authentication."""
        self._disconnect_key_events()
        self.clear_escalate()

        if self.success_callback:
            self.success_callback(api_key, role)

    def _on_cancel(self, widget=None):
        """Handle cancel button click."""
        logging.info("Escalate cancelled by user")
        self._disconnect_key_events()
        self.clear_escalate()

        if self.cancel_callback:
            self.cancel_callback()

    def _show_error(self, message):
        """Show error message popup."""
        self.screen.show_popup_message(message)

    def clear_escalate(self):
        """Remove escalate overlay."""
        if self.escalate_box:
            self.screen.overlay.remove(self.escalate_box)
        self.escalate_box = None
        self.accumulator_buffer = ""
        if self.accumulator_timeout:
            GLib.source_remove(self.accumulator_timeout)
            self.accumulator_timeout = None
