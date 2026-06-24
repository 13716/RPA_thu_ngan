# legacy/ — bản tiền thân (đã thay thế, lưu để tham chiếu)

Các file ở đây là **phiên bản đầu** của tool, đã được thay bằng pipeline hợp nhất.
**Không file đang dùng nào import chúng** — giữ lại chỉ để đối chiếu lịch sử.

| File cũ | Đã thay bằng |
|---------|--------------|
| `hoadon_to_form.py` | `autofill.py` (luồng hợp nhất 5 đích) |
| `fill_invoice_form_playwright.py` | `form_filler.py` (Playwright đa trang) |
| `fill_invoice_form.py` | `form_filler.submit_post` (HTTP POST) |
| `form_config.py` | schema động sinh trong `autofill` |

> Lưu ý: chúng import các module ở thư mục cha (`_bootstrap`, `ocr_to_form`,
> `test_image_processing`). Nếu thật sự cần chạy lại, copy file về root rồi chạy
> `py -3.11 <file>.py` — đừng chạy thẳng trong `legacy/` (sai sys.path).
