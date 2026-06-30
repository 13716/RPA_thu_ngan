# Mock Orion Health HIS — giả lập 3 màn (Đăng nhập → Trang chủ → OPD Visit Registration)
# để TEST automation UIA offline. WinForms lấy Control.Name làm UIA AutomationId
# nên đặt Name trùng auto_id OH thật -> desktop_filler target y hệt.
#
# Chạy:  powershell -ExecutionPolicy Bypass -File mock_oh\mock_oh.ps1
# (đăng nhập: gõ user/pass bất kỳ rồi ĐĂNG NHẬP; mở "OPD Visit Registration" rồi chạy autofill)

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
[Windows.Forms.Application]::EnableVisualStyles()

# ── lớp dữ liệu: lưu tạm bệnh nhân đã tạo vào patients.json (như "DB" của OH) ──
$script:PatientsFile = Join-Path (Split-Path -Parent $PSCommandPath) "patients.json"
function Get-Patients {
    if (-not (Test-Path $script:PatientsFile)) { return @() }
    try {
        $raw = Get-Content $script:PatientsFile -Raw -Encoding UTF8 | ConvertFrom-Json
        # lọc bỏ phần lồng/rác, chỉ giữ object có 'cccd' và dựng lại sạch
        return @($raw | Where-Object { $_.cccd } | ForEach-Object {
            [PSCustomObject]@{ cccd=$_.cccd; ho_ten=$_.ho_ten; ngay_sinh=$_.ngay_sinh;
                               gioi_tinh=$_.gioi_tinh; dia_chi=$_.dia_chi; sdt=$_.sdt; bhyt=$_.bhyt }
        })
    } catch { return @() }
}
function Add-Patient($p) {
    $list = @(Get-Patients)
    $list += [PSCustomObject]@{ cccd=$p.cccd; ho_ten=$p.ho_ten; ngay_sinh=$p.ngay_sinh;
                                gioi_tinh=$p.gioi_tinh; dia_chi=$p.dia_chi; sdt=$p.sdt; bhyt=$p.bhyt }
    ConvertTo-Json -InputObject @($list) -Depth 3 | Out-File $script:PatientsFile -Encoding UTF8
}
function Refresh-SavedList {
    if (-not $script:lstSaved) { return }
    $script:lstSaved.Items.Clear()
    foreach ($p in Get-Patients) {
        [void]$script:lstSaved.Items.Add(("{0,-15} {1,-22} {2,-12} {3}" -f $p.cccd, $p.ho_ten, $p.ngay_sinh, $p.gioi_tinh))
    }
}

$form = New-Object Windows.Forms.Form
$form.Name = "FormMain"                               # auto_id cửa sổ (như OH)
$form.Text = "Orion Health HIS (UAT Environment)"
$form.Size = New-Object Drawing.Size(940, 660)
$form.StartPosition = "CenterScreen"
$form.BackColor = [Drawing.Color]::White

function New-Label($text, $x, $y, $w) {
    $l = New-Object Windows.Forms.Label
    $l.Text = $text; $l.Location = "$x,$y"; $l.Size = "$w,22"
    $l.Font = New-Object Drawing.Font("Segoe UI", 10)
    return $l
}
function New-Box($name, $x, $y, $w) {
    $t = New-Object Windows.Forms.TextBox
    $t.Name = $name; $t.Location = "$x,$y"; $t.Size = "$w,26"
    $t.Font = New-Object Drawing.Font("Segoe UI", 11)
    return $t
}

# ───────────────── PANEL 1: ĐĂNG NHẬP ─────────────────
$pnlLogin = New-Object Windows.Forms.Panel
$pnlLogin.Dock = "Fill"

$ttl = New-Label "Orion Health HIS" 320 40 320
$ttl.Font = New-Object Drawing.Font("Segoe UI", 20, [Drawing.FontStyle]::Bold)
$ttl.ForeColor = [Drawing.Color]::FromArgb(0,120,160)
$pnlLogin.Controls.Add($ttl)
$pnlLogin.Controls.Add((New-Label "Hello, Welcome!" 330 90 300))

