# -*- coding: utf-8 -*-
"""
Backend ĐÍCH = APP DESKTOP (pywinauto-UIA). Điền dữ liệu OCR vào một app Windows.
Tái dùng bộ đồ nghề đã kiểm chứng trên Zalo: force_front, clipboard, read-back verify.

Định vị ô theo locator NHIỀU TẦNG: 'auto_id' → 'name' → 'control_type'+'found_index'
(app không có auto_id/name ổn định vẫn bám được). Lấy bằng GUI "➕ App mới…" hoặc
py -3.11 inspect_uia.py "<tên app>" --all. App chạy quyền Admin → chạy tool as Admin.

ĐANG CẤU HÌNH CHO: Microsoft Access (form FormHoaDon trong hoadon_demo.accdb).
"""
from __future__ import annotations
import _bootstrap  # .env, temp->D:, sys.path
import os
import re
import time

from zalo_demo import force_front, set_clipboard, read_value

# ====================== CẤU HÌNH APP ĐÍCH (SỬA Ở ĐÂY) ======================
# Trỏ tới file .accdb → tự mở Access + form (FormHoaDon là StartUpForm).
APP_EXE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hoadon_demo.accdb")
WINDOW_TITLE = "Access"       # regex 1 phần tiêu đề cửa sổ đích

# key | label (cho OCR) | name (UIA Name của ô) | type
FIELDS: list[dict] = [
    {"key": "so_hoa_don",      "label": "Số hoá đơn",          "name": "txtSoHoaDon",      "type": "text"},
    {"key": "ky_hieu",         "label": "Ký hiệu hoá đơn",     "name": "txtKyHieu",        "type": "text"},
    {"key": "ngay_lap",        "label": "Ngày lập",            "name": "txtNgayLap",       "type": "date"},
    {"key": "ten_ncc",         "label": "Tên nhà cung cấp",    "name": "txtTenNCC",        "type": "text"},
    {"key": "mst_ncc",         "label": "MST nhà cung cấp",    "name": "txtMST",           "type": "text"},
    {"key": "dien_giai",       "label": "Diễn giải",           "name": "txtDienGiai",      "type": "text"},
    {"key": "tien_truoc_thue", "label": "Tiền trước thuế",     "name": "txtTienTruocThue", "type": "text"},
    {"key": "thue_suat",       "label": "Thuế suất GTGT",      "name": "txtThueSuat",      "type": "text"},
    {"key": "tong_thanh_toan", "label": "Tổng tiền thanh toán","name": "txtTongThanhToan", "type": "text"},
]
# Access lưu record khi gõ Shift+Enter; form không có nút Lưu riêng.
SUBMIT = {"keys": "+{ENTER}"}   # hoặc {"auto_id": "..."} / {"name": "..."} với app có nút Lưu
# ===========================================================================


_BROWSER_CLASSES = ("Chrome_WidgetWin", "MozillaWindowClass")   # tránh bám nhầm tab trình duyệt cùng tên


def connect_or_launch(title: str = WINDOW_TITLE, exe: str = APP_EXE, timeout: int = 40,
                      window_auto_id: "str | None" = None):
    from pywinauto import Desktop

    def _find():
        cand = []
        for w in Desktop(backend="uia").windows():
            try:
                if not w.is_visible():
                    continue
                cls = w.element_info.class_name or ""
                if any(b in cls for b in _BROWSER_CLASSES):
                    continue                                   # bỏ Chrome/Edge/Firefox
                # khớp theo auto_id cửa sổ HOẶC theo tiêu đề (đỡ kén; vẫn đã loại trình duyệt)
                aid_ok = window_auto_id and (w.element_info.automation_id == window_auto_id)
                title_ok = re.search(f"(?i).*{title}.*", w.window_text() or "")
                if aid_ok or title_ok:
                    cand.append(w)
            except Exception:
                continue
        if not cand:
            raise RuntimeError("no window")
        best = max(cand, key=lambda w: w.rectangle().width() * w.rectangle().height())
        return Desktop(backend="uia").window(handle=best.handle)

    try:
        return _find()
    except Exception as e:
        first_err = e
    if exe and os.path.exists(exe):
        print(f"🚀 Tự khởi chạy app: {exe}")
        if exe.lower().endswith(".ps1"):                   # script PowerShell (vd mock_oh)
            import subprocess
            subprocess.Popen(["powershell", "-ExecutionPolicy", "Bypass", "-File", exe])
        else:                                              # .exe / .accdb …
            os.startfile(exe)
        end = time.time() + timeout
        while time.time() < end:
            try:
                return _find()
            except Exception as e:
                first_err = e
                time.sleep(1)
    from inspect_uia import _elevation_hint
    hint = _elevation_hint(first_err)
    raise RuntimeError(f"Không thấy/bám được cửa sổ '{title}' (app đã mở? đúng tiêu đề?). {hint}")


