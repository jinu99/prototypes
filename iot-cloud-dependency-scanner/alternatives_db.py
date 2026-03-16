"""Local alternative suggestions database.

Maps IoT manufacturers/categories to self-hosted or local alternatives.
Hardcoded for 10+ popular manufacturers as required by spec.
"""

from dataclasses import dataclass


@dataclass
class Alternative:
    name: str
    description: str
    url: str
    category: str  # "full_replacement", "partial", "bridge"


# Manufacturer -> list of local alternatives
ALTERNATIVES: dict[str, list[Alternative]] = {
    "Amazon": [
        Alternative(
            "Home Assistant",
            "Open-source home automation with Alexa-compatible skills",
            "https://www.home-assistant.io",
            "full_replacement",
        ),
        Alternative(
            "Mycroft/OVOS",
            "Open-source voice assistant, runs locally",
            "https://openvoiceos.org",
            "full_replacement",
        ),
    ],
    "Google": [
        Alternative(
            "Home Assistant",
            "Full local automation platform, replaces Google Home",
            "https://www.home-assistant.io",
            "full_replacement",
        ),
        Alternative(
            "Jellyfin",
            "Local media server to replace Chromecast streaming",
            "https://jellyfin.org",
            "partial",
        ),
    ],
    "Apple": [
        Alternative(
            "Home Assistant + HomeKit bridge",
            "Local HomeKit-compatible controller",
            "https://www.home-assistant.io/integrations/homekit",
            "bridge",
        ),
    ],
    "Samsung": [
        Alternative(
            "Home Assistant + SmartThings integration",
            "Local automation with optional SmartThings bridge",
            "https://www.home-assistant.io/integrations/smartthings",
            "bridge",
        ),
        Alternative(
            "Zigbee2MQTT",
            "Direct Zigbee device control without Samsung cloud",
            "https://www.zigbee2mqtt.io",
            "full_replacement",
        ),
    ],
    "Philips Hue": [
        Alternative(
            "Zigbee2MQTT",
            "Control Hue bulbs directly via Zigbee without Hue cloud",
            "https://www.zigbee2mqtt.io",
            "full_replacement",
        ),
        Alternative(
            "deCONZ",
            "Local Zigbee gateway for Hue and other Zigbee devices",
            "https://phoscon.de/en/conbee",
            "full_replacement",
        ),
    ],
    "TP-Link": [
        Alternative(
            "Tasmota",
            "Flash TP-Link devices with local-only firmware",
            "https://tasmota.github.io",
            "full_replacement",
        ),
        Alternative(
            "ESPHome",
            "Custom firmware for ESP-based TP-Link devices",
            "https://esphome.io",
            "full_replacement",
        ),
    ],
    "Sonos": [
        Alternative(
            "Snapcast",
            "Open-source multi-room audio synchronization",
            "https://github.com/badaix/snapcast",
            "full_replacement",
        ),
        Alternative(
            "Mopidy",
            "Local music server with Sonos-like features",
            "https://mopidy.com",
            "partial",
        ),
    ],
    "Ring": [
        Alternative(
            "Frigate NVR",
            "Local-only AI-powered NVR for security cameras",
            "https://frigate.video",
            "full_replacement",
        ),
        Alternative(
            "Scrypted",
            "Local video integration platform with HomeKit support",
            "https://www.scrypted.app",
            "full_replacement",
        ),
    ],
    "Wyze": [
        Alternative(
            "Frigate NVR + RTSP firmware",
            "Flash Wyze cams with RTSP firmware, use local NVR",
            "https://frigate.video",
            "full_replacement",
        ),
    ],
    "Tuya": [
        Alternative(
            "Tasmota",
            "Flash Tuya devices with local-only firmware",
            "https://tasmota.github.io",
            "full_replacement",
        ),
        Alternative(
            "LocalTuya",
            "Control Tuya devices locally without cloud",
            "https://github.com/rospogriern/localtuya",
            "bridge",
        ),
    ],
    "Xiaomi": [
        Alternative(
            "Valetudo",
            "Cloud-free firmware for Xiaomi robot vacuums",
            "https://valetudo.cloud",
            "full_replacement",
        ),
        Alternative(
            "Zigbee2MQTT",
            "Control Xiaomi Zigbee sensors locally",
            "https://www.zigbee2mqtt.io",
            "full_replacement",
        ),
    ],
    "Roku": [
        Alternative(
            "Jellyfin + Kodi",
            "Local media server and player combo",
            "https://jellyfin.org",
            "full_replacement",
        ),
    ],
    "LG": [
        Alternative(
            "Jellyfin",
            "Local media server for LG webOS TV app",
            "https://jellyfin.org",
            "partial",
        ),
    ],
    "Nest": [
        Alternative(
            "Home Assistant",
            "Full local replacement for Nest thermostat automation",
            "https://www.home-assistant.io",
            "full_replacement",
        ),
    ],
    "Ecobee": [
        Alternative(
            "Home Assistant + local API",
            "Ecobee has local API support for cloud-free control",
            "https://www.home-assistant.io/integrations/ecobee",
            "bridge",
        ),
    ],
    "iRobot": [
        Alternative(
            "Valetudo (Dreame/Roborock)",
            "Consider switching to Valetudo-compatible vacuums",
            "https://valetudo.cloud",
            "full_replacement",
        ),
    ],
    "Belkin Wemo": [
        Alternative(
            "Tasmota / ESPHome",
            "Flash with local-only firmware",
            "https://tasmota.github.io",
            "full_replacement",
        ),
    ],
    "Arlo": [
        Alternative(
            "Frigate NVR",
            "Replace with local RTSP cameras + Frigate",
            "https://frigate.video",
            "full_replacement",
        ),
    ],
    "LIFX": [
        Alternative(
            "LIFX LAN Protocol",
            "LIFX supports direct LAN control without cloud",
            "https://lan.developer.lifx.com",
            "bridge",
        ),
    ],
}


def get_alternatives(manufacturer: str) -> list[Alternative]:
    """Get local alternatives for a given manufacturer."""
    return ALTERNATIVES.get(manufacturer, [])


def get_all_manufacturers() -> list[str]:
    """Get list of all manufacturers with known alternatives."""
    return sorted(ALTERNATIVES.keys())
