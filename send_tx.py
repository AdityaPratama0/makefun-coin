#!/usr/bin/env python3
"""send_tx.py: tanda tangani transaksi pump.fun dengan ed25519 lalu kirim lewat RPC.

web3.js menolak menandatangani karena objek kunci beda kelas, jadi tanda tangan
dibuat langsung: baca signature slot, tanda tangani byte pesan, kirim via JSON-RPC.
"""
import base64, json, os, subprocess, sys
import nacl.signing

KP = os.path.expanduser("~/.agent-sessions/makefun-keypair.json")
TXF = "/tmp/pf_tx.json"
RPC = "https://api.mainnet-beta.solana.com"


def load_tx():
    raw = json.load(open(TXF))
    inner = json.loads(raw["text"]) if isinstance(raw, dict) and "text" in raw else raw
    data = inner.get("data") or inner
    return data, base64.b64decode(data["transaction"])


def b58(b: bytes) -> str:
    A = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    n = int.from_bytes(b, "big"); s = ""
    while n:
        n, r = divmod(n, 58); s = A[r] + s
    return "1" * (len(b) - len(b.lstrip(b"\0"))) + s


def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    out = subprocess.run(["curl", "-sS", "-m", "40", "--noproxy", "*", "-X", "POST", RPC,
                          "-H", "Content-Type: application/json", "-d", body],
                         capture_output=True, text=True).stdout
    return json.loads(out)


def main():
    data, blob = load_tx()
    seed = bytes(json.load(open(KP))[:32])
    sk = nacl.signing.SigningKey(seed)
    wallet = b58(bytes(sk.verify_key))

    # format transaksi versi 0: compact-u16 jumlah tanda tangan, lalu 64 byte per tanda tangan
    n = blob[0]
    if n > 8:
        print("jumlah tanda tangan tidak wajar:", n); return 1
    sigs = [bytearray(blob[1 + i * 64: 1 + (i + 1) * 64]) for i in range(n)]
    msg = blob[1 + n * 64:]
    sig = sk.sign(msg).signature
    filled = False
    for i, s in enumerate(sigs):
        if not any(s):
            sigs[i] = bytearray(sig); filled = True; break
    if not filled:
        print("tidak ada slot tanda tangan kosong"); return 1
    out = bytes([n]) + b"".join(bytes(s) for s in sigs) + msg
    b64 = base64.b64encode(out).decode()
    print("wallet", wallet, "| mint", data.get("mintPublicKey"), "| panjang tx", len(out))

    res = rpc("sendTransaction", [b64, {"encoding": "base64", "skipPreflight": False,
                                        "maxRetries": 3, "preflightCommitment": "confirmed"}])
    if "result" not in res:
        print("RPC menolak:", json.dumps(res)[:300]); return 1
    sigstr = res["result"]
    print("terkirim:", sigstr)
    print("https://solscan.io/tx/" + sigstr)
    import time
    for _ in range(10):
        time.sleep(4)
        st = rpc("getSignatureStatuses", [[sigstr], {"searchTransactionHistory": True}])
        v = (st.get("result", {}).get("value") or [None])[0]
        if v and v.get("confirmationStatus"):
            print("status:", v["confirmationStatus"], "err:", v.get("err"))
            break
    return 0


if __name__ == "__main__":
    sys.exit(main())
