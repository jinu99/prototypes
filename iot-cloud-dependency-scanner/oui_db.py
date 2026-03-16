"""MAC OUI database for manufacturer identification.

Maps MAC address prefixes (first 3 octets) to manufacturer names.
Covers popular IoT device manufacturers.
"""

# Format: "AA:BB:CC" -> "Manufacturer Name"
OUI_DATABASE: dict[str, str] = {
    # Amazon (Echo, Ring, etc.)
    "F0:F0:A4": "Amazon",
    "68:54:FD": "Amazon",
    "44:65:0D": "Amazon",
    "A0:02:DC": "Amazon",
    "FC:65:DE": "Amazon",
    "74:C2:46": "Amazon",
    # Google (Nest, Chromecast, etc.)
    "F4:F5:D8": "Google",
    "54:60:09": "Google",
    "A4:77:33": "Google",
    "30:FD:38": "Google",
    "F8:0F:F9": "Google",
    # Apple (HomePod, Apple TV)
    "3C:22:FB": "Apple",
    "AC:BC:32": "Apple",
    "F0:B4:79": "Apple",
    "A8:5C:2C": "Apple",
    "D0:03:4B": "Apple",
    # Samsung (SmartThings, TVs)
    "B0:47:BF": "Samsung",
    "8C:71:F8": "Samsung",
    "AC:5F:3E": "Samsung",
    "E4:7C:F9": "Samsung",
    # Philips (Hue)
    "00:17:88": "Philips Hue",
    "EC:B5:FA": "Philips Hue",
    # TP-Link (Kasa, Tapo)
    "50:C7:BF": "TP-Link",
    "60:32:B1": "TP-Link",
    "B0:BE:76": "TP-Link",
    "98:DA:C4": "TP-Link",
    # Sonos
    "78:28:CA": "Sonos",
    "B8:E9:37": "Sonos",
    "48:A6:B8": "Sonos",
    # Ring (Amazon subsidiary)
    "4C:19:4E": "Ring",
    "50:14:79": "Ring",
    # Wyze
    "2C:AA:8E": "Wyze",
    "D0:3F:27": "Wyze",
    # Tuya (white-label IoT)
    "D8:1F:12": "Tuya",
    "10:D5:61": "Tuya",
    # Xiaomi
    "64:CE:84": "Xiaomi",
    "78:11:DC": "Xiaomi",
    "28:6C:07": "Xiaomi",
    "50:EC:50": "Xiaomi",
    # Roku
    "DC:3A:5E": "Roku",
    "B0:A7:37": "Roku",
    "AC:3A:7A": "Roku",
    # LG (Smart TVs)
    "00:E0:91": "LG",
    "A8:23:FE": "LG",
    "CC:2D:83": "LG",
    # Nest (legacy, pre-Google)
    "18:B4:30": "Nest",
    "64:16:66": "Nest",
    # Ecobee
    "44:61:32": "Ecobee",
    # iRobot (Roomba)
    "50:14:79": "iRobot",
    # Wemo (Belkin)
    "58:EF:68": "Belkin Wemo",
    "EC:1A:59": "Belkin Wemo",
    # Arlo
    "9C:D3:6D": "Arlo",
    # Eufy
    "98:8B:0A": "Eufy",
    # LIFX
    "D0:73:D5": "LIFX",
    # Yeelight
    "04:CF:8C": "Yeelight",
    # Raspberry Pi (DIY IoT)
    "B8:27:EB": "Raspberry Pi",
    "DC:A6:32": "Raspberry Pi",
    "E4:5F:01": "Raspberry Pi",
    # ESP32/ESP8266 (Espressif - DIY IoT)
    "24:6F:28": "Espressif",
    "30:AE:A4": "Espressif",
    "A4:CF:12": "Espressif",
}


def lookup_manufacturer(mac: str) -> str:
    """Look up manufacturer from MAC address.

    Args:
        mac: MAC address in format "AA:BB:CC:DD:EE:FF"

    Returns:
        Manufacturer name or "Unknown"
    """
    prefix = mac.upper()[:8]
    return OUI_DATABASE.get(prefix, "Unknown")
