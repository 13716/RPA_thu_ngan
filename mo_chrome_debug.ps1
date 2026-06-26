# Mở Chrome kèm CỔNG GỠ LỖI 9222 + profile riêng (giữ đăng nhập/phiên qua các lần)
# để tool GẮN vào và điền THẲNG tab đang mở (không mở/đóng browser mới).
#
# Dùng:
#   1) powershell -ExecutionPolicy Bypass -File mo_chrome_debug.ps1 "https://trang-can-dien"
#   2) Trong Chrome đó: đăng nhập / điều hướng / sẵn sàng captcha
#   3) Chạy:  py -3.11 autofill.py --web "https://trang-can-dien" --doc tailieu.jpg --submit
#      (tool tự thấy cổng 9222 -> điền vào tab đang mở, KHÔNG đụng trình duyệt)

$paths = @(
  (Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe" -EA SilentlyContinue).'(default)',
  "C:\Program Files\Google\Chrome\Application\chrome.exe",
  "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
)
$chrome = $paths | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $chrome) { Write-Host "Không thấy chrome.exe — sửa đường dẫn trong script."; exit 1 }

$prof = Join-Path $env:LOCALAPPDATA "rpa_chrome_profile"
Write-Host "Mở Chrome (gỡ lỗi 9222, profile: $prof)..."
& $chrome --remote-debugging-port=9222 --user-data-dir="$prof" $args
