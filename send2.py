#!/usr/bin/env python3
"""send2.py: tanda tangani, verifikasi tanda tangan sendiri, kirim, lalu pantau status.

perbedaan dari send_tx.py: tanda tangan diperiksa dulu dengan VerifyKey sebelum dikirim,
dan kalau tidak mendarat dalam 60 detik, transaksi dicoba kirim lagi dengan preflight
aktif supaya pesan errornya terlihat.
"""
import base64, json, os, subprocess, sys, time
import nacl.signing

KP = os.path.expanduser("~/.agent-sessions/makefun-keypair.json")
A = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
RPC = os.environ.get("RPC", "https://api.mainnet-beta.solana.com")


def rpc(method, params):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    out = subprocess.run(["curl", "-sS", "-m", "40", "--noproxy", "*", "-X", "POST", RPC,
                          "-H", "Content-Type: application/json", "-d", body],
                         capture_output=True, text=True).stdout
    try:
        return json.loads(out)
    except Exception:
        return {"raw": out[:200]}


def main():
    raw = json.load(open("/tmp/pf_tx.json"))
    inner = json.loads(raw["text"]) if "text" in raw else raw
    data = inner.get("data") or inner
    blob = bytearray(base64.b64decode(data["transaction"]))
    n = blob[0]
    sig_slots = [blob[1 + i * 64: 1 + (i + 1) * 64] for i in range(n)]
    msg = bytes(blob[1 + n * 64:])

    key = bytes(json.load(open(KP)))
    sk = nacl.signing.SigningKey(key[:32])
    pub = bytes(sk.verify_key)
    sig = sk.sign(msg).signature

    # isi slot kosong dengan tanda tangan kita
    for i, s in enumerate(sig_slots):
        if not any(s):
            blob[1 + i * 64: 1 + (i + 1) * 64] = sig
            print("tanda tangan ditempel di slot", i)
            break

    # verifikasi ulang tiap slot
    off = 1; req = msg[0]; klen = msg[4]; off = 5
    keys = [msg[off + j * 32: off + (j + 1) * 32] for j in range(klen)]
    for i in range(req):
        s = bytes(blob[1 + i * 64: 1 + (i + 1) * 64])
        try:
            nacl.signing.VerifyKey(keys[i]).verify(msg, s)
            print(f"  slot {i} valid")
        except Exception as e:
            print(f"  slot {i} TIDAK valid: {type(e).__name__}")

    b64 = base64.b64encode(bytes(blob)).decode()
    res = rpc("sendTransaction", [b64, {"encoding": "base64", "skipPreflight": False,
                                        "maxRetries": 5, "preflightCommitment": "confirmed"}])
    if "result" not in res:
        print("kirim ditolak:", json.dumps(res)[:400])
        return 1
    sigstr = res["result"]
    print("terkirim:", sigstr)
    print("https://solscan.io/tx/" + sigstr)
    for _ in range(15):
        time.sleep(4)
        st = rpc("getSignatureStatuses", [[sigstr], {"searchTransactionHistory": True}])
        v = (st.get("result", {}).get("value") or [None])[0]
        if v:
            print("status:", v.get("confirmationStatus"), "err:", v.get("err"))
            return 0
    print("setelah 60 detik belum masuk. kirim ulang dengan preflight untuk lihat error:")
    res2 = rpc("sendTransaction", [b64, {"encoding": "base64", "skipPreflight": False,
                                         "maxRetries": 0, "preflightCommitment": "processed"}])
    print(json.dumps(res2)[:400])
    return 1


if __name__ == "__main__":
    sys.exit(main())
