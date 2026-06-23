# -*- coding: utf-8 -*-
"""
Điền Google Form TỔNG QUÁT theo danh sách trường (bất kỳ form nào).
Mỗi 'item' = {label, type, options, entry, value}. Không gắn cứng form nào.

  fill_and_submit_browser(form_url, items, ...)  # Playwright (trình duyệt thật)
  submit_post(post_url, items)                   # HTTP POST (không trình duyệt)
"""
from __future__ import annotations
import _bootstrap  # temp->D:, .env, sys.path
import time
import unicodedata
from pathlib import Path

SUBMIT_LABELS = ("gửi", "submit")
SHOT_DIR = _bootstrap.SCREENSHOT_DIR


def _nfc(s) -> str:
    return unicodedata.normalize("NFC", s or "")


def _ddmmyyyy_to_iso(s: str) -> str:
    d, m, y = str(s).split("/")
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


# ── Playwright ────────────────────────────────────────────────────────────────
def _click_submit(page) -> None:
    btns = page.get_by_role("button")
    for i in range(btns.count()):
        b = btns.nth(i)
        label = _nfc(b.get_attribute("aria-label") or "") or _nfc(b.inner_text() or "")
        if label.strip().lower() in SUBMIT_LABELS:
            b.click()
            return
    raise RuntimeError("Không tìm thấy nút Gửi/Submit")


def _fill_field(page, item) -> None:
    val = item.get("value")
    if val in (None, ""):
        return
    t, label = item["type"], item["label"]
    if t in ("text", "paragraph"):
        box = page.get_by_role("textbox", name=label, exact=False).first
        box.click()
        box.fill(str(val))
    elif t == "date":
        page.locator('input[type="date"]').first.fill(_ddmmyyyy_to_iso(val))
    elif t in ("radio", "scale"):
        page.get_by_role("radio", name=str(val), exact=True).click()
    elif t == "dropdown":
        page.get_by_role("listbox").first.click()
        page.get_by_role("option", name=str(val), exact=True).click()
    elif t == "checkbox":
        for v in (val if isinstance(val, list) else [val]):
            page.get_by_role("checkbox", name=str(v), exact=True).click()
    else:
        raise ValueError(f"type chưa hỗ trợ: {t} (trường {item.get('entry')})")


def fill_and_submit_browser(form_url: str, items: "list[dict]", *, headless: bool = True,
                            retries: int = 2, shot_dir: Path = SHOT_DIR,
                            channel: str = "chrome", slow_mo: int = 0,
                            shot_name: str = "form") -> dict:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

    shot_dir.mkdir(exist_ok=True)
    last_err = ""
    for attempt in range(1, retries + 1):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=headless, channel=channel, slow_mo=slow_mo)
                page = browser.new_page()
                page.goto(form_url, wait_until="domcontentloaded")
                page.wait_for_selector("div[role='listitem']", timeout=15000)

                for it in items:
                    _fill_field(page, it)
                _click_submit(page)

                page.wait_for_selector("text=/ghi|recorded|response/i", timeout=15000)
                shot = shot_dir / f"{shot_name}_attempt{attempt}.png"
                page.screenshot(path=str(shot), full_page=True)
                browser.close()
                print(f"[OK] {shot_name} (lần {attempt}) -> {shot}")
                return {"ok": True, "screenshot": str(shot), "attempts": attempt, "error": ""}
        except PWTimeout as e:
            last_err = f"Timeout: {e}"
        except Exception as e:
            last_err = str(e)
        print(f"[RETRY] {shot_name} lần {attempt} lỗi: {last_err}")
        time.sleep(2 * attempt)
    return {"ok": False, "screenshot": "", "attempts": retries, "error": last_err}


# ── HTTP POST (không trình duyệt) ─────────────────────────────────────────────
def submit_post(post_url: str, items: "list[dict]") -> bool:
    import requests
    payload: dict = {}
    for it in items:
        val = it.get("value")
        if val in (None, ""):
            continue
        if it["type"] == "date":
            d, m, y = str(val).split("/")
            payload[f"{it['entry']}_day"] = int(d)
            payload[f"{it['entry']}_month"] = int(m)
            payload[f"{it['entry']}_year"] = int(y)
        elif it["type"] == "checkbox" and isinstance(val, list):
            payload[it["entry"]] = val
        else:
            payload[it["entry"]] = str(val)
    r = requests.post(post_url, data=payload, timeout=15)
    ok = r.status_code in (200, 302)
    print(f"[{'OK' if ok else 'FAIL'}] POST -> HTTP {r.status_code}")
    return ok
