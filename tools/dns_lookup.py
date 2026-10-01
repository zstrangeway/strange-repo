"""Ask one DNS server for a name's A records, bypassing every local cache.

No dig on every machine this runs on, and the point is to ask the UDM
itself rather than whatever the OS resolver remembers.

Usage: dns_lookup.py <server> <name>   (prints one IP per line; exit 1 if none)
"""
import os
import socket
import struct
import sys

server, name = sys.argv[1], sys.argv[2]
qid = int.from_bytes(os.urandom(2), "big")
question = b"".join(bytes([len(p)]) + p.encode() for p in name.rstrip(".").split(".")) + b"\0"
query = struct.pack("!HHHHHH", qid, 0x0100, 1, 0, 0, 0) + question + struct.pack("!HH", 1, 1)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.settimeout(3)
sock.sendto(query, (server, 53))
resp, _ = sock.recvfrom(4096)

_, flags, qd, an, _, _ = struct.unpack("!HHHHHH", resp[:12])
pos = 12 + len(question) + 4
ips = []
for _ in range(an):
    pos += 2 if resp[pos] >= 0xC0 else resp.index(b"\0", pos) - pos + 1  # name
    rtype, _, _, rdlen = struct.unpack("!HHIH", resp[pos : pos + 10])
    pos += 10
    if rtype == 1 and rdlen == 4:
        ips.append(socket.inet_ntoa(resp[pos : pos + 4]))
    pos += rdlen
print("\n".join(ips))
sys.exit(0 if ips else 1)
