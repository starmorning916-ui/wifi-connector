# Wi-Fi Connector

A Python command-line tool that scans, selects, and connects to Wi-Fi networks on Windows — all without touching the Settings app.

## How It Works

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
