# -*- coding: utf-8 -*-
"""
DEMO desktop automation trên Zalo (app Electron) bằng pywinauto-UIA.
Chỉ GÕ vào ô tìm kiếm liên hệ rồi ĐỌC LẠI để verify — KHÔNG gửi tin, không nhắn ai.

Mục đích: chứng minh cơ chế "điền vào app desktop" hoạt động trên app thật,
trong lúc chờ truy cập được OH. Minh hoạ cả 2 họ thao tác:
  - Họ A: set_edit_text (ValuePattern.SetValue) — nhanh nhưng Electron hay "lười"
  - Họ B: type_keys (gõ phím thật)             — Electron thường cần cái này

Chạy:
    # mở Zalo, đăng nhập trước, rồi:
    py -3.11 zalo_demo.py "Nguyen"
"""
import _bootstrap  # nạp .env (lấy ZALO_PASSWORD), temp->D:, sys.path
import os
import re
import sys
import time

ZALO_EXE = r"C:\Users\hello\AppData\Local\Programs\Zalo\Zalo.exe"
ZALO_PASSWORD = os.environ.get("ZALO_PASSWORD", "")   # đặt trong .env: ZALO_PASSWORD=...


def _type_literal(send_keys, s: str) -> None:
    """Gõ chuỗi literal qua bàn phím thật, escape ký tự đặc biệt của pywinauto."""
    for ch in s:
        send_keys("{" + ch + "}" if ch in "+^%~(){}[]" else ch, pause=0.02)


def _locked(dlg) -> bool:
    """Còn ở màn khoá không? = ô 'passcode' còn tồn tại."""
    try:
        return dlg.child_window(auto_id="passcode", control_type="Edit").exists(timeout=0.5)
    except Exception:
        return False


