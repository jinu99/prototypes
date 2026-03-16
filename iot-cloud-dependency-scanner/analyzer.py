"""Cloud dependency analysis module.

Calculates cloud dependency scores based on DNS query patterns.
"""

import math
from dataclasses import dataclass

from dns_capture import DeviceDNSProfile
from scanner import Device
from alternatives_db import get_alternatives, Alternative


# Known cloud provider domains for categorization
CLOUD_PROVIDERS = {
    "amazonaws.com": "AWS",
    "azure.com": "Azure",
    "azure-devices.net": "Azure IoT",
    "googleapis.com": "Google Cloud",
    "google.com": "Google",
    "gstatic.com": "Google",
    "cloudfront.net": "AWS CloudFront",
    "akamaized.net": "Akamai CDN",
    "amazon.com": "Amazon",
    "alexa.com": "Amazon Alexa",
    "ring.com": "Ring (Amazon)",
    "nest.com": "Google Nest",
    "philips.com": "Philips",
    "meethue.com": "Philips Hue",
    "tuya.com": "Tuya Cloud",
    "tuyaus.com": "Tuya Cloud",
    "xiaomi.com": "Xiaomi Cloud",
    "apple.com": "Apple iCloud",
    "icloud.com": "Apple iCloud",
    "samsung.com": "Samsung",
    "samsungcloud.com": "Samsung Cloud",
    "sonos.com": "Sonos",
    "tp-link.com": "TP-Link Cloud",
    "tplinkcloud.com": "TP-Link Cloud",
    "roku.com": "Roku",
    "wemo.com": "Belkin Wemo",
    "wyzecam.com": "Wyze Cloud",
    "amazonalexa.com": "Amazon Alexa",
    "fireoscaptiveportal.com": "Amazon",
    "samsungcloudsolution.net": "Samsung Cloud",
    "samsungqbe.com": "Samsung",
    "lifx.com": "LIFX Cloud",
    "io.mi.com": "Xiaomi IoT",
    "miui.com": "Xiaomi",
    "kinesisvideo.us-east-1.amazonaws.com": "AWS Kinesis",
}


@dataclass
class CloudDependencyScore:
    """Cloud dependency analysis result for a single device."""

    device: Device
    dns_profile: DeviceDNSProfile | None
    score: float  # 0-100, higher = more cloud dependent
    query_frequency: float  # queries per minute
    endpoint_diversity: int  # unique cloud endpoints
    cloud_endpoints: dict[str, str]  # domain -> cloud provider
    total_queries: int
    rating: str  # "Low", "Medium", "High", "Critical"
    alternatives: list[Alternative]

    @property
    def cloud_query_ratio(self) -> float:
        """Ratio of queries going to known cloud providers."""
        if self.total_queries == 0:
            return 0.0
        cloud_queries = sum(
            count
            for domain, count in (
                self.dns_profile.endpoints.items() if self.dns_profile else {}
            )
            if domain in CLOUD_PROVIDERS
        )
        return cloud_queries / self.total_queries


def calculate_dependency_score(
    device: Device,
    dns_profile: DeviceDNSProfile | None,
    capture_duration: int = 300,
) -> CloudDependencyScore:
    """Calculate cloud dependency score for a device.

    Score formula (0-100):
    - Query frequency component (0-40): queries/min normalized
    - Endpoint diversity component (0-30): unique cloud endpoints
    - Cloud ratio component (0-30): % of queries to known cloud services
    """
    if dns_profile is None or dns_profile.total_queries == 0:
        return CloudDependencyScore(
            device=device,
            dns_profile=dns_profile,
            score=0.0,
            query_frequency=0.0,
            endpoint_diversity=0,
            cloud_endpoints={},
            total_queries=0,
            rating="Unknown",
            alternatives=get_alternatives(device.manufacturer),
        )

    duration_min = max(capture_duration / 60, 1)
    query_freq = dns_profile.total_queries / duration_min

    # Identify cloud endpoints
    cloud_eps: dict[str, str] = {}
    for domain in dns_profile.endpoints:
        if domain in CLOUD_PROVIDERS:
            cloud_eps[domain] = CLOUD_PROVIDERS[domain]

    endpoint_diversity = len(cloud_eps)

    # Score components
    # Query frequency: log scale, cap at 40
    freq_score = min(40, math.log2(max(query_freq, 1)) * 10)

    # Endpoint diversity: linear, cap at 30
    diversity_score = min(30, endpoint_diversity * 5)

    # Cloud query ratio
    total = dns_profile.total_queries
    cloud_queries = sum(
        dns_profile.endpoints.get(d, 0) for d in cloud_eps
    )
    cloud_ratio = cloud_queries / total if total > 0 else 0
    ratio_score = cloud_ratio * 30

    score = freq_score + diversity_score + ratio_score

    # Rating
    if score >= 75:
        rating = "Critical"
    elif score >= 50:
        rating = "High"
    elif score >= 25:
        rating = "Medium"
    elif score > 0:
        rating = "Low"
    else:
        rating = "Unknown"

    return CloudDependencyScore(
        device=device,
        dns_profile=dns_profile,
        score=round(score, 1),
        query_frequency=round(query_freq, 2),
        endpoint_diversity=endpoint_diversity,
        cloud_endpoints=cloud_eps,
        total_queries=total,
        rating=rating,
        alternatives=get_alternatives(device.manufacturer),
    )


def analyze_network(
    devices: list[Device],
    dns_profiles: dict[str, DeviceDNSProfile],
    capture_duration: int = 300,
) -> list[CloudDependencyScore]:
    """Analyze cloud dependency for all discovered devices."""
    results = []
    for device in devices:
        profile = dns_profiles.get(device.ip)
        score = calculate_dependency_score(device, profile, capture_duration)
        results.append(score)

    # Sort by score descending
    results.sort(key=lambda r: r.score, reverse=True)
    return results
