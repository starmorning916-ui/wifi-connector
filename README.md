# Wi-Fi Security Toolkit

A Python penetration testing toolkit for Windows that scans Wi-Fi networks and cracks WPA2 passwords using dictionary attacks. Includes network reconnaissance and handshake capture automation.

## Files

- `wifi_connector.py` — Scan and connect to known networks (quick connection utility)
- `wifi_cracker.py` — WPA2 handshake capture and password cracking (pentesting)
- `README.md` — This file

---

## Part 1: Wi-Fi Connector (Quick Connect)

A Python command-line tool that scans, selects, and connects to Wi-Fi networks on Windows — all without touching the Settings app.

### How It Works

The script uses Windows' built-in `netsh` command-line utility under the hood:

1. **Scan** — Runs `netsh wlan show networks` to discover all nearby Wi-Fi networks and displays them in a table with signal strength and security type.
2. **Select** — The user picks a network by number from the list.
3. **Profile Creation** — Generates a valid Windows WLAN XML profile file containing the SSID, security type (WPA2/WPA3/Open), and password. This is the same format Windows uses internally to store saved networks.
4. **Profile Installation** — Loads the XML profile into Windows via `netsh wlan add profile`, registering it as a known network.
5. **Connect** — Sends `netsh wlan connect name=<SSID>` to initiate the connection.
6. **Verify** — Polls `netsh wlan show interfaces` every second (up to 15s) to confirm the connection succeeded.
7. **Display** — Shows connection details (signal, speed, channel) and IP address via `ipconfig`.

If a connection attempt fails, it automatically retries up to 3 times with a 3-second delay between attempts.

## Requirements

- **Windows 10/11**
- **Python 3.6+**
- **Administrator privileges** (required by `netsh` to add Wi-Fi profiles)
- **Wi-Fi adapter** enabled and target network in range

## Usage

1. Open Command Prompt or PowerShell **as Administrator**
2. Run the script:

```
python wifi_connector.py
```

3. Pick a network from the scanned list
4. Enter the password
5. The script connects and shows your connection info

## Supported Network Types

| Security Type  | Supported |
|---------------|-----------|
| WPA2-PSK      | Yes       |
| WPA3-Personal | Yes       |
| Open (no password) | Yes  |
| WPA2-Enterprise (802.1X) | No |

## Example Output

```
Scanning for available Wi-Fi networks...

#    SSID                             Signal     Security
-----------------------------------------------------------------
1    HomeNetwork                      95%        WPA2-Personal
2    Neighbor_5G                      60%        WPA2-Personal
3    CoffeeShop_Free                  40%        Open

Enter the number of the network to connect to (or 'q' to quit): 1
Enter the Wi-Fi password: ********

Connection attempt 1/3...
Waiting for connection to 'HomeNetwork'......... Connected!

--- Connection Info ---
  SSID           : HomeNetwork
  State          : connected
  Signal         : 95%
  Channel        : 6
  Receive rate (Mbps) : 144
------------------------------

Successfully connected to 'HomeNetwork'!
```

## Project Structure

```
wifi_connector/
├── wifi_connector.py    # Main script
└── README.md            # This file
```

## How the XML Profile Works

Windows stores Wi-Fi credentials as XML files. The script dynamically generates one like this:

```xml
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>NetworkName</name>
    <SSIDConfig>
        <SSID><name>NetworkName</name></SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <keyMaterial>YourPassword</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>
```

The XML is written to a temporary file, loaded by `netsh`, and immediately deleted so the plain-text password doesn't persist on disk.

---

## Part 2: Wi-Fi Cracker (WPA2 Pentesting)

Automated WPA2 password cracking tool for authorized penetration testing. Captures handshakes and performs dictionary/GPU-accelerated attacks.

### How It Works

1. **Network Scan** — Lists all nearby Wi-Fi networks with SSID, BSSID, and security type
2. **Handshake Capture** — Uses `airodump-ng` to capture WPA4-way handshake (requires deauth)
3. **Dictionary Attack** — Compares captured handshake against wordlist passwords
4. **Password Cracking** — If match found, extracts and displays the password
5. **GPU Acceleration** — Uses hashcat for 10-50x faster cracking (optional, requires GPU)

