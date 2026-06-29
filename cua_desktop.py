# -*- coding: utf-8 -*-
"""
CUA DESKTOP (Bậc 4 cho app desktop) — vision SUY LUẬN, UIA THAO TÁC.
Chụp ảnh cửa sổ app → Gemini nhìn để QUYẾT ĐỊNH (vd bệnh nhân đã có chưa) → UIA bấm
nút theo auto_id. Dùng cho bước rẽ nhánh mà UIA tất định không tự quyết được.

  find_or_create(dlg, cfg, values) -> found(bool)   # tìm BN → có thì chọn, chưa thì tạo mới
"""
from __future__ import annotations
import _bootstrap  # .env, temp->D:, sys.path
import re
import json
import time

from test_image_processing import create_ocr_adapter, prepare_for_api


def capture_b64(dlg) -> "str | None":
    """Chụp ảnh cửa sổ (PIL) → base64 cho Gemini."""
    try:
        import numpy as np
        import cv2
        img = dlg.capture_as_image()                 # PIL.Image
        arr = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        b64, _ = prepare_for_api(arr)
        return b64
    except Exception as e:
        print(f"  ⚠️  chụp cửa sổ lỗi: {str(e)[:50]}")
        return None


def _wait_ctrl(dlg, aid, tries=8):
    for _ in range(tries):
        try:
            c = dlg.child_window(auto_id=aid).wrapper_object()
            if c.is_visible():
                return c
        except Exception:
            pass
        time.sleep(0.4)
    return None


def _click(ctrl):
    try:
        ctrl.invoke()
    except Exception:
        try:
            ctrl.click_input()
        except Exception:
            pass


def _set_text(ctrl, text):
    from pywinauto.keyboard import send_keys
    try:
        ctrl.set_edit_text(text)
    except Exception:
        ctrl.set_focus(); send_keys("^a{BACKSPACE}"); send_keys(text, with_spaces=True)


def _decide_found(dlg, create_aid) -> bool:
    """CUA: bệnh nhân ĐÃ tồn tại chưa? Gemini nhìn ảnh quyết định; lỗi → fallback DOM."""
    b64 = capture_b64(dlg)
    if b64:
        try:
            prompt = (
                "Đây là ảnh màn hình TRA CỨU bệnh nhân của phần mềm y tế. Hãy quyết định: "
                "bệnh nhân ĐÃ TỒN TẠI trong hệ thống (có dòng kết quả/tên bệnh nhân) hay "
                "CHƯA CÓ (thông báo 'không tìm thấy' / danh sách trống)?\n"
                'CHỈ trả JSON: {"found": true} nếu đã có, {"found": false} nếu chưa có.')
            res = create_ocr_adapter().ocr(b64, prompt=prompt)
            if res.get("success"):
                m = re.search(r"\{.*\}", res.get("text", ""), re.S)
                if m:
                    found = bool(json.loads(m.group(0)).get("found"))
                    print(f"  🤖 CUA (vision) quyết định: bệnh nhân {'ĐÃ CÓ' if found else 'CHƯA CÓ'}")
                    return found
        except Exception as e:
            print(f"  ⚠️  CUA vision lỗi ({str(e)[:40]}) → fallback DOM")
    # fallback tất định: thấy nút 'tạo mới' đang hiện = chưa có
    try:
        not_found = dlg.child_window(auto_id=create_aid).exists(timeout=0.5)
        print(f"  🔁 DOM fallback: bệnh nhân {'CHƯA CÓ' if not_found else 'ĐÃ CÓ'}")
        return not not_found
    except Exception:
        return False


def find_or_create(dlg, cfg: dict, values: dict) -> bool:
    """Gõ mã tra cứu → bấm Tìm → CUA quyết định có/chưa → bấm Chọn (nếu có) hoặc Tạo mới (nếu chưa).
    Trả True nếu bệnh nhân đã tồn tại."""
    # 1) gõ mã (vd CCCD) vào ô tìm kiếm
    sv = str(values.get(cfg.get("search_value_key", "cccd"), "") or "")
    box = _wait_ctrl(dlg, cfg["search_box"])
    if box and sv:
        _set_text(box, sv)
        print(f"  🔎 Tra cứu: {sv}")
    # 2) bấm Tìm
    btn = _wait_ctrl(dlg, cfg["search_button"])
    if btn:
        _click(btn)
        time.sleep(1.0)
    # 3) CUA quyết định
    found = _decide_found(dlg, cfg["create_button"])
    # 4) UIA thao tác theo quyết định
    target = cfg["select_button"] if found else cfg["create_button"]
    print(f"  ➡️  {'CHỌN bệnh nhân có sẵn' if found else 'TẠO bệnh nhân mới'} (bấm {target})")
    t = _wait_ctrl(dlg, target)
    if t:
        _click(t)
        time.sleep(1.0)
    else:
        print(f"  ⚠️  không thấy nút '{target}'")
    return found
