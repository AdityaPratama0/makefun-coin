#!/usr/bin/env python3
"""logo_png.py: ubah logo.svg jadi logo.png 512x512 memakai chromium yang sudah ada."""
import os
from playwright.sync_api import sync_playwright

CHROME = os.path.expanduser("~/.cache/ms-playwright/chromium-1208/chrome-linux64/chrome")
svg = open("logo.svg").read()

with sync_playwright() as p:
    b = p.chromium.launch(headless=True, executable_path=CHROME)
    pg = b.new_page(viewport={"width": 512, "height": 512}, device_scale_factor=1)
    pg.set_content(f"<html><body style='margin:0'>{svg}</body></html>")
    pg.wait_for_timeout(500)
    pg.screenshot(path="logo.png", clip={"x": 0, "y": 0, "width": 512, "height": 512})
    b.close()
print("logo.png", os.path.getsize("logo.png"), "byte")
