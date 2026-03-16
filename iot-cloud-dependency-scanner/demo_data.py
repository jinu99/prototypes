"""Demo/mock data for testing without root privileges.

Provides realistic fake network scan and DNS capture results
simulating a typical smart home setup.
"""

import random
import time

from scanner import Device
from dns_capture import DeviceDNSProfile, DNSRecord


def generate_demo_devices() -> list[Device]:
    """Generate a realistic set of IoT devices."""
    return [
        Device(
            ip="192.168.1.10",
            mac="F0:F0:A4:11:22:33",
            manufacturer="Amazon",
            hostname="echo-dot-kitchen",
            mdns_services=["_airplay._tcp.local"],
        ),
        Device(
            ip="192.168.1.11",
            mac="54:60:09:AA:BB:CC",
            manufacturer="Google",
            hostname="chromecast-living-room",
            mdns_services=["_googlecast._tcp.local"],
        ),
        Device(
            ip="192.168.1.12",
            mac="00:17:88:DD:EE:FF",
            manufacturer="Philips Hue",
            hostname="hue-bridge",
            mdns_services=["_hue._tcp.local"],
            ssdp_info="Philips Hue Bridge",
        ),
        Device(
            ip="192.168.1.13",
            mac="50:C7:BF:11:22:33",
            manufacturer="TP-Link",
            hostname="kasa-plug-desk",
        ),
        Device(
            ip="192.168.1.14",
            mac="78:28:CA:AA:BB:CC",
            manufacturer="Sonos",
            hostname="sonos-beam",
            mdns_services=["_sonos._tcp.local"],
            ssdp_info="Sonos Beam",
        ),
        Device(
            ip="192.168.1.15",
            mac="4C:19:4E:11:22:33",
            manufacturer="Ring",
            hostname="ring-doorbell-front",
        ),
        Device(
            ip="192.168.1.16",
            mac="2C:AA:8E:DD:EE:FF",
            manufacturer="Wyze",
            hostname="wyze-cam-garage",
        ),
        Device(
            ip="192.168.1.17",
            mac="64:CE:84:11:22:33",
            manufacturer="Xiaomi",
            hostname="roborock-s7",
        ),
        Device(
            ip="192.168.1.18",
            mac="DC:3A:5E:AA:BB:CC",
            manufacturer="Roku",
            hostname="roku-ultra",
            ssdp_info="Roku Ultra",
        ),
        Device(
            ip="192.168.1.19",
            mac="D8:1F:12:11:22:33",
            manufacturer="Tuya",
            hostname="smart-curtain",
        ),
        Device(
            ip="192.168.1.20",
            mac="3C:22:FB:AA:BB:CC",
            manufacturer="Apple",
            hostname="apple-tv-bedroom",
            mdns_services=["_airplay._tcp.local", "_raop._tcp.local"],
        ),
        Device(
            ip="192.168.1.21",
            mac="B0:47:BF:DD:EE:FF",
            manufacturer="Samsung",
            hostname="samsung-tv-55",
            ssdp_info="Samsung Smart TV",
        ),
        Device(
            ip="192.168.1.22",
            mac="18:B4:30:11:22:33",
            manufacturer="Nest",
            hostname="nest-thermostat",
        ),
        Device(
            ip="192.168.1.23",
            mac="B8:27:EB:AA:BB:CC",
            manufacturer="Raspberry Pi",
            hostname="pi-homeassistant",
        ),
        Device(
            ip="192.168.1.24",
            mac="D0:73:D5:11:22:33",
            manufacturer="LIFX",
            hostname="lifx-bulb-living",
        ),
    ]


def _make_queries(ip: str, domains: list[tuple[str, int]]) -> DeviceDNSProfile:
    """Helper to create a DNS profile with specified query patterns."""
    profile = DeviceDNSProfile(ip=ip)
    base_time = time.time() - 300  # 5 minutes ago

    for domain, count in domains:
        for i in range(count):
            record = DNSRecord(
                timestamp=base_time + random.uniform(0, 300),
                src_ip=ip,
                query_name=domain,
            )
            profile.add_query(record)

    return profile


