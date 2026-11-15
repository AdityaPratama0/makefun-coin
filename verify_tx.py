#!/usr/bin/env python3
"""verify_tx.py: periksa apakah tanda tangan di transaksi pump.fun valid.

Kalau tanda tangan milik server (mint) tidak valid, transaksi tidak mungkin mendarat,
dan jalan keluarnya adalah membangun transaksi sendiri dengan SDK resmi.
"""
import base64, json, sys
import nacl.signing

A = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def b58e(b: bytes) -> str:
    n = int.from_bytes(b, "big"); s = ""
    while n:
        n, r = divmod(n, 58); s = A[r] + s
    return "1" * (len(b) - len(b.lstrip(b"\0"))) + s


def b58d(s: str) -> bytes:
    n = 0
    for ch in s:
        n = n * 58 + A.index(ch)
    return n.to_bytes((n.bit_length() + 7) // 8, "big")


def main(path="/tmp/pf_tx.json"):
    raw = json.load(open(path))
    inner = json.loads(raw["text"]) if isinstance(raw, dict) and "text" in raw else raw
    data = inner.get("data") or inner
    blob = base64.b64decode(data["transaction"])
    n = blob[0]
    sigs = [blob[1 + i * 64: 1 + (i + 1) * 64] for i in range(n)]
    msg = blob[1 + n * 64:]

    # baca static account keys dari header pesan versi 0
    # layout: [prefix 0x80] numRequiredSignatures, numReadonlySigned, numReadonlyUnsigned, lalu shortvec jumlah kunci
    off = 1
    req = msg[off]; off += 3
    klen = msg[off]; off += 1
    keys = []
    for _ in range(klen):
        keys.append(msg[off:off + 32]); off += 32

    print(f"mint dari API: {data.get('mintPublicKey')}")
    for i in range(min(req, len(keys))):
        pub = keys[i]
        addr = b58e(pub)
        filled = any(sigs[i])
        ok = False
        if filled:
            try:
                nacl.signing.VerifyKey(pub).verify(msg, sigs[i])
                ok = True
            except Exception:
                ok = False
        print(f"  slot {i} {addr} terisi={filled} tanda tangan_valid={ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
