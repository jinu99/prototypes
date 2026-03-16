"""Network device discovery module.

Discovers IoT devices using:
- ARP scanning (Layer 2)
- mDNS browsing (multicast DNS)
- SSDP discovery (UPnP)

Requires root privileges for ARP scanning.
"""

import socket
import struct
import subprocess
import re
from dataclasses import dataclass, field

from oui_db import lookup_manufacturer


@dataclass
class Device:
    ip: str
    mac: str
    manufacturer: str = ""
    hostname: str = ""
    mdns_services: list[str] = field(default_factory=list)
    ssdp_info: str = ""

    def __post_init__(self):
        if not self.manufacturer:
            self.manufacturer = lookup_manufacturer(self.mac)


def arp_scan(interface: str = "eth0", network: str = "192.168.1.0/24") -> list[Device]:
    """Perform ARP scan to discover devices on the local network.

    Uses scapy's arping or falls back to system arp table.
    """
    devices = []

    try:
        from scapy.all import ARP, Ether, srp, conf
        conf.verb = 0

        arp = ARP(pdst=network)
        ether = Ether(dst="ff:ff:ff:ff:ff:ff")
        packet = ether / arp

        result = srp(packet, timeout=3, iface=interface, verbose=False)[0]

        for _, received in result:
            ip = received.psrc
            mac = received.hwsrc.upper()
            devices.append(Device(ip=ip, mac=mac))

    except (PermissionError, OSError) as e:
        print(f"[!] ARP scan requires root: {e}")
        print("[*] Falling back to ARP table...")
        devices = _read_arp_table()

    return devices


def _read_arp_table() -> list[Device]:
    """Read devices from system ARP table as fallback."""
    devices = []
    try:
        result = subprocess.run(
            ["arp", "-an"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.strip().split("\n"):
            match = re.search(
                r"\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+([0-9a-fA-F:]{17})", line
            )
            if match:
                ip, mac = match.group(1), match.group(2).upper()
                devices.append(Device(ip=ip, mac=mac))
    except Exception:
        pass
    return devices


def mdns_discover(timeout: float = 3.0) -> dict[str, list[str]]:
    """Discover mDNS services on the network.

    Returns: dict mapping IP -> list of service names
    """
    services: dict[str, list[str]] = {}

    try:
        from scapy.all import DNS, DNSQR, IP, UDP, sr1, conf
        conf.verb = 0

        # Query for common IoT mDNS service types
        service_types = [
            "_http._tcp.local",
            "_hap._tcp.local",       # HomeKit
            "_googlecast._tcp.local", # Chromecast
            "_airplay._tcp.local",    # AirPlay
            "_raop._tcp.local",       # AirPlay audio
            "_sonos._tcp.local",      # Sonos
            "_hue._tcp.local",        # Philips Hue
        ]

        mdns_ip = "224.0.0.251"
        mdns_port = 5353

        for svc in service_types:
            pkt = (
                IP(dst=mdns_ip)
                / UDP(dport=mdns_port)
                / DNS(rd=1, qd=DNSQR(qname=svc, qtype="PTR"))
            )
            try:
                ans = sr1(pkt, timeout=timeout, verbose=False)
                if ans and ans.haslayer(DNS):
                    src_ip = ans[IP].src
                    if src_ip not in services:
                        services[src_ip] = []
                    services[src_ip].append(svc)
            except Exception:
                continue

    except (PermissionError, OSError):
        pass

    return services


def ssdp_discover(timeout: float = 3.0) -> dict[str, str]:
    """Discover UPnP/SSDP devices on the network.

    Returns: dict mapping IP -> device description
    """
    devices: dict[str, str] = {}

    ssdp_request = (
        "M-SEARCH * HTTP/1.1\r\n"
        "HOST: 239.255.255.250:1900\r\n"
        'MAN: "ssdp:discover"\r\n'
        "MX: 2\r\n"
        "ST: ssdp:all\r\n"
        "\r\n"
    )

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        sock.sendto(
            ssdp_request.encode(), ("239.255.255.250", 1900)
        )

        while True:
            try:
                data, addr = sock.recvfrom(4096)
                response = data.decode("utf-8", errors="ignore")
                server = ""
                for line in response.split("\r\n"):
                    if line.upper().startswith("SERVER:"):
                        server = line.split(":", 1)[1].strip()
                        break
                devices[addr[0]] = server or "UPnP Device"
            except socket.timeout:
                break
        sock.close()
    except Exception:
        pass

    return devices


def scan_network(
    interface: str = "eth0", network: str = "192.168.1.0/24"
) -> list[Device]:
    """Full network scan combining ARP, mDNS, and SSDP.

    Returns combined device list with enriched information.
    """
    print(f"[*] Starting ARP scan on {network} (interface: {interface})...")
    devices = arp_scan(interface, network)
    device_map = {d.ip: d for d in devices}

    print(f"[*] Found {len(devices)} devices via ARP")
    print("[*] Running mDNS discovery...")
    mdns_results = mdns_discover()
    for ip, services in mdns_results.items():
        if ip in device_map:
            device_map[ip].mdns_services = services
        else:
            device_map[ip] = Device(
                ip=ip, mac="00:00:00:00:00:00", mdns_services=services
            )

    print("[*] Running SSDP discovery...")
    ssdp_results = ssdp_discover()
    for ip, info in ssdp_results.items():
        if ip in device_map:
            device_map[ip].ssdp_info = info
        else:
            device_map[ip] = Device(
                ip=ip, mac="00:00:00:00:00:00", ssdp_info=info
            )

    all_devices = list(device_map.values())
    print(f"[*] Total devices discovered: {len(all_devices)}")
    return all_devices
