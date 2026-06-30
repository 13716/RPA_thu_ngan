# -*- coding: utf-8 -*-
"""
KỊCH BẢN khám bệnh (orchestrator) — chain 3 mảnh đã có:
  B1. OCR ảnh/PDF bệnh nhân  -> trích trường + SUY LUẬN BHYT còn hạn (theo ngày hôm nay)
  B2. (tuỳ) kiểm BHYT trên FORM WEB baohiemxahoi.gov.vn  -> điền sẵn, NGƯỜI giải captcha + đọc kết quả
  B3. Mở OH (mock) điền thông tin bệnh nhân

Chạy:
  py -3.11 scenario_kham_benh.py --doc "...\\cccd.jpg"            # B1 + B3 (BHYT suy luận tự động)
  py -3.11 scenario_kham_benh.py --doc "...\\cccd.jpg" --bhyt-web # thêm B2 (mở web, bạn giải captcha)
  thêm --no-oh để bỏ B3 (chỉ OCR + kiểm BHYT)
"""
import _bootstrap  # .env, temp->D:, sys.path
import sys

import autofill
import desktop_profiles
import desktop_filler

# Schema bệnh nhân = 7 ô của OH + 1 trường SUY LUẬN trạng thái BHYT
PATIENT_FIELDS = [
    {"key": "ho_ten",    "label": "Họ và tên bệnh nhân",                "entry": "ho_ten",    "type": "text"},
    {"key": "ngay_sinh", "label": "Ngày tháng năm sinh",                 "entry": "ngay_sinh", "type": "date"},
    {"key": "gioi_tinh", "label": "Giới tính",                           "entry": "gioi_tinh", "type": "text"},
    {"key": "cccd",      "label": "Số căn cước công dân hoặc Hộ chiếu",   "entry": "cccd",      "type": "text"},
    {"key": "dia_chi",   "label": "Địa chỉ thường trú",                  "entry": "dia_chi",   "type": "text"},
    {"key": "sdt",       "label": "Số điện thoại liên hệ",               "entry": "sdt",       "type": "text"},
    {"key": "bhyt",      "label": "Số thẻ Bảo hiểm y tế (BHYT)",         "entry": "bhyt",      "type": "text"},
    {"key": "bhyt_status", "label": "Thẻ BHYT còn hạn hay đã hết hạn (theo hôm nay)",
     "entry": "bhyt_status", "type": "radio", "options": ["còn hạn", "đã hết hạn"]},
]

WEB_BHYT_URL = "https://baohiemxahoi.gov.vn/tracuu/Pages/tra-cuu-thoi-han-su-dung-the-bhyt.aspx"


def extract_patient(doc: str) -> dict:
    """B1: OCR + suy luận -> dict {key: value}."""
    recs = autofill._extract_records(doc, PATIENT_FIELDS)
    items, _ = autofill._items_from_values(recs[0] if recs else {}, PATIENT_FIELDS)
    return {it["key"]: it["value"] for it in items}


def check_bhyt_web(data: dict) -> str:
    """B2 (bán tự động): mở web BHYT, điền sẵn mã thẻ/họ tên/ngày sinh, NGƯỜI giải captcha
    + bấm Tra cứu; đọc text kết quả trên trang. KHÔNG vượt được captcha."""
    import web_target
    from playwright.sync_api import sync_playwright
    attach = web_target.cdp_alive()
    print("   (gắn Chrome đang mở)" if attach else "   (mở Chrome mới)")
    with sync_playwright() as p:
        browser, page, owns = web_target.open_page(p, WEB_BHYT_URL, attach=attach, headless=False)
        fields = web_target.inspect_page(page)
        # map dữ liệu OCR -> ô trên web theo nhãn/selector
        m = {"txtMaThe": data.get("bhyt"), "txtHoTen": data.get("ho_ten"), "txtNgaySinh": data.get("ngay_sinh")}
        items = [{**f, "value": next((v for k, v in m.items() if k in f["entry"]), None)} for f in fields]
        web_target.apply_fills(page, items)
        print("   🔒 Trang có captcha — HÃY giải captcha + bấm 'Tra cứu' trên trình duyệt...")
        try:
            page.wait_for_selector("text=/còn hạn|hết hạn|giá trị sử dụng|không tìm thấy/i", timeout=180000)
            import re
            body = page.inner_text("body")
            mres = re.search(r"(?i)(còn hạn[^\n]{0,60}|đã hết hạn[^\n]{0,40}|giá trị sử dụng[^\n]{0,60})", body)
            result = mres.group(1).strip() if mres else "(đã có kết quả — xem trình duyệt)"
        except Exception:
            result = "(chưa đọc được kết quả — captcha chưa giải / hết thời gian)"
        if not owns:
            print("   (giữ tab của bạn)")
        else:
            try: browser.close()
            except Exception: pass
    return result


def fill_oh(data: dict) -> None:
    """B3: mở OH (mock) điền bệnh nhân."""
    prof = desktop_profiles.load_profile("oh_mock")
    desktop_filler.fill_desktop({k: data.get(k) for k in
                                 ("ho_ten", "ngay_sinh", "gioi_tinh", "cccd", "dia_chi", "sdt", "bhyt")},
                                submit=True, profile=prof)


def main() -> int:
    args = sys.argv[1:]
    if "--doc" not in args:
        print(__doc__); return 1
    doc = args[args.index("--doc") + 1]
    use_web = "--bhyt-web" in args
    do_oh = "--no-oh" not in args

    print("=" * 60 + "\nKỊCH BẢN KHÁM BỆNH\n" + "=" * 60)
    print("\n▶ B1. OCR ảnh bệnh nhân + suy luận BHYT...")
    data = extract_patient(doc)
    for k in ("ho_ten", "ngay_sinh", "gioi_tinh", "cccd", "dia_chi", "sdt", "bhyt"):
        print(f"   • {k:<10} = {data.get(k)!r}")
    print(f"\n▶ B1-kết: BHYT (suy luận theo hôm nay) = {data.get('bhyt_status')!r}")

    if use_web:
        print("\n▶ B2. Kiểm BHYT trên FORM WEB (bạn giải captcha)...")
        web_res = check_bhyt_web(data)
        print(f"▶ B2-kết: web trả về → {web_res!r}")

    if do_oh:
        print("\n▶ B3. Mở OH điền thông tin bệnh nhân...")
        fill_oh(data)
        print("▶ B3-kết: đã điền + lưu vào OH (mock).")

    print("\n" + "=" * 60 + "\n✅ XONG KỊCH BẢN.\n" + "=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
