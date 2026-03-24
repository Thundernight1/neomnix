# tcpdump Quick Reference

## Basic Capture
```bash
# Capture all traffic on interface
sudo tcpdump -i eth0

# Save to file
sudo tcpdump -i eth0 -w capture.pcap

# Read saved file
tcpdump -r capture.pcap

# Verbose output
sudo tcpdump -i eth0 -v

# Don't resolve hostnames (faster)
sudo tcpdump -i eth0 -n

# Don't resolve ports
sudo tcpdump -i eth0 -nn
```

## Interface Selection
```bash
# List available interfaces
tcpdump -D
ip link show

# Capture on all interfaces
sudo tcpdump -i any
```

## Filters (BPF Syntax)

### By Protocol
```bash
sudo tcpdump -i eth0 tcp
sudo tcpdump -i eth0 udp
sudo tcpdump -i eth0 icmp
sudo tcpdump -i eth0 arp
sudo tcpdump -i eth0 ip6
```

### By Port
```bash
sudo tcpdump -i eth0 port 80
sudo tcpdump -i eth0 port 443
sudo tcpdump -i eth0 'tcp port 80 or tcp port 443'
sudo tcpdump -i eth0 portrange 1024-65535
```

### By Host
```bash
sudo tcpdump -i eth0 host 192.168.1.100
sudo tcpdump -i eth0 src host 10.0.0.1
sudo tcpdump -i eth0 dst host 10.0.0.1
```

### By Network
```bash
sudo tcpdump -i eth0 net 192.168.1.0/24
sudo tcpdump -i eth0 src net 10.0.0.0/8
```

### Combined Filters
```bash
# HTTP from specific host
sudo tcpdump -i eth0 'host 192.168.1.100 and tcp port 80'

# Exclude SSH, capture rest
sudo tcpdump -i eth0 'not port 22'

# DNS only
sudo tcpdump -i eth0 'udp port 53'

# All TCP SYN packets (connection attempts)
sudo tcpdump -i eth0 'tcp[tcpflags] & tcp-syn != 0'

# Large packets (possible data exfil)
sudo tcpdump -i eth0 'greater 1000'
```

## Output Options
```bash
# ASCII output (readable text)
sudo tcpdump -i eth0 -A

# Hex + ASCII
sudo tcpdump -i eth0 -X

# Show ethernet headers
sudo tcpdump -i eth0 -e

# Timestamps
sudo tcpdump -i eth0 -tttt    # Full date/time
sudo tcpdump -i eth0 -ttt     # Delta between packets
```

## Packet Count
```bash
# Capture only 100 packets
sudo tcpdump -i eth0 -c 100

# Rotate capture files (10MB each)
sudo tcpdump -i eth0 -C 10 -w capture.pcap

# Time-based rotation (60 seconds)
sudo tcpdump -i eth0 -G 60 -w capture_%Y%m%d_%H%M%S.pcap
```

## Security-Focused Captures
```bash
# Capture credentials (HTTP POST)
sudo tcpdump -i eth0 -A 'tcp port 80 and (((ip[2:2] - ((ip[0]&0xf)<<2)) - ((tcp[12]&0xf0)>>2)) != 0)'

# Capture DNS to find domains being queried
sudo tcpdump -i eth0 -n 'udp port 53' -A

# Detect port scans (many SYN to different ports)
sudo tcpdump -i eth0 'tcp[tcpflags] == tcp-syn'

# FTP/Telnet cleartext
sudo tcpdump -i eth0 'port 21 or port 23' -A
```
