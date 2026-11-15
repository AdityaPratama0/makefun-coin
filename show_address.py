#!/usr/bin/env python3
"""Cetak alamat wallet make.fun dari keypair. Jalankan ini sebelum meminta transfer."""
import json, os

A = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58(b: bytes) -> str:
    n = int.from_bytes(b, "big"); s = ""
    while n:
        n, r = divmod(n, 58); s = A[r] + s
    return "1" * (len(b) - len(b.lstrip(b"\0"))) + s


kp = os.path.expanduser("~/.agent-sessions/makefun-keypair.json")
raw = json.load(open(kp))
print(b58(bytes(raw[32:])))
