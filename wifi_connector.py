import os
import subprocess
import tempfile
import time
import sys
import re
from xml.sax.saxutils import escape


def scan_networks():
    """Scan and list all visible Wi-Fi networks."""
    print("\nScanning for available Wi-Fi networks...\n")
    try:
        result = subprocess.run(
            ['netsh', 'wlan', 'show', 'networks', 'mode=bssid'],
            capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Error scanning networks: {e.stderr.strip()}")
        return []

    networks = []
    current = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("SSID") and "BSSID" not in line:
            match = re.match(r"SSID\s+\d+\s*:\s*(.*)", line)
            if match:
                if current.get("ssid"):
                    networks.append(current)
                current = {"ssid": match.group(1).strip()}
        elif line.startswith("Authentication"):
            current["auth"] = line.split(":")[-1].strip()
        elif line.startswith("Signal"):
            current["signal"] = line.split(":")[-1].strip()

    if current.get("ssid"):
        networks.append(current)

    # Remove duplicates (same SSID) keeping strongest signal
    seen = {}
    for net in networks:
        ssid = net["ssid"]
        if ssid and (ssid not in seen):
            seen[ssid] = net
    return list(seen.values())


def display_networks(networks):
    """Display scanned networks in a numbered list."""
    if not networks:
        print("No networks found. Make sure Wi-Fi is enabled.")
        return

    print(f"{'#':<4} {'SSID':<32} {'Signal':<10} {'Security'}")
    print("-" * 65)
    for i, net in enumerate(networks, 1):
        ssid = net.get("ssid", "Unknown")
        signal = net.get("signal", "N/A")
        auth = net.get("auth", "Unknown")
        print(f"{i:<4} {ssid:<32} {signal:<10} {auth}")
    print()


def create_wifi_xml(ssid, password, auth_type="WPA2PSK"):
    """Create a valid Windows WLAN profile XML."""
    if auth_type in ("WPA2PSK", "WPA2-Personal"):
        auth_tag = "WPA2PSK"
    elif auth_type in ("WPA3SAE", "WPA3-Personal"):
        auth_tag = "WPA3SAE"
    else:
        auth_tag = "WPA2PSK"

    safe_ssid = escape(ssid)
    safe_password = escape(password)
    xml_content = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{safe_ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{safe_ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>{auth_tag}</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{safe_password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>
"""
    return xml_content


def create_open_wifi_xml(ssid):
    """Create a WLAN profile XML for an open (no password) network."""
    safe_ssid = escape(ssid)
    xml_content = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{safe_ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{safe_ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>open</authentication>
                <encryption>none</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
        </security>
    </MSM>
</WLANProfile>
"""
    return xml_content


def add_profile(xml_data):
    """Write XML to temp file and add the profile via netsh."""
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=".xml", mode="w", encoding="utf-8"
    ) as f:
        f.write(xml_data)
        temp_path = f.name

    try:
        result = subprocess.run(
            ['netsh', 'wlan', 'add', 'profile', f'filename={temp_path}', 'user=all'],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return False, result.stderr.strip() or result.stdout.strip()
        return True, "Profile added successfully."
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def connect(ssid):
    """Send the connect command for a given SSID."""
    result = subprocess.run(
        ['netsh', 'wlan', 'connect', f'name={ssid}'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        return False, result.stderr.strip() or result.stdout.strip()
    return True, result.stdout.strip()


def check_connection(ssid, timeout=15):
    """Poll the connection state until connected or timeout."""
    print(f"Waiting for connection to '{ssid}'", end="", flush=True)
    for _ in range(timeout):
        time.sleep(1)
        print(".", end="", flush=True)
        try:
            result = subprocess.run(
                ['netsh', 'wlan', 'show', 'interfaces'],
                capture_output=True, text=True, check=True
            )
            output = result.stdout
            if ssid.lower() in output.lower() and "connected" in output.lower():
                state_match = re.search(r"State\s+:\s+(.*)", output)
                if state_match and "connected" in state_match.group(1).lower():
                    print(" Connected!")
                    return True
        except subprocess.CalledProcessError:
            pass
    print(" Timed out.")
    return False


def show_connection_info():
    """Display current connection details and IP address."""
    print("\n--- Connection Info ---")
    try:
        result = subprocess.run(
            ['netsh', 'wlan', 'show', 'interfaces'],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.splitlines():
            line = line.strip()
            if any(line.startswith(prefix) for prefix in
                   ["SSID", "State", "Signal", "Radio type", "Authentication",
                    "Channel", "Receive rate", "Transmit rate"]):
                if not line.startswith("BSSID"):
                    print(f"  {line}")
    except subprocess.CalledProcessError:
        print("  Could not read Wi-Fi interface info.")

    try:
        result = subprocess.run(
            ['ipconfig'], capture_output=True, text=True, check=True
        )
        capture = False
        for line in result.stdout.splitlines():
            if "Wireless" in line or "Wi-Fi" in line or "WLAN" in line:
                capture = True
                print(f"\n  {line.strip()}")
            elif capture:
                if line.strip() == "":
                    break
                print(f"  {line.strip()}")
    except subprocess.CalledProcessError:
        print("  Could not read IP config.")
    print("-" * 30)


def connect_to_wifi(ssid, password, auth_type="WPA2PSK", max_retries=3):
    """Full connection flow with retries."""
    is_open = auth_type.lower() == "open"

    if is_open:
        xml_data = create_open_wifi_xml(ssid)
    else:
        xml_data = create_wifi_xml(ssid, password, auth_type)

    # Add the profile
    ok, msg = add_profile(xml_data)
    if not ok:
        print(f"Failed to add profile: {msg}")
        return False
    print(f"Profile added for '{ssid}'.")

    # Try connecting with retries
    for attempt in range(1, max_retries + 1):
        print(f"\nConnection attempt {attempt}/{max_retries}...")
        ok, msg = connect(ssid)
        if not ok:
            print(f"Connect command failed: {msg}")
            if attempt < max_retries:
                print("Retrying in 3 seconds...")
                time.sleep(3)
            continue

        if check_connection(ssid):
            show_connection_info()
            return True

        if attempt < max_retries:
            print("Connection not established. Retrying in 3 seconds...")
            time.sleep(3)

    print(f"\nFailed to connect to '{ssid}' after {max_retries} attempts.")
    return False


def main():
    # Step 1: Scan for networks
    networks = scan_networks()
    display_networks(networks)

    if not networks:
        sys.exit(1)

    # Step 2: Let user pick a network
    while True:
        choice = input("Enter the number of the network to connect to (or 'q' to quit): ").strip()
        if choice.lower() == 'q':
            print("Exiting.")
            sys.exit(0)
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(networks):
                selected = networks[idx]
                break
            print(f"Please enter a number between 1 and {len(networks)}.")
        except ValueError:
            print("Invalid input. Enter a number.")

    ssid = selected["ssid"]
    auth = selected.get("auth", "WPA2-Personal")
    print(f"\nSelected: {ssid}  (Security: {auth})")

    # Step 3: Get password (skip for open networks)
    if "open" in auth.lower():
        password = ""
        auth_type = "open"
    else:
        password = input("Enter the Wi-Fi password: ").strip()
        if not password:
            print("Password cannot be empty for a secured network.")
            sys.exit(1)
        if "WPA3" in auth.upper():
            auth_type = "WPA3SAE"
        else:
            auth_type = "WPA2PSK"

    # Step 4: Connect
    success = connect_to_wifi(ssid, password, auth_type)
    if success:
        print(f"\nSuccessfully connected to '{ssid}'!")
    else:
        print(f"\nCould not connect to '{ssid}'. Check the password and try again.")


if __name__ == "__main__":
    main()
