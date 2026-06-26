# -*- coding: utf-8 -*-
"""
SOI CÂY UIA của một app Windows — để biết tên/ID từng ô nhập trước khi điền.
Tương đương Accessibility Insights nhưng bằng Python (pywinauto-UIA).

Cài: py -3.11 -m pip install pywinauto

Dùng:
    # 1) Liệt kê các cửa sổ đang mở (lấy đúng title để soi):
    py -3.11 inspect_uia.py

    # 2) Soi 1 cửa sổ theo title (khớp 1 phần, không phân biệt hoa/thường):
    py -3.11 inspect_uia.py "Tên cửa sổ app"

In ra mọi control TƯƠNG TÁC ĐƯỢC (ô nhập, combobox, checkbox, radio, nút) kèm:
  ControlType | AutomationId | Name | có ValuePattern? (điền set-value được không)
và sinh sẵn khối CONTROLS để dán vào desktop_config (sẽ viết sau).
"""
import sys


def list_window_titles() -> "list[str]":
    """Tiêu đề các cửa sổ cấp cao đang mở (cho GUI/CLI chọn để soi)."""
    from pywinauto import Desktop
    seen = []
    for w in Desktop(backend="uia").windows():
        try:
            t = w.window_text()
            if t and t not in seen:
                seen.append(t)
        except Exception:
            pass
    return seen


def list_windows():
    print("📋 Các cửa sổ cấp cao đang mở (lấy 'title' để soi):\n")
    for t in list_window_titles():
        print(f"   • {t}")
    print('\n→ Chạy lại: py -3.11 inspect_uia.py "<một phần title>"')


# kiểu control TƯƠNG TÁC phổ biến -> kiểu trường trong tool (mở rộng để đỡ sót)
CTRL_MAP = {
    "Edit": "text", "Document": "paragraph", "ComboBox": "dropdown",
    "CheckBox": "checkbox", "RadioButton": "radio", "Button": "button",
    "Hyperlink": "link", "TabItem": "tab", "MenuItem": "menuitem",
    "ListItem": "listitem", "Slider": "slider", "Spinner": "spinner",
}


def _elevation_hint(err: Exception) -> str:
    low = str(err).lower()
    if any(k in low for k in ("denied", "0x80070005", "access is denied", "elevat")):
        return ("⛔ Không đọc được cây UIA — RẤT CÓ THỂ app chạy QUYỀN ADMIN còn tool thì không "
                "(Windows chặn tiến trình quyền thấp đọc cửa sổ quyền cao). Hãy chạy lại tool "
                "BẰNG QUYỀN ADMINISTRATOR. (gốc: " + str(err)[:100] + ")")
    return "Soi lỗi: " + str(err)[:180]


# pattern UIA -> thuộc tính iface của pywinauto (truy cập lỗi = không hỗ trợ pattern đó)
_PATTERNS = [
    ("Value", "iface_value"), ("Toggle", "iface_toggle"), ("Invoke", "iface_invoke"),
    ("ExpandCollapse", "iface_expand_collapse"), ("Selection", "iface_selection"),
    ("SelectionItem", "iface_selection_item"), ("RangeValue", "iface_range_value"),
    ("Grid", "iface_grid"), ("GridItem", "iface_grid_item"), ("Table", "iface_table"),
    ("Text", "iface_text"), ("Scroll", "iface_scroll"), ("Window", "iface_window"),
]
_CORE_PATTERNS = {"Value", "Toggle", "Invoke", "ExpandCollapse", "SelectionItem"}


def supported_patterns(ctrl, full: bool = True) -> "list[str]":
    """Các UIA pattern control HỖ TRỢ (Value/Toggle/Invoke/Grid…) → biết tương tác kiểu nào.
    full=False chỉ dò nhóm lõi (nhanh, cho soi GUI)."""
    out = []
    for name, attr in _PATTERNS:
        if not full and name not in _CORE_PATTERNS:
            continue
        try:
            if getattr(ctrl, attr) is not None:
                out.append(name)
        except Exception:
            pass
    return out


def _key_value(ctrl) -> str:
    """Giá trị hiện tại để xem nhanh (Value / Toggle / RangeValue)."""
    try:
        v = ctrl.iface_value.CurrentValue
        if v not in (None, ""):
            return f"value={v!r}"
    except Exception:
        pass
    try:
        return f"toggle={int(ctrl.iface_toggle.CurrentToggleState)}"
    except Exception:
        pass
    try:
        rv = ctrl.iface_range_value
        return f"range={rv.CurrentValue}[{rv.CurrentMinimum}..{rv.CurrentMaximum}]"
    except Exception:
        pass
    return ""


