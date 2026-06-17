"""HID input parser for card scanners and QR code readers."""

# Default prefix mappings for HID devices
DEFAULT_PREFIX_MAP = {
    "CARD:": "card",
    "QR:": "qr",
    "TOKEN:": "token",
}


def parse_hid_input(accumulated_string, prefix_map=None):
    """
    Parse HID input with configurable prefixes.

    Args:
        accumulated_string: Raw accumulated input from HID device
        prefix_map: Optional dict mapping prefix -> device type
                   Defaults to DEFAULT_PREFIX_MAP if not provided

    Returns:
        dict: {"type": str, "content": str}
              type: "card", "qr", "token", or "unknown"
              content: input string with prefix stripped

    Example:
        >>> parse_hid_input("CARD:123456789")
        {"type": "card", "content": "123456789"}

        >>> parse_hid_input("QR:https://example.com")
        {"type": "qr", "content": "https://example.com"}
    """
    if prefix_map is None:
        prefix_map = DEFAULT_PREFIX_MAP

    # Case-insensitive prefix matching
    accumulated_upper = accumulated_string.upper()

    for prefix, device_type in prefix_map.items():
        if accumulated_upper.startswith(prefix):
            return {
                "type": device_type,
                "content": accumulated_string[len(prefix):]  # Keep original case for content
            }

    return {"type": "unknown", "content": accumulated_string}
