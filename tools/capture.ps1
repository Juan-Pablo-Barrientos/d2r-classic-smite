# Wait for F10, then grab the middle of the primary screen as fast as possible for N seconds.
# Saves numbered JPEGs (with elapsed ms in the name) to -OutDir. Beeps at start and end.
param(
    [string]$OutDir = "$PSScriptRoot\capture",
    [double]$Seconds = 5,
    [int]$Width = 1100,
    [int]$Height = 800,
    [int]$WaitMinutes = 15
)
Add-Type -AssemblyName System.Drawing, System.Windows.Forms
Add-Type @'
using System.Runtime.InteropServices;
public static class Win {
    [DllImport("user32.dll")] public static extern short GetAsyncKeyState(int vKey);
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}
'@
[void][Win]::SetProcessDPIAware()  # real pixels, not DPI-scaled ones

New-Item -ItemType Directory -Force $OutDir | Out-Null
Get-ChildItem $OutDir -Filter *.jpg -ErrorAction SilentlyContinue | Remove-Item

$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$w = [math]::Min($Width, $screen.Width); $h = [math]::Min($Height, $screen.Height)
$x = $screen.X + [int](($screen.Width - $w) / 2); $y = $screen.Y + [int](($screen.Height - $h) / 2)
"screen $($screen.Width)x$($screen.Height); capturing ${w}x${h} at ($x,$y). Waiting for F10..."

$VK_F10 = 0x79
$deadline = (Get-Date).AddMinutes($WaitMinutes)
while (([Win]::GetAsyncKeyState($VK_F10) -band 0x8000) -eq 0) {
    if ((Get-Date) -gt $deadline) { "no F10 within $WaitMinutes minutes; giving up"; exit 1 }
    Start-Sleep -Milliseconds 15
}
[console]::Beep(1200, 120)

$jpeg = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | ? MimeType -eq 'image/jpeg'
$enc = New-Object System.Drawing.Imaging.EncoderParameters 1
$enc.Param[0] = New-Object System.Drawing.Imaging.EncoderParameter ([System.Drawing.Imaging.Encoder]::Quality, [long]88)
$bmp = New-Object System.Drawing.Bitmap $w, $h
$g = [System.Drawing.Graphics]::FromImage($bmp)
$sw = [Diagnostics.Stopwatch]::StartNew()
$n = 0
while ($sw.Elapsed.TotalSeconds -lt $Seconds) {
    $g.CopyFromScreen($x, $y, 0, 0, $bmp.Size)
    $bmp.Save(('{0}\f{1:D4}_{2:D5}ms.jpg' -f $OutDir, $n, [int]$sw.ElapsedMilliseconds), $jpeg, $enc)
    $n++
}
$g.Dispose(); $bmp.Dispose()
[console]::Beep(800, 200)
'captured {0} frames in {1:N1}s ({2:N0} fps) to {3}' -f $n, $sw.Elapsed.TotalSeconds, ($n / $sw.Elapsed.TotalSeconds), $OutDir