def collect_controls(title: str) -> "tuple[str, list[dict]]":
    """Soi 1 cửa sổ → (tiêu đề thật, danh sách control). Bắt MỌI control tương tác HOẶC có
    auto_id (đỡ sót Hyperlink/Group-có-id như richInput của Zalo). Kèm control_type + index
    để làm LOCATOR DỰ PHÒNG khi auto_id/name rỗng/trùng.
    """
    from pywinauto import Desktop
    win = Desktop(backend="uia").window(title_re=f"(?i).*{title}.*")
    win.wait("exists", timeout=10)
    try:
        win.wait("visible ready", timeout=5)          # chờ app VẼ XONG (tránh cây thiếu/đang load)
    except Exception:
        pass
    try:
        descs = win.descendants()
    except Exception as e:
        raise RuntimeError(_elevation_hint(e))
    rows, counter = [], {}
    for ctrl in descs:
        info = ctrl.element_info
        ct = info.control_type or ""
        aid = info.automation_id or ""
        if ct not in CTRL_MAP and not aid:            # bỏ container/nhãn không định danh
            continue
        idx = counter.get(ct, 0)
        counter[ct] = idx + 1
        has_value = False
        try:
            has_value = bool(ctrl.iface_value) if hasattr(ctrl, "iface_value") else False
        except Exception:
            pass
        rows.append({
            "type": CTRL_MAP.get(ct, (ct or "other").lower()),
            "auto_id": aid,
            "name": info.name or "",
            "control_type": ct,                        # locator dự phòng
            "index": idx,                              # found_index theo control_type
            "value": has_value,
            "patterns": supported_patterns(ctrl, full=False),   # tương tác kiểu nào
        })
    return win.window_text(), rows


def _slug(s: str) -> str:
    import re, unicodedata
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace("đ", "d").lower()
    return re.sub(r"[^a-z0-9]+", "_", s).strip("_") or "field"


def inspect(title: str, show_all: bool = False):
    from pywinauto import Desktop
    win = Desktop(backend="uia").window(title_re=f"(?i).*{title}.*")
    win.wait("exists", timeout=10)
    print(f"\n🪟 Cửa sổ: {win.window_text()}\n")

    if show_all:
        # In MỌI control + PATTERN hỗ trợ + giá trị hiện tại (giàu như UIA walker)
        print(f"{'#':<4}{'TYPE':<14}{'VIS':<4}{'AUTO_ID':<22}{'NAME':<26}{'PATTERNS':<34}VALUE")
        print("-" * 130)
        for i, ctrl in enumerate(win.descendants(), 1):
            info = ctrl.element_info
            try:
                vis = "Y" if ctrl.is_visible() else "."
            except Exception:
                vis = "?"
            pats = ",".join(supported_patterns(ctrl))      # đầy đủ pattern
            kv = _key_value(ctrl)
            print(f"{i:<4}{str(info.control_type)[:13]:<14}{vis:<4}"
                  f"{(info.automation_id or '')[:21]:<22}{(info.name or '')[:25]:<26}"
                  f"{pats[:33]:<34}{kv[:40]}")
        return

    print(f"{'#':<3}{'TYPE':<11}{'VALUE?':<7}{'AUTO_ID':<24}NAME")
    print("-" * 80)

    _wt, rows = collect_controls(title)
    for i, r in enumerate(rows, 1):
        print(f"{i:<3}{r['type']:<11}{'✔' if r['value'] else '':<7}{r['auto_id'][:23]:<24}{r['name']}")

    # khối CONTROLS gợi ý (chỉ ô nhập/chọn, bỏ button)
    inputs = [r for r in rows if r["type"] != "button"]
    print("\n" + "=" * 80)
    print("➜ Khối CONTROLS gợi ý — sửa 'key' cho khớp 9 trường OCR, bỏ ô không cần:")
    print("=" * 80)
    print("CONTROLS = [")
    for r in inputs:
        ident = f'"auto_id": "{r["auto_id"]}"' if r["auto_id"] else f'"name": "{r["name"]}"'
        print(f'    {{"key": "{_slug(r["name"]) or "TODO"}", {ident}, "type": "{r["type"]}"}},')
    print("]")
    print("\n💡 Ô nào AUTO_ID trống thì định danh bằng Name (hoặc thứ tự). "
          "Gửi output này cho tôi để viết backend điền desktop.")


def main() -> int:
    try:
        import pywinauto  # noqa
    except ImportError:
        print("❌ Chưa cài pywinauto. Chạy: py -3.11 -m pip install pywinauto")
        return 1
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    show_all = "--all" in sys.argv
    if not pos:
        list_windows()
    else:
        inspect(pos[0], show_all=show_all)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