$pnlLogin.Controls.Add((New-Label "Tên đăng nhập" 300 150 320))
$txtUser = New-Box "UserNameTextBox" 300 174 320
$pnlLogin.Controls.Add($txtUser)

$pnlLogin.Controls.Add((New-Label "Mật khẩu" 300 214 320))
$txtPass = New-Box "PasswordTextBox" 300 238 320
$txtPass.PasswordChar = "*"
$pnlLogin.Controls.Add($txtPass)

$pnlLogin.Controls.Add((New-Label "Cơ sở (Facility)" 300 278 320))
$cboFac = New-Object Windows.Forms.ComboBox
$cboFac.Name = "FacilitySelectorComboBox"; $cboFac.Location = "300,302"; $cboFac.Size = "320,26"
$cboFac.DropDownStyle = "DropDownList"
[void]$cboFac.Items.AddRange(@("HHN-Vinmec Times City","Vinmec Central Park"))
$cboFac.SelectedIndex = 0
$pnlLogin.Controls.Add($cboFac)

$btnLogin = New-Object Windows.Forms.Button
$btnLogin.Name = "LoginButton"; $btnLogin.Text = "ĐĂNG NHẬP"
$btnLogin.Location = "300,350"; $btnLogin.Size = "320,40"
$btnLogin.BackColor = [Drawing.Color]::FromArgb(0,120,160)
$btnLogin.ForeColor = [Drawing.Color]::White
$btnLogin.Font = New-Object Drawing.Font("Segoe UI", 11, [Drawing.FontStyle]::Bold)
$pnlLogin.Controls.Add($btnLogin)

$lblLoginMsg = New-Label "" 300 400 320
$lblLoginMsg.Name = "WarningContentTextBlock"; $lblLoginMsg.ForeColor = [Drawing.Color]::Red
$pnlLogin.Controls.Add($lblLoginMsg)

# ───────────────── PANEL 2: TRANG CHỦ ─────────────────
$pnlHome = New-Object Windows.Forms.Panel
$pnlHome.Dock = "Fill"; $pnlHome.Visible = $false

$pnlHome.Controls.Add((New-Label "Quick Launch (gõ tên màn):" 30 20 260))
$txtSearch = New-Box "PART_SearchTextBox" 30 44 300
$pnlHome.Controls.Add($txtSearch)
$pnlHome.Controls.Add((New-Label "Applications" 30 90 200))

$apps = @("OPD Visit Registration","Emergency Visit Registration","Patient Profile",
          "Patient Queue","Patient Billing","Select Company")
$y = 116
foreach ($a in $apps) {
    $b = New-Object Windows.Forms.Button
    $b.Name = $a                                      # auto_id = tên app (như sidebar OH)
    $b.Text = $a; $b.Location = "30,$y"; $b.Size = "300,34"
    $b.TextAlign = "MiddleLeft"
    $b.Font = New-Object Drawing.Font("Segoe UI", 10)
    if ($a -eq "OPD Visit Registration") {
        $b.Add_Click({ $pnlHome.Visible = $false; $pnlSearch.Visible = $true; Refresh-SavedList })
    } else {
        $b.Add_Click({ [Windows.Forms.MessageBox]::Show("(mock) màn '$($this.Name)' chưa dựng") })
    }
    $pnlHome.Controls.Add($b)
    $y += 40
}

# ──────────── PANEL 2.5: TRA CỨU / TẠO BỆNH NHÂN (PatientBanner mô phỏng) ────────────
$pnlSearch = New-Object Windows.Forms.Panel
$pnlSearch.Dock = "Fill"; $pnlSearch.Visible = $false

$sh = New-Label "Tra cứu bệnh nhân" 30 16 400
$sh.Font = New-Object Drawing.Font("Segoe UI", 15, [Drawing.FontStyle]::Bold)
$pnlSearch.Controls.Add($sh)

