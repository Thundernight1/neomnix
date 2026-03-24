# BPF Capture Filters Reference

## Syntax Structure
```
[qualifier] [value]
[expr1] and/or/not [expr2]
```

## Protocol Filters
| Filter | Captures |
|--------|----------|
| `tcp` | TCP traffic |
| `udp` | UDP traffic |
| `icmp` | ICMP/ping |
| `arp` | ARP requests/replies |
| `ip` | All IPv4 |
| `ip6` | All IPv6 |
| `not arp` | Everything except ARP |

## Port Filters
| Filter | Captures |
|--------|----------|
| `port 80` | HTTP |
| `port 443` | HTTPS |
| `port 22` | SSH |
| `port 53` | DNS |
| `port 25` | SMTP |
| `port 3306` | MySQL |
| `port 5432` | PostgreSQL |
| `port 27017` | MongoDB |
| `portrange 1-1023` | Well-known ports |
| `not port 22` | Exclude SSH |

## Host Filters
| Filter | Captures |
|--------|----------|
| `host 1.2.3.4` | To or from IP |
| `src host 1.2.3.4` | From IP only |
| `dst host 1.2.3.4` | To IP only |
| `net 192.168.0.0/16` | Entire subnet |

## TCP Flags
```bash
# SYN (connection initiation)
tcp[tcpflags] & tcp-syn != 0

# SYN-ACK (connection acceptance)
tcp[tcpflags] == (tcp-syn|tcp-ack)

# RST (connection reset)
tcp[tcpflags] & tcp-rst != 0

# FIN (connection close)
tcp[tcpflags] & tcp-fin != 0

# Only ACK
tcp[tcpflags] == tcp-ack
```

## Payload Filters
```bash
# HTTP GET requests
tcp[((tcp[12:1] & 0xf0) >> 2):4] = 0x47455420

# HTTP POST requests
tcp[((tcp[12:1] & 0xf0) >> 2):4] = 0x504f5354

# DNS queries (byte matching)
udp[10] & 0x80 = 0
```

## Size Filters
```bash
greater 1000    # Packets > 1000 bytes
less 64         # Packets < 64 bytes
len >= 500      # Packet length >= 500
```

## Complex Examples
```bash
# HTTP traffic not to localhost
'tcp port 80 and not host 127.0.0.1'

# Non-local DNS
'udp port 53 and not src net 192.168.0.0/24'

# HTTPS from specific subnet
'tcp port 443 and src net 10.0.0.0/8'

# All traffic except established SSH sessions
'not (tcp port 22 and tcp[tcpflags] == tcp-ack)'

# Find potential data exfiltration (large outbound packets)
'src net 192.168.0.0/16 and greater 1400'

# Broadcast/multicast traffic
'broadcast or multicast'

# VLAN tagged traffic
'vlan'
```

## Wireshark Display Filters (different syntax)
```
# HTTP only
http

# Specific IP
ip.addr == 192.168.1.100

# TCP stream containing "password"
tcp contains "password"

# DNS queries
dns.flags.response == 0

# Large HTTP responses
http.response and frame.len > 10000

# TLS handshakes
ssl.record.content_type == 22
```