### Speed Comparison

| Method | Speed | Hardware Required |
|--------|-------|------------------|
| aircrack-ng (CPU) | ~10K passwords/sec | CPU |
| hashcat (GPU) | ~1M passwords/sec | NVIDIA/AMD GPU |
| Dictionary (rockyou.txt) | Depends on position | Varies |

### Installation (Required)

#### 1. Npcap (Packet Capture)
```
Download: https://npcap.com/download.html
- Install "Npcap 1.x" (latest version)
- ✓ Enable "WinPcap API compatibility"
- Restart after install
```

#### 2. aircrack-ng for Windows
```
Download: https://www.aircrack-ng.org/download.html
- Get the latest Windows binary
- Extract to C:\aircrack-ng\ or add to PATH
- Verify: Open CMD and type "aircrack-ng"
```

#### 3. (Optional but MUCH faster) hashcat
```
Download: https://hashcat.net/hashcat/
- Extract to C:\hashcat\
- Requires NVIDIA/AMD GPU for acceleration
- Works 10-50x faster than CPU method
```

#### 4. Wordlist (Password Dictionary)
```
Download rockyou.txt (14.3 million common passwords):
https://github.com/brannondorsey/naive-hashcat/releases/download/data/rockyou.txt
- Save to same folder as script, or note the path
```

### Usage

```bash
python wifi_cracker.py
```

**Workflow:**
1. Script scans and lists all nearby networks
2. You select target network by number
3. (If handshake not captured) Script captures WPA handshake
   - Requires monitor mode (may need special adapter on Windows)
   - Or provide path to pre-captured .cap file
4. Script attempts dictionary crack against handshake
5. If match found → password displayed

### Example Output

```
=============================================================================
Wi-Fi WPA2 Cracker for Windows (Authorized Penetration Testing Only)
=============================================================================

[*] Checking for required tools...
[+] aircrack-ng found: C:\aircrack-ng\aircrack-ng.exe
[+] hashcat found (GPU acceleration available): C:\hashcat\hashcat.exe

#   SSID                           BSSID              Security
---------------------------------------------------------------------------
1   TestNetwork_5G                 AA:BB:CC:DD:EE:FF  WPA2-Personal
2   GuestWiFi                      11:22:33:44:55:66  WPA2-Personal

Enter network number to crack (or 'q' to quit): 1

[*] Target: TestNetwork_5G (AA:BB:CC:DD:EE:FF)
[*] Security: WPA2-Personal

Path to .cap handshake file: capture.cap

[*] Starting GPU-accelerated attack with hashcat...

[+] PASSWORD FOUND: MyPassword123
```

### Windows Monitor Mode Challenges

On Windows, monitor mode (required to capture handshakes) has limitations:

**Option 1: USB Wi-Fi Adapter (Recommended)**
- Get: Alfa AWUS036ACH, TP-Link TL-WN722N, or similar
- Supports monitor mode on Windows with proper drivers
- ~$30-50

**Option 2: Linux USB / WSL2**
- Run aircrack-ng in Linux subsystem
- More reliable for handshake capture
- Requires Linux setup

**Option 3: Pre-captured Handshake**
- If provided by competition, skip capture step
- Go straight to cracking phase

### Optimization Tips for Competitions

**Speed up cracking:**
1. Use hashcat (GPU) instead of aircrack-ng (CPU)
   - 10-50x faster depending on GPU
2. Use smaller wordlist focused on common passwords
   - Top 1M passwords: https://github.com/danielmiessler/SecLists
3. Start with 8-character passwords (statistically most common)
4. Use GPU with high VRAM (RTX 3080+) for fastest results

**Example competition workflow:**
```bash
# 1. Provide .cap file directly
python wifi_cracker.py
# Select network → Use .cap file → Auto-crack with hashcat
# Total time: 5-30 seconds (vs minutes with dictionary)
```

### Disclaimer

This tool is for **authorized penetration testing only**:
- Obtain written permission before testing any network
- Illegal to crack networks without authorization
- Designed for security professionals and sanctioned competitions
- Only use on networks you own or have explicit permission to test