# kiểu trường (tool) -> control_type (UIA) để định vị đúng loại control
_TYPE2CT = {
    "text": "Edit", "paragraph": "Document", "dropdown": "ComboBox",
    "checkbox": "CheckBox", "radio": "RadioButton", "button": "Button",
    "link": "Hyperlink", "tab": "TabItem", "menuitem": "MenuItem",
    "listitem": "ListItem", "slider": "Slider", "spinner": "Spinner",
}


def _locate(dlg, field: dict):
    """Định vị control theo locator NHIỀU TẦNG: auto_id → name → control_type+found_index.
    control_type suy từ field['type'] (mở rộng ngoài Edit) hoặc field['control_type']."""
    ct = field.get("control_type") or _TYPE2CT.get(field.get("type", ""))
    if field.get("auto_id"):
        kw = {"auto_id": field["auto_id"]}
        if ct:
            kw["control_type"] = ct
        return dlg.child_window(**kw).wrapper_object()
    if field.get("name"):
        kw = {"title_re": f"(?i).*{re.escape(field['name'])}.*"}
        if ct:
            kw["control_type"] = ct
        return dlg.child_window(**kw).wrapper_object()
    if field.get("control_type"):                  # dự phòng: theo loại + thứ tự
        return dlg.child_window(control_type=field["control_type"],
                                found_index=int(field.get("found_index", 0))).wrapper_object()
    raise RuntimeError("field thiếu locator (cần auto_id / name / control_type)")


def _locate_retry(dlg, field: dict, tries: int = 3):
    """Chờ-sẵn-sàng: thử định vị vài lần (control có thể chưa render xong)."""
    last = None
    for i in range(tries):
        try:
            return _locate(dlg, field)
        except Exception as e:
            last = e
            time.sleep(0.5)
    raise last


def fill_one(dlg, field: dict, value) -> str:
    from pywinauto.keyboard import send_keys
    print("       [locate]", end="", flush=True)
    ctrl = _locate_retry(dlg, field)
    print(" [click]", end="", flush=True)
    try:
        ctrl.click_input()
    except Exception as e:
        print(f"(click lỗi {e})", end="", flush=True)
        try:
            ctrl.set_focus()
        except Exception:
            pass
    time.sleep(0.15)

    # Họ A: ValuePattern.SetValue
    done = False
    print(" [setvalue]", end="", flush=True)
    try:
        ctrl.iface_value.SetValue(str(value))
        done = True
    except Exception as e:
        print(f"(setvalue lỗi {e})", end="", flush=True)
    # Họ B: clipboard
    if not done:
        print(" [paste]", end="", flush=True)
        send_keys("^a"); send_keys("{DEL}")
        set_clipboard(str(value))
        send_keys("^v")
    time.sleep(0.2)
    print(" [read]", flush=True)
    return read_value(ctrl)


def do_submit(dlg, submit_cfg: "dict | None" = None) -> None:
    from pywinauto.keyboard import send_keys
    sub = submit_cfg if submit_cfg is not None else SUBMIT
    if sub.get("auto_id") or sub.get("name"):
        kw = {k: v for k, v in sub.items() if k in ("auto_id", "name") and v}
        try:
            btn = dlg.child_window(**kw).wrapper_object()
            try:
                btn.invoke()
            except Exception:
                btn.click_input()
            print("✅ Đã bấm nút Lưu.")
            return
        except Exception as e:
            print(f"⛔ Không bấm được nút Lưu: {e}")
    if sub.get("keys"):
        send_keys(sub["keys"])
        print(f"✅ Đã gửi phím lưu record ({sub['keys']}).")