def generate_demo_dns_profiles() -> dict[str, DeviceDNSProfile]:
    """Generate realistic DNS profiles for demo devices."""
    return {
        # Amazon Echo - heavy cloud user
        "192.168.1.10": _make_queries("192.168.1.10", [
            ("device-metrics-us.amazon.com", 45),
            ("api.amazonalexa.com", 30),
            ("avs-alexa-14-na.amazon.com", 25),
            ("unagi-na.amazon.com", 15),
            ("dp-gw-na.amazon.com", 12),
            ("dcape-na.amazon.com", 8),
            ("d3p8zr0ffa9t17.cloudfront.net", 20),
            ("fireoscaptiveportal.com", 5),
        ]),
        # Google Chromecast
        "192.168.1.11": _make_queries("192.168.1.11", [
            ("clients3.google.com", 35),
            ("connectivitycheck.gstatic.com", 20),
            ("play.googleapis.com", 15),
            ("www.googleapis.com", 12),
            ("android.clients.google.com", 10),
            ("time.google.com", 8),
        ]),
        # Philips Hue - moderate, mostly local
        "192.168.1.12": _make_queries("192.168.1.12", [
            ("diag.meethue.com", 8),
            ("ws.meethue.com", 5),
            ("firmware.meethue.com", 2),
        ]),
        # TP-Link Kasa
        "192.168.1.13": _make_queries("192.168.1.13", [
            ("euw1-api.tplinkcloud.com", 25),
            ("use1-api.tplinkcloud.com", 20),
            ("n-devs.tplinkcloud.com", 15),
            ("d1oxm0i0bf1kek.cloudfront.net", 10),
        ]),
        # Sonos
        "192.168.1.14": _make_queries("192.168.1.14", [
            ("api.ws.sonos.com", 18),
            ("msmetrics.ws.sonos.com", 12),
            ("update-firmware.sonos.com", 3),
            ("dcapps.ws.sonos.com", 8),
        ]),
        # Ring Doorbell - heavy cloud
        "192.168.1.15": _make_queries("192.168.1.15", [
            ("fw.ring.com", 40),
            ("app.ring.com", 30),
            ("nw.ring.com", 25),
            ("oauth.ring.com", 5),
            ("prd-api-us.ring.com", 20),
            ("d26hhearhq0yso.cloudfront.net", 15),
            ("snoo-production.kinesisvideo.us-east-1.amazonaws.com", 35),
        ]),
        # Wyze Cam
        "192.168.1.16": _make_queries("192.168.1.16", [
            ("api.wyzecam.com", 30),
            ("wyze-mars-service.wyzecam.com", 20),
            ("iot.wyzecam.com", 15),
            ("api.tuyaus.com", 10),
        ]),
        # Xiaomi Roborock
        "192.168.1.17": _make_queries("192.168.1.17", [
            ("ot.io.mi.com", 20),
            ("de.api.io.mi.com", 15),
            ("account.xiaomi.com", 8),
            ("sdkconfig.ad.xiaomi.com", 12),
            ("tracking.miui.com", 10),
        ]),
        # Roku
        "192.168.1.18": _make_queries("192.168.1.18", [
            ("logs.roku.com", 30),
            ("cooper.logs.roku.com", 20),
            ("scribe.logs.roku.com", 15),
            ("api.sr.roku.com", 10),
        ]),
        # Tuya smart curtain
        "192.168.1.19": _make_queries("192.168.1.19", [
            ("a2.tuyaus.com", 20),
            ("m2.tuyaus.com", 15),
            ("p2.tuyaus.com", 10),
        ]),
        # Apple TV - moderate
        "192.168.1.20": _make_queries("192.168.1.20", [
            ("gsp-ssl.ls.apple.com", 12),
            ("configuration.apple.com", 8),
            ("xp.apple.com", 6),
            ("init.itunes.apple.com", 5),
            ("play.itunes.apple.com", 4),
        ]),
        # Samsung TV
        "192.168.1.21": _make_queries("192.168.1.21", [
            ("gpm.samsungcloud.com", 20),
            ("lcprd1.samsungcloudsolution.net", 15),
            ("osb-apps.samsungqbe.com", 10),
            ("d1oxlq5h9knih.cloudfront.net", 8),
            ("cdn.samsungcloudsolution.net", 12),
        ]),
        # Nest Thermostat
        "192.168.1.22": _make_queries("192.168.1.22", [
            ("frontdoor.nest.com", 25),
            ("home.nest.com", 20),
            ("transport.home.nest.com", 18),
            ("log-upload.home.nest.com", 10),
            ("czfe.nest.com", 8),
        ]),
        # Raspberry Pi (Home Assistant) - mostly local
        "192.168.1.23": _make_queries("192.168.1.23", [
            ("github.com", 3),
            ("pypi.org", 2),
        ]),
        # LIFX - moderate
        "192.168.1.24": _make_queries("192.168.1.24", [
            ("cloud.lifx.com", 10),
            ("api.lifx.com", 5),
        ]),
    }
