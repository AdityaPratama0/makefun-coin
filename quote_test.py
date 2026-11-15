#!/usr/bin/env python3
"""quote_test.py: buka halaman tukar XMR->SOL dan masukkan 0,00359 XMR untuk melihat minimum nyata."""
import os, re, sys
from playwright.sync_api import sync_playwright

CHROME = os.path.expanduser("~/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome")
PROXY = {"server": os.environ["MOOPROXY_SERVER"], "username": os.environ["MOOPROXY_USER"],
         "password": os.environ["MOOPROXY_PASS"]}
URL = sys.argv[1] if len(sys.argv) > 1 else "https://rabbit.io/XMR/SOL"
AMOUNT = sys.argv[2] if len(sys.argv) > 2 else "0.00359"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, executable_path=CHROME)
    ctx = b.new_context(user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"))
    pg = ctx.new_page()
    pg.goto(URL, wait_until="domcontentloaded", timeout=90000)
    pg.wait_for_timeout(6000)
    # cari input pertama dan isi
    filled = False
    for sel in ("input[inputmode='decimal']", "input[type='text']", "input"):
        loc = pg.locator(sel)
        if loc.count():
            try:
                loc.first.click(); loc.first.fill(AMOUNT); filled = True; break
            except Exception:
                continue
    pg.wait_for_timeout(6000)
    txt = pg.inner_text("body")
    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    keep = [l for l in lines if re.search(r"(min|minimum|too small|least|0\.0\d+|SOL|XMR|amount)", l, re.I)][:25]
    print("terisi:", filled)
    print("\n".join(keep)[:1600])
    b.close()
