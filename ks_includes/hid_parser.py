"""HID input parser for card scanners and QR code readers."""

# Default prefix mappings for HID devices
DEFAULT_PREFIX_MAP = {
    "Q": "qr",
    "": "card",  # No prefix = NFC card/token
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
        >>> parse_hid_input("card-12345")
        {"type": "card", "content": "card-12345"}

        >>> parse_hid_input("Qhttps://example.com")
        {"type": "qr", "content": "https://example.com"}
    """
    if prefix_map is None:
        prefix_map = DEFAULT_PREFIX_MAP

    # Case-insensitive prefix matching
    accumulated_upper = accumulated_string.upper()

    for prefix, device_type in prefix_map.items():
        if prefix == "":
            # Empty prefix matches everything - put this last in the dict
            continue
        if accumulated_upper.startswith(prefix):
            return {
                "type": device_type,
                "content": accumulated_string[len(prefix):]  # Keep original case for content
            }

    # No prefix matched - check if empty prefix exists (default to card/token)
    if "" in prefix_map:
        return {"type": prefix_map[""], "content": accumulated_string}

    return {"type": "unknown", "content": accumulated_string}
