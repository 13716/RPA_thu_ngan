# mock_oh — App GIẢ LẬP Orion Health HIS (để test automation offline)

Dựng bằng PowerShell + WinForms (có sẵn trong Windows, không cần cài/biên dịch).
WinForms lấy `Control.Name` làm **UIA AutomationId** → đặt tên control trùng auto_id OH thật
nên `desktop_filler` target **y hệt** OH. Dùng để test trước khi có máy Vingroup.

## 3 màn (mô phỏng theo file soi uia_walker của OH)
1. **Đăng nhập** — `FormMain` · `UserNameTextBox` · `PasswordTextBox` · `FacilitySelectorComboBox` · `LoginButton`.
2. **Trang chủ** — `PART_SearchTextBox` (Quick Launch) + nút app: `OPD Visit Registration`, `Patient Profile`…
3. **OPD Visit Registration** — ô bệnh nhân: `txtHoTen` · `txtNgaySinh` · `txtGioiTinh` · `txtCCCD` ·
   `txtDiaChi` · `txtSDT` · `txtBHYT` + `ButtonSave`.

## Chạy thử
```powershell
# 1) Mở app giả lập:
powershell -ExecutionPolicy Bypass -File mock_oh\mock_oh.ps1
#    → gõ user/pass bất kỳ → ĐĂNG NHẬP → bấm "OPD Visit Registration"

# 2) Ở cửa sổ khác, điền từ tài liệu OCR vào form đang mở:
py -3.11 autofill.py --profile oh_mock --doc "C:\...\cccd.jpg" --submit
```
Profile: `profiles/oh_mock.json` (bám cửa sổ theo `window_auto_id=FormMain` để không nhầm tab trình duyệt cùng tên).

## Khi có OH thật
- Đổi `auto_id` trong `oh_mock.json` cho khớp file soi uia_walker thật (login OH dùng đúng
  `UserNameTextBox`/`PasswordTextBox`/`LoginButton` nên phần đăng nhập đã trùng sẵn).
- Còn thiếu: soi màn **OPD Visit Registration đang mở** trên OH thật để lấy auto_id các ô bệnh nhân
  (mock đang dùng tên `txt*` tự đặt).
- Mật khẩu để **vault**, chỉ chạy **UAT**, có người duyệt ở bước lâm sàng.
