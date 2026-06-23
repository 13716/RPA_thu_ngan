# -*- coding: utf-8 -*-
"""
Khởi tạo môi trường cho toàn bộ app rpa_hoadon. PHẢI `import _bootstrap` ở
DÒNG ĐẦU mỗi script (trước cv2, playwright, fitz, test_image_processing...).

Nó làm 3 việc:
  1. Ép file tạm (Windows/Chrome/OpenCV) ghi sang ổ D: (tránh ổ C: đầy).
  2. Thêm thư mục cha (ocr_vsf) vào sys.path để import được test_image_processing.py.
  3. Nạp .env (tìm ở thư mục cha rồi tới thư mục này) để có OCR_PROVIDER + API key.
"""
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent          # ...\ocr_vsf\rpa_hoadon
PARENT = HERE.parent                            # ...\ocr_vsf  (chứa test_image_processing.py)

# (2) cho phép import pipeline OCR nằm ở thư mục cha
if str(PARENT) not in sys.path:
    sys.path.insert(0, str(PARENT))

# (3) nạp .env: ưu tiên ocr_vsf\.env, fallback rpa_hoadon\.env
try:
    from dotenv import load_dotenv
    for cand in (PARENT / ".env", HERE / ".env"):
        if cand.exists():
            load_dotenv(cand, override=True)
            break
except Exception:
    pass

# (1) chuyển temp sang ổ D:
_TMP = HERE / "_tmp"
_TMP.mkdir(exist_ok=True)
_p = str(_TMP)
os.environ["TEMP"] = _p
os.environ["TMP"] = _p
os.environ["TMPDIR"] = _p
tempfile.tempdir = _p

# đường dẫn output (tuyệt đối, trên ổ D:)
SCREENSHOT_DIR = HERE / "screenshots"
DEBUG_DIR = HERE / "debug_output"
