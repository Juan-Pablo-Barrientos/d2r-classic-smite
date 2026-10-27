# Side-by-side comparison GIF: pre-rendered left frames (left_000.png, ... from dcc_sync.py) next to
# captured JPEG frames at FromMs, FromMs+StepMs, ... (cropped), each panel labelled on top.
# gif_fix.py adds timing and looping afterwards.
param(
    [Parameter(Mandatory)][string]$Out,
    [Parameter(Mandatory)][string]$LeftDir,
    [Parameter(Mandatory)][string]$RightDir,
    [int]$FromMs, [int]$StepMs = 40,
    [int[]]$RightCrop = @(430, 100, 290, 340),
    [string]$LeftLabel = 'Original Diablo II', [string]$RightLabel = 'Classic Smite (HD)'
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationCore, WindowsBase, System.Drawing

function To-Wpf([System.Drawing.Bitmap]$bmp) {
    $ms = New-Object IO.MemoryStream; $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png); $ms.Position = 0
    (New-Object System.Windows.Media.Imaging.PngBitmapDecoder $ms, 'PreservePixelFormat', 'OnLoad').Frames[0]
}

$lefts = Get-ChildItem $LeftDir -Filter 'left_*.png' | Sort-Object Name
$right = Get-ChildItem $RightDir -Filter *.jpg | Sort-Object Name | % {
    [pscustomobject]@{ File = $_.FullName; Ms = [int][regex]::Match($_.Name, '_(\d+)ms').Groups[1].Value }
}
$pw = $RightCrop[2]; $ph = $RightCrop[3]; $labelH = 28; $gap = 6
$font = New-Object System.Drawing.Font 'Segoe UI', 12, ([System.Drawing.FontStyle]::Bold)
$fmt = New-Object System.Drawing.StringFormat; $fmt.Alignment = 'Center'; $fmt.LineAlignment = 'Center'
$enc = New-Object System.Windows.Media.Imaging.GifBitmapEncoder

for ($i = 0; $i -lt $lefts.Count; $i++) {
    $canvas = New-Object System.Drawing.Bitmap (2 * $pw + $gap), ($ph + $labelH)
    $g = [System.Drawing.Graphics]::FromImage($canvas)
    $g.Clear([System.Drawing.Color]::FromArgb(13, 17, 23))
    $limg = [System.Drawing.Image]::FromFile($lefts[$i].FullName)
    $g.DrawImage($limg, 0, $labelH, $pw, $ph); $limg.Dispose()
    $t = $FromMs + $i * $StepMs
    $rf = $right | Sort-Object { [math]::Abs($_.Ms - $t) } | Select-Object -First 1
    $rimg = [System.Drawing.Image]::FromFile($rf.File)
    $g.DrawImage($rimg, (New-Object System.Drawing.Rectangle ($pw + $gap), $labelH, $pw, $ph), $RightCrop[0], $RightCrop[1], $pw, $ph, [System.Drawing.GraphicsUnit]::Pixel)
    $rimg.Dispose()
    $g.DrawString($LeftLabel, $font, [System.Drawing.Brushes]::White, (New-Object System.Drawing.RectangleF 0, 0, $pw, $labelH), $fmt)
    $g.DrawString($RightLabel, $font, [System.Drawing.Brushes]::White, (New-Object System.Drawing.RectangleF ($pw + $gap), 0, $pw, $labelH), $fmt)
    $g.Dispose()
    $enc.Frames.Add((To-Wpf $canvas)); $canvas.Dispose()
}
$fs = [IO.File]::Create($Out); $enc.Save($fs); $fs.Dispose()
"wrote $Out with $($lefts.Count) frames"
