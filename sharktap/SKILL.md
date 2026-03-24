---
name: sharktap
description: SharkTap network monitoring and packet capture tool
model: haiku
color: blue
type: network-monitoring
---

# SharkTap Network Monitoring

## Capabilities
- **Passive Network Monitoring**: Transparent inline tap
- **Packet Capture**: Full packet capture via dual Ethernet ports
- **Traffic Analysis**: Real-time network traffic inspection
- **No Inline Interference**: Does not affect network performance
- **Gigabit Support**: Up to 1 Gbps throughput

## Hardware Info
- **Model**: Hak5 SharkTap
- **Ports**:
  - 2x RJ45 Ethernet (inline tap)
  - 1x USB-C (monitor port)
- **Power**: USB-C powered
- **Compatibility**: Works with Wireshark, tcpdump, NetworkMiner

## Setup

### Physical Connection
```
[Device A] <----> [SharkTap Port 1]
                      |
                 [SharkTap Port 2] <----> [Device B]
                      |
                 [USB-C to Computer]
```

### Capture Setup
```bash
# 1. Connect SharkTap inline between two network devices
# 2. Connect USB-C to monitoring computer
# 3. Identify SharkTap interface
ip link show

# 4. Start capture with tcpdump
sudo tcpdump -i eth_sharktap -w capture.pcap

# 5. Or use Wireshark
sudo wireshark -i eth_sharktap
```

## Common Operations

### 1. Basic Packet Capture
```bash
# Capture all traffic
sudo tcpdump -i eth_sharktap -w full_capture.pcap

# Capture specific protocol
sudo tcpdump -i eth_sharktap 'tcp port 443' -w https_traffic.pcap

# Capture with timestamp
sudo tcpdump -i eth_sharktap -tttt -w timestamped.pcap
```

### 2. Real-time Monitoring
```bash
# Monitor HTTP traffic
sudo tcpdump -i eth_sharktap -A 'tcp port 80'

# Monitor DNS queries
sudo tcpdump -i eth_sharktap -n 'udp port 53'

# Monitor specific host
sudo tcpdump -i eth_sharktap host 192.168.1.100
```

### 3. Traffic Analysis
```bash
# Analyze with tshark
tshark -r capture.pcap -q -z conv,tcp

# Extract HTTP objects
tshark -r capture.pcap --export-objects http,output_dir/

# Protocol hierarchy
tshark -r capture.pcap -q -z io,phs
```

## Use Cases

### 1. Network Troubleshooting
- Monitor traffic between router and device
- Identify connectivity issues
- Analyze packet loss

### 2. Security Monitoring
- Detect suspicious traffic patterns
- Identify unauthorized connections
- Monitor for data exfiltration

### 3. Performance Analysis
- Measure network latency
- Identify bandwidth hogs
- Analyze protocol overhead

## Python Capture Script
See scripts/capture.py for automated packet capture and analysis.

## References
- Wireshark User Guide: https://www.wireshark.org/docs/
- tcpdump manual: references/tcpdump.md
- Capture filters: references/filters.md

## Safety Notes
✅ **PASSIVE MONITORING ONLY**
- SharkTap is a passive tap - does not modify traffic
- Safe for production environments
- No risk of network disruption
- Legal for monitoring your own network traffic