def unlock(dlg, pwd: str) -> bool:
    """Mở khoá Zalo: gõ mã khoá rồi BẤM nút 'MỞ', và XÁC MINH đã rời màn khoá."""
    if not _locked(dlg):
        print("🔓 Zalo đã mở sẵn (không ở màn khoá) — bỏ qua đăng nhập.")
        return True
    if not pwd:
        print("⚠️  Chưa có ZALO_PASSWORD trong .env — bỏ qua bước mở khoá.")
        return not _locked(dlg)
    from pywinauto.keyboard import send_keys
    from pywinauto.mouse import click as mouse_click
    dlg.set_focus()
    time.sleep(0.3)

    # 1) focus ô mã khoá (auto_id='passcode')
    fld = None
    for kw in (dict(auto_id="passcode", control_type="Edit"),
               dict(title_re=r"(?i).*mã kh.a.*", control_type="Edit"),
               dict(control_type="Edit")):
        try:
            fld = dlg.child_window(**kw).wrapper_object()
            break
        except Exception:
            continue
    if fld is not None:
        try:
            fld.click_input()
        except Exception:
            fld.set_focus()
        print(f"🔑 Focus ô mã khoá (auto_id={fld.element_info.automation_id!r})")
    else:
        print("   (không thấy ô mã khoá — gõ vào ô đang focus)")

    # 2) gõ mã khoá (phím thật) — xoá trước cho sạch
    if fld is not None:
        try:
            fld.set_focus()
        except Exception:
            pass
    dlg.set_focus()
    time.sleep(0.3)
    send_keys("^a")
    send_keys("{BACKSPACE}")
    _type_literal(send_keys, pwd)
    time.sleep(0.4)
    # đọc lại (ô password có thể ẩn giá trị -> rỗng là bình thường)
    if fld is not None:
        print(f"   (đọc lại ô mã khoá: {read_value(fld)!r})")
    print(f"   👀 NHÌN màn khoá Zalo: ô đã hiện {len(pwd)} chấm chưa? (chờ 3s rồi bấm MỞ)")
    time.sleep(3)

    # 3) SUBMIT: thử nhiều cách, KIỂM TRA sau mỗi cách (passcode đã có 4 chấm)
    def _find_mo():
        for ct in ("Hyperlink", "Button", "Text", "Group", "Pane", "Custom"):
            try:
                return dlg.child_window(title_re=r"(?i)^\s*mở\s*$", control_type=ct).wrapper_object()
            except Exception:
                continue
        return None

    def s_enter():
        if fld is not None:
            fld.set_focus()
        send_keys("{ENTER}")

    def s_invoke():
        el = _find_mo()
        if el is None:
            raise RuntimeError("không thấy MỞ")
        el.invoke()                 # gọi InvokePattern trực tiếp (không dùng chuột)

    def s_click():
        el = _find_mo()
        if el is None:
            raise RuntimeError("không thấy MỞ")
        el.click_input()

    def s_coord():
        r = fld.rectangle()
        mouse_click(coords=(r.right + 40, (r.top + r.bottom) // 2))

    for name, fn in (("Enter", s_enter), ("invoke MỞ", s_invoke),
                     ("click MỞ", s_click), ("toạ độ cạnh ô", s_coord)):
        try:
            fn()
            print(f"   ⏎ thử submit: {name}")
        except Exception as e:
            print(f"   {name} lỗi: {e}")
            continue
        for _ in range(4):
            time.sleep(1)
            if not _locked(dlg):
                print(f"✅ Đã rời màn khoá (cách: {name}).")
                return True

    print("⛔ MỞ KHOÁ THẤT BẠI sau khi thử mọi cách — kiểm tra lại mã trong .env.")
    return False


def get_zalo(timeout: int = 30):
    """Gắn vào Zalo; nếu chưa mở thì TỰ KHỞI CHẠY rồi chờ cửa sổ (bước 'mở app')."""
    from pywinauto import Desktop

    def _find():
        # title có thể là 'Zalo' (splash) hoặc 'Zalo - <tên>' (màn khoá/chính).
        # Ưu tiên cửa sổ có '- <tên>' (nội dung thật), rồi tới diện tích lớn nhất.
        # Trả về WindowSpecification (qua handle) để có .child_window().
        wins = Desktop(backend="uia").windows(title_re=r"(?i)zalo")
        vis = [w for w in wins if w.is_visible()] or wins
        if not vis:
            raise RuntimeError("no zalo window")
        named = [w for w in vis if re.search(r"(?i)zalo\s*-\s*\S", w.window_text())]
        pool = named or vis
        best = max(pool, key=lambda w: w.rectangle().width() * w.rectangle().height())
        return Desktop(backend="uia").window(handle=best.handle)

    try:
        return _find()
    except Exception:
        print("🚀 Zalo chưa mở → đang khởi chạy...")
        if not os.path.exists(ZALO_EXE):
            raise RuntimeError(f"Không thấy Zalo.exe tại: {ZALO_EXE}")
        os.startfile(ZALO_EXE)
        end = time.time() + timeout
        while time.time() < end:
            try:
                return _find()
            except Exception:
                time.sleep(1)
        raise RuntimeError("Đã khởi chạy nhưng chưa thấy cửa sổ Zalo "
                           "(có thể đang ở màn hình đăng nhập / quét QR).")


def set_clipboard(text: str) -> None:
    import win32clipboard
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
    win32clipboard.CloseClipboard()


def force_front(dlg) -> None:
    """Ép cửa sổ Zalo lên TRƯỚC thật (tránh click/gõ trúng cửa sổ đè lên)."""
    try:
        hwnd = dlg.wrapper_object().handle
    except Exception:
        hwnd = None
    try:
        dlg.set_focus()
    except Exception:
        pass
    time.sleep(0.3)
    try:
        import win32gui
        if hwnd and win32gui.GetForegroundWindow() != hwnd:
            try:                                   # "búa tạ": minimize rồi restore -> lên trước
                dlg.minimize(); time.sleep(0.2)
                dlg.restore();  time.sleep(0.4)
            except Exception:
                pass
    except Exception:
        pass
    time.sleep(0.2)


def _search_ready(dlg) -> bool:
    """Đã vào màn chính chưa = ô tìm kiếm tồn tại & hiển thị."""
    try:
        s = dlg.child_window(auto_id="contact-search-input", control_type="Edit")
        return s.exists(timeout=0.3) and s.is_visible()
    except Exception:
        return False


def wait_ready(timeout: int = 40):
    """
    Chờ Zalo vào trạng thái RÕ RÀNG sau khi mở (tránh race lúc splash chưa hiện màn khoá).
    Trả về (dlg, state) với state ∈ {'locked','main','unknown'}.
    """
    end = time.time() + timeout
    last = None
    while time.time() < end:
        try:
            last = get_zalo()
        except Exception:
            time.sleep(1)
            continue
        if _locked(last):
            return last, "locked"
        if _search_ready(last):
            return last, "main"
        time.sleep(1)
    return (last or get_zalo()), "unknown"


def read_value(ctrl) -> str:
    """Đọc giá trị ô bằng nhiều cách (UIA value / legacy / window text)."""
    for fn in (
        lambda: ctrl.get_value(),
        lambda: ctrl.legacy_properties().get("Value"),
        lambda: ctrl.window_text(),
    ):
        try:
            v = fn()
            if v:
                return v
        except Exception:
            pass
    return ""


def enter_zalo():
    """Mở/chờ Zalo tới trạng thái rõ ràng, tự mở khoá nếu đang khoá. Trả về dlg hoặc None."""
    dlg, state = wait_ready()
    dlg.set_focus()
    print(f"🪟 Cửa sổ: {dlg.window_text()}  |  trạng thái: {state}")
    if state == "locked":
        if not unlock(dlg, ZALO_PASSWORD):
            return None
        dlg, state = wait_ready(timeout=20)   # chờ vào màn chính
    if state != "main" and not _search_ready(dlg):
        print("⛔ Chưa vào được màn chính Zalo.")
        return None
    return dlg


def main() -> int:
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    text = pos[0] if pos else "Nguyen Van A"

    dlg = enter_zalo()
    if dlg is None:
        return 2
    if not open_chat(dlg, text):
        return 2
    return 0


def open_chat(dlg, name: str) -> bool:
    """Tìm tên trong ô search → Enter mở chat người đầu tiên. KHÔNG gửi tin nhắn."""
    from pywinauto.keyboard import send_keys

    force_front(dlg)                      # ép Zalo lên trước trước khi thao tác
    search = dlg.child_window(auto_id="contact-search-input", control_type="Edit")
    try:
        search.wait("exists", timeout=12)
    except Exception:
        print("⛔ Chưa vào được màn chính (ô tìm kiếm không xuất hiện).")
        return False

    # 1) click ô search rồi DÁN tên (clipboard — chuẩn dấu, đỡ lỗi gõ)
    try:
        search.click_input()
    except Exception:
        search.set_focus()
    send_keys("^a")
    send_keys("{BACKSPACE}")
    set_clipboard(name)
    send_keys("^v")
    time.sleep(1.5)                       # chờ kết quả lọc
    typed = read_value(search)
    print(f"🔎 Đã tìm: {name!r}  (đọc lại ô: {typed!r})")
    if not typed.strip():                 # ô không nhận chữ => chưa thực sự ở màn chính
        print("⛔ Ô tìm kiếm KHÔNG nhận chữ → chưa vào màn chính (chưa mở khoá?). Dừng.")
        return False

    # 2) Enter để mở chat người đầu tiên trong kết quả
    send_keys("{ENTER}")
    time.sleep(1.5)
    print("💬 Đã Enter mở khung chat (không gửi tin nhắn).")

    # 3) chụp ảnh bằng chứng cửa sổ Zalo
    try:
        shot = _bootstrap.SCREENSHOT_DIR
        shot.mkdir(exist_ok=True)
        path = shot / ("zalo_chat_" + re.sub(r"[^0-9A-Za-z]+", "_", name).strip("_") + ".png")
        dlg.capture_as_image().save(str(path))
        print(f"📸 Ảnh khung chat: {path}")
    except Exception as e:
        print(f"   (không chụp được ảnh: {e})")

    print("\n✅ Xong: mở app → mở khoá → tìm người → mở chat.")
    return True


if __name__ == "__main__":
    try:
        import pywinauto  # noqa
    except ImportError:
        print("❌ Cần: py -3.11 -m pip install pywinauto")
        raise SystemExit(1)
    raise SystemExit(main())
