# SharkTap Setup Guide

## What is SharkTap?
SharkTap is a passive inline network tap — plugs between target device and its network connection.
All traffic passes through transparently, captured to USB Ethernet interface on analyst laptop.

## Hardware Connection
```
[Target Device]
      |
   [SharkTap]  ← USB-C to analyst laptop
      |
[Network Switch/Router]
```

## Physical Setup
1. Unplug target device's ethernet cable
2. Connect that cable to SharkTap "Network" port
3. Connect SharkTap "Device" port to target device
4. Connect SharkTap USB-C to analyst laptop
5. SharkTap appears as USB Ethernet interface

## Interface Detection

### Linux
```bash
# List interfaces
ip link show
# SharkTap appears as: enx[mac_address] or eth1

# Or check dmesg after plugging in
dmesg | tail -20 | grep -i ethernet

# Bring interface up (no IP needed for capture)
sudo ip link set enx001122334455 up
```

### macOS
```bash
# List interfaces
ifconfig | grep -A 4 "en[0-9]"
# Or
networksetup -listallhardwareports

# SharkTap appears as en2, en3, etc.
# No IP needed, just up state
sudo ifconfig en2 up
```

## No-IP Passive Capture
SharkTap captures at Layer 2 — no IP address needed on capture interface.
This makes it truly passive (target device doesn't know you're there).

```bash
# Linux: capture without IP
sudo tcpdump -i enx001122334455 -w capture.pcap

# macOS: capture without IP
sudo tcpdump -i en2 -w capture.pcap
```

## Promiscuous Mode
```bash
# Linux: enable promiscuous mode
sudo ip link set enx001122334455 promisc on

# Verify
ip link show enx001122334455
# Should show: <BROADCAST,MULTICAST,PROMISC,UP,LOWER_UP>
```

## Wireshark Setup
```bash
# Install
sudo apt install wireshark   # Debian/Ubuntu
brew install wireshark        # macOS

# Run with SharkTap interface
wireshark -i enx001122334455

# Or capture first, analyze later
sudo tcpdump -i enx001122334455 -w /tmp/capture.pcap
wireshark /tmp/capture.pcap
```

## Long-term Monitoring Setup
```bash
# Capture with file rotation (100MB files, keep last 10)
sudo tcpdump -i enx001122334455 \
  -C 100 \
  -W 10 \
  -w /captures/tap_%Y%m%d_%H%M%S.pcap \
  -G 3600

# Monitor disk usage
watch -n 60 'df -h /captures && ls -lh /captures'
```

## Requirements
```bash
# Python script dependencies
pip install watchdog    # For file monitoring features

# System tools needed
sudo apt install tcpdump tshark wireshark-common
```

## Verify Tap is Working
```bash
# Should see traffic immediately after running
sudo tcpdump -i enx001122334455 -c 10 -nn
# If you see packets: tap is working
# If no packets: check cable connections
```

## Troubleshooting
| Problem | Solution |
|---------|----------|
| Interface not detected | Try different USB port, check dmesg |
| No packets captured | Verify cables, check promisc mode |
| Permission denied | Use sudo, or add user to pcap group |
| High CPU usage | Use capture filters to reduce load |
| Disk filling up | Enable file rotation with -C and -W flags |