def _run_steps(dlg, steps: list) -> None:
    """Các BƯỚC điều hướng trước khi điền (app nhiều màn): đăng nhập → mở form.
    Mỗi step: {"fill": auto_id, "value"/"value_env"} | {"click": auto_id} | {"wait": giây}."""
    from pywinauto.keyboard import send_keys
    for st in steps:
        if "wait" in st:
            time.sleep(float(st["wait"]))
            continue
        aid = st.get("fill") or st.get("click")
        ctrl = None
        for _ in range(6):                                 # chờ control xuất hiện (tối đa ~3s rồi bỏ qua)
            try:
                c = dlg.child_window(auto_id=aid).wrapper_object()
                if c.is_visible():
                    ctrl = c
                    break
            except Exception:
                pass
            time.sleep(0.5)
        if ctrl is None:
            print(f"  ⚠️  bước: không thấy '{aid}' (bỏ qua)")
            continue
        if "fill" in st:
            val = os.environ.get(st["value_env"], "") if "value_env" in st else st.get("value", "")
            try:
                ctrl.set_edit_text(val)
            except Exception:
                ctrl.set_focus(); send_keys("^a{BACKSPACE}")
                send_keys(val, with_spaces=True)
            print(f"  ⌨️  điền {aid}")
        else:
            try:
                ctrl.invoke()                  # InvokePattern: không cần cửa sổ ở trên cùng (chắc hơn click chuột)
            except Exception:
                try:
                    ctrl.click_input()
                except Exception:
                    pass
            print(f"  🖱️  bấm {aid}")
        time.sleep(0.4)


def fill_desktop(values_by_id: dict, *, submit: bool = False, profile: "dict | None" = None) -> dict:
    # cấu hình: từ profile (đa-app) hoặc module (mặc định)
    if profile:
        fields = profile["fields"]
        title = profile["window_title"]
        exe = profile.get("exe", "")
        if exe and not os.path.isabs(exe):
            exe = os.path.join(os.path.dirname(os.path.abspath(__file__)), exe)
        submit_cfg = profile.get("submit", {})
        win_aid = profile.get("window_auto_id")
    else:
        fields, title, exe, submit_cfg = FIELDS, WINDOW_TITLE, APP_EXE, SUBMIT
        win_aid = None

    dlg = connect_or_launch(title, exe, window_auto_id=win_aid)
    steps = profile.get("steps") if profile else None
    foc = profile.get("find_or_create") if profile else None
    if steps or foc:                                       # app nhiều màn: đăng nhập + tra cứu + mở form
        # nếu ĐÃ ở màn cần điền (ô đầu hiện sẵn) → bỏ qua điều hướng (gửi tiếp nhanh, không treo)
        on_form = False
        if fields:
            try:
                _locate(dlg, fields[0]); on_form = True
            except Exception:
                on_form = False
        if on_form:
            print("✓ Đã ở màn cần điền — bỏ qua điều hướng.")
        else:
            if steps:
                print("🧭 Điều hướng (đăng nhập → mở màn)...")
                _run_steps(dlg, steps)                     # invoke(): không cần cửa sổ ở trên cùng
            if foc:                                        # tra cứu → CUA quyết định có/chưa → chọn/tạo mới
                import cua_desktop
                print("🤖 Tra cứu + quyết định (CUA vision → UIA bấm nút)...")
                found = cua_desktop.find_or_create(dlg, foc, values_by_id)
                if found:                                  # ĐÃ CÓ trong hệ thống → KHÔNG nhập mới
                    print("✓ Bệnh nhân ĐÃ CÓ trong hệ thống → mở hồ sơ, KHÔNG điền form đăng ký mới.")
                    return {"_existing": True}
    # chờ form tải xong (ô đầu tiên xuất hiện) — mở file mất vài giây
    if fields:
        end = time.time() + 20
        while time.time() < end:
            try:
                _locate(dlg, fields[0])
                break
            except Exception:
                time.sleep(1)
                if not steps:                              # có steps thì GIỮ đúng cửa sổ đã điều hướng (đừng bám cửa sổ khác)
                    try:
                        dlg = connect_or_launch(title, exe, window_auto_id=win_aid)
                    except Exception:
                        pass
    force_front(dlg)
    print(f"  🪟 Đã bám cửa sổ: {dlg.window_text()!r}")
    out = {}
    for f in fields:
        v = values_by_id.get(f["key"])
        if v in (None, "", []):
            continue
        print(f"  → đang điền: {f['label']}")
        try:
            rb = fill_one(dlg, f, v)
        except Exception as e:
            print(f"  • {f['label']:<22} ⛔ KHÔNG tìm thấy ô (name={f.get('name')!r}): {e}")
            continue
        out[f["key"]] = rb
        flag = "✓" if str(rb).strip() == str(v).strip() else "≠"
        print(f"  • {f['label']:<22} điền {v!r} → đọc lại {rb!r}  [{flag}]")
    if submit:
        do_submit(dlg, submit_cfg)
    return out


def schema() -> list[dict]:
    """Schema cho autofill: id=key (Access định danh bằng Name nên không dùng auto_id làm id)."""
    return [{"id": f["key"], "label": f["label"], "type": f.get("type", "text")} for f in FIELDS]


if __name__ == "__main__":
    print(f"Cấu hình {len(FIELDS)} ô cho cửa sổ ~ '{WINDOW_TITLE}'.")
