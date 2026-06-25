# -*- coding: utf-8 -*-
"""
ĐÍCH = TRANG WEB BẤT KỲ (không phải Google Form). Soi DOM thật bằng Playwright lấy các
ô nhập (input/select/textarea) → điền theo selector. Khác inspect_form (chỉ đọc được
Google Form qua FB_PUBLIC_LOAD_DATA_).

  inspect_web(url)            -> [ {label, type, entry=selector, options} ]  (dùng làm schema)
  fill_web(url, items, ...)   -> {ok, filled, screenshot}

LƯU Ý: KHÔNG vượt được captcha (reCAPTCHA…). Trang có captcha thì chỉ ĐIỀN, để người
tự giải captcha + bấm nút (dùng headed + keep_open_secs).
"""
from __future__ import annotations
import _bootstrap  # .env, temp->D:, sys.path
import re

SKIP_IDS = ("g-recaptcha-response",)        # ô captcha — bỏ qua

_INSPECT_JS = r"""
() => {
  const cssId = el => (window.CSS && CSS.escape) ? CSS.escape(el.id) : el.id;
  const sel = el => el.id ? ('#'+cssId(el)) : (el.name ? (el.tagName.toLowerCase()+"[name='"+el.name+"']") : null);
  const labelOf = el => {
    if (el.getAttribute('aria-label')) return el.getAttribute('aria-label').trim();
    if (el.placeholder) return el.placeholder.trim();
    if (el.id){ const l=document.querySelector("label[for='"+cssId(el)+"']"); if(l) return l.innerText.trim(); }
    const p = el.closest('div,td,li,p'); return p ? p.innerText.trim().slice(0,60) : '';
  };
  const out=[];
  document.querySelectorAll('input,select,textarea').forEach(el=>{
    const tag=el.tagName.toLowerCase();
    const type=(el.type||tag).toLowerCase();
    if (['hidden','submit','button','reset','image','file'].includes(type)) return;
    const s=sel(el); if(!s) return;
    let kind='text';
    if (tag==='textarea') kind='paragraph';
    else if (tag==='select') kind='dropdown';
    else if (type==='checkbox') kind='checkbox';
    else if (type==='radio') kind='radio';
    else if (type==='date') kind='date';
    let options=null;
    if (tag==='select') options=[...el.options].map(o=>o.text.trim()).filter(Boolean);
    out.push({selector:s, id:el.id||'', name:el.name||'', label:labelOf(el), type:kind, options});
  });
  return out;
}
"""


def _fields_from_raw(raw: list) -> list:
    fields, seen = [], set()
    for r in raw:
        if r["id"] in SKIP_IDS or r["selector"] in seen:
            continue
        seen.add(r["selector"])
        fields.append({
            "label": r["label"] or r["name"] or r["selector"],
            "type": r["type"],
            "entry": r["selector"],          # _fid dùng 'entry' làm khoá
            "options": r["options"],
        })
    return fields


def inspect_web(url: str, *, headless: bool = True, timeout: int = 30000) -> list:
    """Soi 1 trang web → danh sách ô nhập (làm schema cho OCR/điền)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=headless, channel="chrome")
        pg = b.new_page()
        pg.goto(url, wait_until="domcontentloaded", timeout=timeout)
        pg.wait_for_timeout(2000)
        raw = pg.evaluate(_INSPECT_JS)
        b.close()
    return _fields_from_raw(raw)


def fill_web(url: str, items: list, *, headless: bool = False, submit: bool = False,
             submit_text: str = "Tra cứu", keep_open_secs: int = 0,
             shot_dir=None) -> dict:
    """Điền các item (đã có 'value') vào trang web theo selector ('entry').
    submit=False (mặc định): chỉ điền, KHÔNG bấm nút (để người giải captcha). """
    from playwright.sync_api import sync_playwright
    shot_dir = shot_dir or _bootstrap.SCREENSHOT_DIR
    shot_dir.mkdir(exist_ok=True)
    filled = {}
    with sync_playwright() as p:
        b = p.chromium.launch(headless=headless, channel="chrome")
        pg = b.new_page()
        pg.goto(url, wait_until="domcontentloaded", timeout=30000)
        pg.wait_for_timeout(2000)
        for it in items:
            v = it.get("value")
            if v in (None, "", []):
                continue
            sel, t = it["entry"], it["type"]
            try:
                loc = pg.locator(sel).first
                if t in ("text", "paragraph", "date"):
                    loc.fill(str(v))
                elif t == "dropdown":
                    loc.select_option(label=str(v))
                elif t == "checkbox":
                    loc.check()
                elif t == "radio":
                    pg.locator(f"{sel}[value='{v}']").first.check()
                try:
                    got = loc.input_value()
                except Exception:
                    got = str(v)
                filled[sel] = got
                print(f"  • {it['label'][:32]:<32} = {got!r}")
            except Exception as e:
                print(f"  • {it['label'][:32]:<32} ⛔ {str(e)[:60]}")
        path = shot_dir / "web_fill.png"
        pg.screenshot(path=str(path), full_page=True)
        if submit:
            try:
                pg.get_by_role("button", name=re.compile(submit_text, re.I)).first.click()
                print(f"  ▶️  đã bấm '{submit_text}'")
            except Exception as e:
                print(f"  ⚠️  không bấm được nút '{submit_text}': {str(e)[:50]}")
        if keep_open_secs:
            print(f"  ⏳ giữ trình duyệt {keep_open_secs}s (tự giải captcha + bấm nút)...")
            pg.wait_for_timeout(keep_open_secs * 1000)
        b.close()
    return {"ok": bool(filled), "filled": filled, "screenshot": str(path)}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Dùng: py -3.11 web_target.py <URL>   (soi DOM, in các ô)")
        raise SystemExit(1)
    for f in inspect_web(sys.argv[1]):
        opt = f"  options={f['options']}" if f.get("options") else ""
        print(f"  [{f['type']:<9}] {f['entry']:<28} {f['label'][:40]!r}{opt}")
