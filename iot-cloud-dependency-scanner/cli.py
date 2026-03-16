"""IoT Cloud Dependency Scanner — CLI entry point.

Usage:
    uv run cli.py scan                  # Full scan (requires root)
    uv run cli.py scan --demo           # Demo mode with mock data
    uv run cli.py capture               # DNS capture only (requires root)
    uv run cli.py report                # Generate report from last scan
    uv run cli.py run                   # Full workflow: scan → capture → report
    uv run cli.py run --demo            # Full workflow with demo data
"""

import argparse
import json
import os
import sys
import time

from scanner import Device, scan_network
from dns_capture import capture_dns, DeviceDNSProfile
from analyzer import analyze_network, CloudDependencyScore
from report import print_cli_report, generate_html_report
from demo_data import generate_demo_devices, generate_demo_dns_profiles


DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def save_devices(devices: list[Device]):
    ensure_data_dir()
    data = []
    for d in devices:
        data.append({
            "ip": d.ip,
            "mac": d.mac,
            "manufacturer": d.manufacturer,
            "hostname": d.hostname,
            "mdns_services": d.mdns_services,
            "ssdp_info": d.ssdp_info,
        })
    with open(os.path.join(DATA_DIR, "devices.json"), "w") as f:
        json.dump(data, f, indent=2)


def load_devices() -> list[Device]:
    path = os.path.join(DATA_DIR, "devices.json")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = json.load(f)
    return [
        Device(
            ip=d["ip"],
            mac=d["mac"],
            manufacturer=d["manufacturer"],
            hostname=d.get("hostname", ""),
            mdns_services=d.get("mdns_services", []),
            ssdp_info=d.get("ssdp_info", ""),
        )
        for d in data
    ]


def save_dns_profiles(profiles: dict[str, DeviceDNSProfile]):
    ensure_data_dir()
    data = {}
    for ip, profile in profiles.items():
        data[ip] = {
            "ip": profile.ip,
            "total_queries": profile.total_queries,
            "endpoints": profile.endpoints,
        }
    with open(os.path.join(DATA_DIR, "dns_profiles.json"), "w") as f:
        json.dump(data, f, indent=2)


def load_dns_profiles() -> dict[str, DeviceDNSProfile]:
    path = os.path.join(DATA_DIR, "dns_profiles.json")
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = json.load(f)
    profiles = {}
    for ip, d in data.items():
        profile = DeviceDNSProfile(ip=d["ip"])
        profile.endpoints = d["endpoints"]
        profile.total_queries = d.get("total_queries", sum(d["endpoints"].values()))
        profiles[ip] = profile
    return profiles


def cmd_scan(args):
    """Scan network for IoT devices."""
    if args.demo:
        print("[DEMO] Using simulated device data...")
        devices = generate_demo_devices()
        print(f"[DEMO] Generated {len(devices)} demo devices")
    else:
        devices = scan_network(
            interface=args.interface,
            network=args.network,
        )

    save_devices(devices)
    print(f"\n[*] {len(devices)} devices saved to {DATA_DIR}/devices.json")

    print("\n  Discovered Devices:")
    print("  " + "-" * 60)
    for d in devices:
        name = d.hostname or d.ip
        print(f"  {name:<30} {d.manufacturer:<15} {d.mac}")
    print()

    return devices


def cmd_capture(args):
    """Capture DNS traffic."""
    devices = load_devices()
    if not devices:
        print("[!] No devices found. Run 'scan' first.")
        return {}

    device_ips = [d.ip for d in devices]

    if args.demo:
        print("[DEMO] Using simulated DNS data...")
        profiles = generate_demo_dns_profiles()
        print(f"[DEMO] Generated DNS profiles for {len(profiles)} devices")
    else:
        profiles = capture_dns(
            interface=args.interface,
            duration=args.duration,
            device_ips=device_ips,
        )

    save_dns_profiles(profiles)
    print(f"[*] DNS profiles saved to {DATA_DIR}/dns_profiles.json")
    return profiles


def cmd_report(args):
    """Generate report from saved data."""
    devices = load_devices()
    profiles = load_dns_profiles()

    if not devices:
        print("[!] No scan data found. Run 'scan' first.")
        return

    duration = getattr(args, "duration", 300)
    results = analyze_network(devices, profiles, duration)

    # CLI report
    print_cli_report(results)

    # HTML report
    output = args.output if hasattr(args, "output") else "report.html"
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), output
    )
    generate_html_report(results, output_path)
    print(f"\n[*] HTML report saved to: {output_path}")


def cmd_run(args):
    """Full workflow: scan → capture → report."""
    print("=" * 50)
    print("  IoT Cloud Dependency Scanner")
    print("  Full Workflow: scan → capture → report")
    print("=" * 50)

    print("\n--- Step 1/3: Network Scan ---")
    devices = cmd_scan(args)

    print("\n--- Step 2/3: DNS Capture ---")
    cmd_capture(args)

    print("\n--- Step 3/3: Analysis & Report ---")
    cmd_report(args)

    print("\n[*] Workflow complete!")


def main():
    parser = argparse.ArgumentParser(
        description="IoT Cloud Dependency Scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Common args
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--demo", action="store_true", help="Use demo/mock data"
    )
    common.add_argument(
        "--interface", "-i", default="eth0", help="Network interface (default: eth0)"
    )
    common.add_argument(
        "--network", "-n", default="192.168.1.0/24",
        help="Network CIDR to scan (default: 192.168.1.0/24)",
    )

    # scan
    sub_scan = subparsers.add_parser("scan", parents=[common], help="Scan network")

    # capture
    sub_capture = subparsers.add_parser("capture", parents=[common], help="Capture DNS")
    sub_capture.add_argument(
        "--duration", "-d", type=int, default=300,
        help="Capture duration in seconds (default: 300)",
    )

    # report
    sub_report = subparsers.add_parser("report", parents=[common], help="Generate report")
    sub_report.add_argument(
        "--output", "-o", default="report.html", help="Output HTML file"
    )
    sub_report.add_argument(
        "--duration", "-d", type=int, default=300,
        help="Original capture duration for scoring (default: 300)",
    )

    # run (full workflow)
    sub_run = subparsers.add_parser("run", parents=[common], help="Full workflow")
    sub_run.add_argument(
        "--duration", "-d", type=int, default=300,
        help="DNS capture duration in seconds (default: 300)",
    )
    sub_run.add_argument(
        "--output", "-o", default="report.html", help="Output HTML file"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "scan": cmd_scan,
        "capture": cmd_capture,
        "report": cmd_report,
        "run": cmd_run,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