$btnSearchBack = New-Object Windows.Forms.Button
$btnSearchBack.Name = "SearchBackButton"; $btnSearchBack.Text = "← Trang chủ"
$btnSearchBack.Location = "560,14"; $btnSearchBack.Size = "120,30"
$btnSearchBack.Add_Click({ $pnlSearch.Visible = $false; $pnlHome.Visible = $true })
$pnlSearch.Controls.Add($btnSearchBack)
$pnlSearch.Controls.Add((New-Label "Mã CCCD / Mã bệnh nhân:" 30 70 200))
$txtSearch = New-Box "PART_TextBox" 240 68 300
$pnlSearch.Controls.Add($txtSearch)
$btnBrowse = New-Object Windows.Forms.Button
$btnBrowse.Name = "PART_BrowseButton"; $btnBrowse.Text = "Tìm"
$btnBrowse.Location = "560,66"; $btnBrowse.Size = "90,28"
$pnlSearch.Controls.Add($btnBrowse)

$lblResult = New-Label "" 30 120 620
$lblResult.Name = "SearchResultText"
$lblResult.Font = New-Object Drawing.Font("Segoe UI", 11)
$pnlSearch.Controls.Add($lblResult)

$btnCreate = New-Object Windows.Forms.Button
$btnCreate.Name = "btnCreatePatient"; $btnCreate.Text = "+ Tạo bệnh nhân mới"
$btnCreate.Location = "30,160"; $btnCreate.Size = "200,38"; $btnCreate.Visible = $false
$btnCreate.BackColor = [Drawing.Color]::FromArgb(0,150,90); $btnCreate.ForeColor = [Drawing.Color]::White
$btnCreate.Font = New-Object Drawing.Font("Segoe UI", 10, [Drawing.FontStyle]::Bold)
$pnlSearch.Controls.Add($btnCreate)
$btnSelect = New-Object Windows.Forms.Button
$btnSelect.Name = "btnSelectPatient"; $btnSelect.Text = "Chọn bệnh nhân"
$btnSelect.Location = "250,160"; $btnSelect.Size = "180,38"; $btnSelect.Visible = $false
$pnlSearch.Controls.Add($btnSelect)

# danh sách BỆNH NHÂN ĐÃ LƯU (từ patients.json) — hiển thị dưới phần tìm kiếm
$pnlSearch.Controls.Add((New-Label "Bệnh nhân đã lưu (patients.json):" 30 214 400))
$lstSaved = New-Object Windows.Forms.ListBox
$lstSaved.Name = "lstSavedPatients"; $lstSaved.Location = "30,238"; $lstSaved.Size = "660,300"
$lstSaved.Font = New-Object Drawing.Font("Consolas", 9)
$pnlSearch.Controls.Add($lstSaved)
$script:lstSaved = $lstSaved

$script:knownPatients = @{ "111111111111" = "Nguyễn Có Sẵn"; "222222222222" = "Trần Đã Tồn Tại" }
$btnBrowse.Add_Click({
    $code = $txtSearch.Text.Trim()
    $name = $null
    if ($script:knownPatients.ContainsKey($code)) { $name = $script:knownPatients[$code] }
    else {
        $saved = Get-Patients | Where-Object { "$($_.cccd)" -eq $code } | Select-Object -First 1
        if ($saved) { $name = $saved.ho_ten }
    }
    if ($name) {
        $lblResult.Text = "✓ Đã tìm thấy: $name   (CCCD $code)"
        $lblResult.ForeColor = [Drawing.Color]::FromArgb(0,120,0)
        $btnSelect.Visible = $true; $btnCreate.Visible = $false
    } else {
        $lblResult.Text = "✗ Không tìm thấy bệnh nhân với mã '$code'. Có thể tạo mới."
        $lblResult.ForeColor = [Drawing.Color]::FromArgb(180,0,0)
        $btnCreate.Visible = $true; $btnSelect.Visible = $false
    }
})
$btnCreate.Add_Click({ $pnlSearch.Visible = $false; $pnlReg.Visible = $true })
# ĐÃ CÓ -> mở hồ sơ (ở lại màn tra cứu, sẵn sàng cho bệnh nhân kế)
$btnSelect.Add_Click({
    $lblResult.Text = "✓ Đã mở hồ sơ bệnh nhân (không tạo mới)."
    $btnSelect.Visible = $false; $txtSearch.Clear()
})

# ──────────── PANEL 3: OPD VISIT REGISTRATION (form điền) ────────────
$pnlReg = New-Object Windows.Forms.Panel
$pnlReg.Dock = "Fill"; $pnlReg.Visible = $false; $pnlReg.AutoScroll = $true

