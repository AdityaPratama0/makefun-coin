#!/usr/bin/env python3
"""launch_fast.py: ambil transaksi pump.fun, tanda tangani, dan kirim dalam SATU proses.

Masalah sebelumnya: transaksi dibuat lewat API lalu dikirim dari proses terpisah,
dan blockhash-nya sudah kedaluwarsa saat dikirim (BlockhashNotFound).
Di sini jeda antara build dan kirim dijaga di bawah 10 detik.
"""
import base64, json, os, subprocess, sys, time
import nacl.signing
from playwright.sync_api import sync_playwright

HOME = os.path.expanduser("~")
CHROME = os.path.join(HOME, ".cache/ms-playwright/chromium-1208/chrome-linux64/chrome")
PROXY = {"server": os.environ["MOOPROXY_SERVER"], "username": os.environ["MOOPROXY_USER"],
         "password": os.environ["MOOPROXY_PASS"]}
KP = os.path.join(HOME, ".agent-sessions", "makefun-keypair.json")
RPC = "https://api.mainnet-beta.solana.com"
API = "https://fun-block.pump.fun/agents/create-coin"


def b58(b: bytes) -> str:
    A = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    n = int.from_bytes(b, "big"); s = ""
    while n:
        n, r = divmod(n, 58); s = A[r] + s
    return "1" * (len(b) - len(b.lstrip(b"\0"))) + s


def rpc(method, params, timeout=40):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    out = subprocess.run(["curl", "-sS", "-m", str(timeout), "--noproxy", "*", "-X", "POST", RPC,
                          "-H", "Content-Type: application/json", "-d", body],
                         capture_output=True, text=True).stdout
    try:
        return json.loads(out)
    except Exception:
        return {"raw": out[:200]}


def main(send=False):
    key = bytes(json.load(open(KP)))
    sk = nacl.signing.SigningKey(key[:32])
    pub = bytes(sk.verify_key)
    wallet = b58(pub)

    body = {
        "user": wallet,
        "name": os.environ.get("COIN_NAME", "Make Fun"),
        "symbol": os.environ.get("COIN_SYMBOL", "MAKEFUN"),
        "uri": os.environ.get("COIN_URI", ""),
        "solLamports": os.environ.get("COIN_BUY_LAMPORTS", "1000000"),
        "encoding": "base64",
        "feePayer": wallet,
        "creator": wallet,
    }
    if not body["uri"]:
        print("COIN_URI kosong"); return 2

    t0 = time.time()
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, executable_path=CHROME, proxy=PROXY)
        ctx = b.new_context(user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                       "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"))
        pg = ctx.new_page()
        pg.goto("https://fun-block.pump.fun/", wait_until="domcontentloaded", timeout=90000)
        pg.wait_for_timeout(3000)
        out = pg.evaluate("""async (body) => {
              const r = await fetch('/agents/create-coin', {
                method: 'POST', headers: { 'content-type': 'application/json' },
                body: JSON.stringify(body) });
              const t = await r.text();
              return { status: r.status, text: t };
            }""", body)
        b.close()
    print(f"API dijawab dalam {time.time()-t0:.1f}s, status {out['status']}")
    inner = json.loads(out["text"])
    data = inner.get("data") or inner
    if not data.get("transaction"):
        print("tidak ada transaksi:", str(inner)[:300]); return 1
    print("mint:", data.get("mintPublicKey"))

    blob = bytearray(base64.b64decode(data["transaction"]))
    n = blob[0]
    msg = bytes(blob[1 + n * 64:])
    sig = sk.sign(msg).signature
    for i in range(n):
        if not any(blob[1 + i * 64: 1 + (i + 1) * 64]):
            blob[1 + i * 64: 1 + (i + 1) * 64] = sig
            print("tanda tangan wallet di slot", i)
            break
    b64 = base64.b64encode(bytes(blob)).decode()
    print(f"jeda build->kirim: {time.time()-t0:.1f}s")

    if not send:
        print("mode kering: transaksi siap, tidak dikirim")
        return 0

    res = rpc("sendTransaction", [b64, {"encoding": "base64", "skipPreflight": False,
                                        "maxRetries": 5, "preflightCommitment": "confirmed"}])
    if "result" not in res:
        print("ditolak:", json.dumps(res)[:300]); return 1
    sigstr = res["result"]
    print("terkirim:", sigstr)
    print("https://solscan.io/tx/" + sigstr)
    for _ in range(12):
        time.sleep(4)
        st = rpc("getSignatureStatuses", [[sigstr], {"searchTransactionHistory": True}])
        v = (st.get("result", {}).get("value") or [None])[0]
        if v:
            print("status:", v.get("confirmationStatus"), "| err:", v.get("err"))
            return 0
    print("belum mendarat dalam 48 detik")
    return 1


if __name__ == "__main__":
    sys.exit(main("--send" in sys.argv))
