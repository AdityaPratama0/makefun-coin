#!/usr/bin/env python3
"""pf_api.py: panggil API pump.fun dari dalam browser sungguhan.

Cloudflare menolak curl, jadi permintaan dibuat lewat fetch di halaman
pump.fun yang sudah lolos tantangan.
"""
import json, os, sys

HOME = os.path.expanduser("~")
CHROME = os.path.join(HOME, ".cache/ms-playwright/chromium-1208/chrome-linux64/chrome")


def call(body_path):
    body = json.load(open(body_path))
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, executable_path=CHROME,
        proxy={"server": os.environ["MOOPROXY_SERVER"], "username": os.environ["MOOPROXY_USER"],
               "password": os.environ["MOOPROXY_PASS"]})
        ctx = b.new_context(user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"))
        ctx.route("**/*", lambda r: r.abort() if r.request.resource_type in {"image", "media", "font"}
                  else r.continue_())
        pg = ctx.new_page()
        pg.goto("https://fun-block.pump.fun/", wait_until="domcontentloaded", timeout=90000)
        pg.wait_for_timeout(6000)
        out = pg.evaluate(
            """async (body) => {
                 const r = await fetch('/agents/create-coin', {
                   method: 'POST',
                   headers: { 'content-type': 'application/json' },
                   body: JSON.stringify(body),
                 });
                 const t = await r.text();
                 return { status: r.status, text: t.slice(0, 4000) };
               }""", body)
        b.close()
    open("/tmp/pf_tx.json","w").write(json.dumps(out))
    return out


if __name__ == "__main__":
    res = call(sys.argv[1] if len(sys.argv) > 1 else "body.json")
    print(json.dumps(res)[:1500])
