# -*- coding: utf-8 -*-
"""
Đọc chứng từ (ẢNH hoặc PDF) thành danh sách "trang" để đưa vào OCR.
Dùng chung cho mọi tool. Kế thừa chiến thuật lai của covert.py:
  - PDF điện tử (có text) -> lấy text bằng pdfplumber (rẻ, chính xác)
  - PDF scan / ảnh        -> render/encode ảnh cho LLM vision OCR

Trả về list các tuple:
  ('text',  markdown)        # PDF điện tử
  ('image', b64, (w,h))      # ảnh / PDF scan
"""
from __future__ import annotations
from pathlib import Path

from test_image_processing import process_image, prepare_for_api

IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
PDF_TEXT_MIN = 50  # >50 ký tự text => PDF điện tử


def _table_to_markdown(table_data) -> str:
    if not table_data or not any(table_data):
        return ""
    rows = [r for r in table_data if r and any(c is not None for c in r)]
    if not rows:
        return ""
    md = ""
    for i, row in enumerate(rows):
        clean = [str(c).replace("\n", "<br>").strip() if c is not None else "" for c in row]
        md += "| " + " | ".join(clean) + " |\n"
        if i == 0:
            md += "| " + " | ".join(["---"] * len(clean)) + " |\n"
    return md + "\n"


def _pdf_page_text(page_plumber) -> str:
    table_bboxes = [t.bbox for t in page_plumber.find_tables()]

    def not_within_table(obj):
        if obj["object_type"] != "char":
            return True
        for x0, top, x1, bottom in table_bboxes:
            if (x0 <= obj["x0"] <= x1) and (top <= obj["top"] <= bottom):
                return False
        return True

    clean_text = page_plumber.filter(not_within_table).extract_text() or ""
    md_tables = "".join(_table_to_markdown(t) for t in page_plumber.extract_tables())
    return (clean_text + "\n\n" + md_tables).strip()


def file_to_pages(path: str) -> "list[tuple]":
    ext = Path(path).suffix.lower()

    if ext in IMG_EXT:
        b64, _q, size = process_image(path)
        return [("image", b64, size)]

    if ext == ".pdf":
        import fitz
        import pdfplumber
        import cv2
        import numpy as np

        pages: list[tuple] = []
        doc = fitz.open(path)
        plumber = pdfplumber.open(path)
        for i in range(len(doc)):
            txt = _pdf_page_text(plumber.pages[i])
            if len(txt.strip()) > PDF_TEXT_MIN:
                print(f"  ⚡ Trang {i+1}/{len(doc)}: PDF điện tử → text thẳng (không gửi ảnh)")
                pages.append(("text", txt))
            else:
                print(f"  📸 Trang {i+1}/{len(doc)}: PDF scan → render ảnh + LLM OCR")
                pix = doc[i].get_pixmap(matrix=fitz.Matrix(2, 2))
                arr = np.frombuffer(pix.tobytes("jpg"), np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                b64, size = prepare_for_api(img)
                pages.append(("image", b64, size))
        plumber.close()
        doc.close()
        return pages

    raise ValueError(f"Định dạng không hỗ trợ: {ext} (chỉ nhận ảnh hoặc .pdf)")