$hdr = New-Label "OPD Visit Registration" 30 16 500
$hdr.Font = New-Object Drawing.Font("Segoe UI", 15, [Drawing.FontStyle]::Bold)
$pnlReg.Controls.Add($hdr)

# nhãn hiển thị | tên control (auto_id). desktop_filler target theo auto_id.
$regFields = @(
    @("Họ và tên bệnh nhân", "txtHoTen"),
    @("Ngày tháng năm sinh (DD/MM/YYYY)", "txtNgaySinh"),
    @("Giới tính", "txtGioiTinh"),
    @("Số CCCD / Hộ chiếu", "txtCCCD"),
    @("Địa chỉ thường trú", "txtDiaChi"),
    @("Số điện thoại", "txtSDT"),
    @("Số thẻ BHYT", "txtBHYT")
)
$y = 64
foreach ($fld in $regFields) {
    $pnlReg.Controls.Add((New-Label $fld[0] 30 $y 240))
    $pnlReg.Controls.Add((New-Box $fld[1] 280 ($y-2) 360))
    $y += 40
}

$btnSave = New-Object Windows.Forms.Button
$btnSave.Name = "ButtonSave"; $btnSave.Text = "Save"
$btnSave.Location = "280,$y"; $btnSave.Size = "120,36"
$btnSave.BackColor = [Drawing.Color]::FromArgb(0,150,90)
$btnSave.ForeColor = [Drawing.Color]::White
$lblSaved = New-Label "" 420 ($y+6) 220
$lblSaved.Name = "StatusTextBlock"; $lblSaved.ForeColor = [Drawing.Color]::FromArgb(0,120,0)
$btnSave.Add_Click({
    $get = { param($n) $c = $pnlReg.Controls.Find($n, $true); if ($c.Count) { $c[0].Text } else { "" } }
    $p = [PSCustomObject][ordered]@{
        cccd      = & $get "txtCCCD"
        ho_ten    = & $get "txtHoTen"
        ngay_sinh = & $get "txtNgaySinh"
        gioi_tinh = & $get "txtGioiTinh"
        dia_chi   = & $get "txtDiaChi"
        sdt       = & $get "txtSDT"
        bhyt      = & $get "txtBHYT"
    }
    Add-Patient $p
    # xoá form + QUAY VỀ màn tra cứu (sẵn sàng bệnh nhân kế)
    foreach ($fld in $regFields) { $c = $pnlReg.Controls.Find($fld[1], $true); if ($c.Count) { $c[0].Clear() } }
    $pnlReg.Visible = $false; $pnlSearch.Visible = $true
    Refresh-SavedList
    $txtSearch.Clear(); $btnCreate.Visible = $false; $btnSelect.Visible = $false
    $lblResult.Text = "✓ Đã lưu bệnh nhân mới vào patients.json. Tra cứu bệnh nhân tiếp theo..."
    $lblResult.ForeColor = [Drawing.Color]::FromArgb(0,120,0)
})
$pnlReg.Controls.Add($btnSave)
$pnlReg.Controls.Add($lblSaved)

$btnBack = New-Object Windows.Forms.Button
$btnBack.Name = "BackButton"; $btnBack.Text = "← Trang chủ"
$btnBack.Location = "30,$y"; $btnBack.Size = "120,36"
$btnBack.Add_Click({ $pnlReg.Visible = $false; $pnlHome.Visible = $true })
$pnlReg.Controls.Add($btnBack)

# ───────────────── điều hướng ─────────────────
$btnLogin.Add_Click({
    if ($txtUser.Text.Trim() -eq "" -or $txtPass.Text.Trim() -eq "") {
        $lblLoginMsg.Text = "Nhập tên đăng nhập và mật khẩu."
        return
    }
    $pnlLogin.Visible = $false; $pnlHome.Visible = $true
    $form.Text = "Registration (UAT Environment) - $($txtUser.Text)"
})

$form.Controls.Add($pnlReg)
$form.Controls.Add($pnlSearch)
$form.Controls.Add($pnlHome)
$form.Controls.Add($pnlLogin)
[void][Windows.Forms.Application]::Run($form)
