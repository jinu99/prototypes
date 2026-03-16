"""Passive DNS capture module.

Captures DNS queries on the network to map which cloud endpoints
each device communicates with. Requires root privileges.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class DNSRecord:
    timestamp: float
    src_ip: str
    query_name: str
    query_type: str = "A"


@dataclass
class DeviceDNSProfile:
    ip: str
    queries: list[DNSRecord] = field(default_factory=list)
    endpoints: dict[str, int] = field(default_factory=dict)  # domain -> count
    _total_queries_override: int | None = field(default=None, repr=False)

    @property
    def total_queries(self) -> int:
        if self._total_queries_override is not None:
            return self._total_queries_override
        return len(self.queries)

    @total_queries.setter
    def total_queries(self, value: int):
        self._total_queries_override = value

    @property
    def unique_endpoints(self) -> int:
        return len(self.endpoints)

    def add_query(self, record: DNSRecord):
        self.queries.append(record)
        domain = _extract_base_domain(record.query_name)
        self.endpoints[domain] = self.endpoints.get(domain, 0) + 1


def _extract_base_domain(fqdn: str) -> str:
    """Extract the base domain from a FQDN.

    e.g., "api.us-east-1.amazonaws.com" -> "amazonaws.com"
    """
    parts = fqdn.rstrip(".").split(".")
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return fqdn


def capture_dns(
    interface: str = "eth0",
    duration: int = 300,
    device_ips: list[str] | None = None,
) -> dict[str, DeviceDNSProfile]:
    """Capture DNS traffic for the specified duration.

    Args:
        interface: Network interface to sniff on
        duration: Capture duration in seconds (default 300 = 5 min)
        device_ips: Optional list of IPs to filter for

    Returns:
        Dict mapping device IP -> DNSProfile
    """
    profiles: dict[str, DeviceDNSProfile] = defaultdict(
        lambda: DeviceDNSProfile(ip="")
    )

    try:
        from scapy.all import sniff, DNS, DNSQR, IP, conf
        conf.verb = 0

        print(f"[*] Starting DNS capture on {interface} for {duration}s...")
        start_time = time.time()

        def process_packet(pkt):
            if pkt.haslayer(DNS) and pkt.haslayer(DNSQR):
                if pkt[DNS].qr == 0:  # Query (not response)
                    src_ip = pkt[IP].src
                    if device_ips and src_ip not in device_ips:
                        return

                    query_name = pkt[DNSQR].qname.decode("utf-8", errors="ignore")
                    query_type = pkt[DNSQR].qtype

                    record = DNSRecord(
                        timestamp=time.time(),
                        src_ip=src_ip,
                        query_name=query_name,
                        query_type=str(query_type),
                    )

                    if src_ip not in profiles:
                        profiles[src_ip] = DeviceDNSProfile(ip=src_ip)
                    profiles[src_ip].add_query(record)

        sniff(
            iface=interface,
            filter="udp port 53",
            prn=process_packet,
            timeout=duration,
            store=False,
        )

        elapsed = time.time() - start_time
        print(f"[*] DNS capture complete. Duration: {elapsed:.0f}s")
        print(f"[*] Captured queries from {len(profiles)} devices")

    except (PermissionError, OSError) as e:
        print(f"[!] DNS capture requires root: {e}")
        return {}

    return dict(profiles)
