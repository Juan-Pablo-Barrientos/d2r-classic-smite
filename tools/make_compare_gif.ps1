# Side-by-side comparison GIF: captured JPEG frames (left) next to the frames of an existing GIF (right),
# each with a label on top. gif_fix.py adds timing and looping afterwards.
param(
    [Parameter(Mandatory)][string]$Out,
    [Parameter(Mandatory)][string]$RightGif,
    [string]$LeftDir = "$PSScriptRoot\capture",
    [int]$LeftFromMs, [int]$StepMs = 40,
    [int[]]$LeftCrop = @(430, 110, 290, 330),
    [string]$LeftLabel = 'Original Diablo II', [string]$RightLabel = 'Classic Smite (HD)'
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationCore, WindowsBase, System.Drawing
Add-Type -AssemblyName System.Windows.Forms  # TextRenderer-free font metrics come from System.Drawing

function To-Drawing($bitmapSource) {
    $png = New-Object System.Windows.Media.Imaging.PngBitmapEncoder
    $png.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($bitmapSource))
    $ms = New-Object IO.MemoryStream; $png.Save($ms); $ms.Position = 0
    [System.Drawing.Bitmap]::new($ms)
}
function To-Wpf([System.Drawing.Bitmap]$bmp) {
    $ms = New-Object IO.MemoryStream; $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png); $ms.Position = 0
    $dec = New-Object System.Windows.Media.Imaging.PngBitmapDecoder $ms, 'PreservePixelFormat', 'OnLoad'
    $dec.Frames[0]
}

$rs = [IO.File]::OpenRead($RightGif)
$right = New-Object System.Windows.Media.Imaging.GifBitmapDecoder $rs, 'PreservePixelFormat', 'OnLoad'
$rs.Dispose()
$left = Get-ChildItem $LeftDir -Filter *.jpg | Sort-Object Name | % {
    [pscustomobject]@{ File = $_.FullName; Ms = [int][regex]::Match($_.Name, '_(\d+)ms').Groups[1].Value }
}

$pw = [math]::Max($LeftCrop[2], $right.Frames[0].PixelWidth); $ph = [math]::Max($LeftCrop[3], $right.Frames[0].PixelHeight)
$labelH = 28; $gap = 6
$font = New-Object System.Drawing.Font 'Segoe UI', 12, ([System.Drawing.FontStyle]::Bold)
$fmt = New-Object System.Drawing.StringFormat; $fmt.Alignment = 'Center'; $fmt.LineAlignment = 'Center'
$enc = New-Object System.Windows.Media.Imaging.GifBitmapEncoder

for ($i = 0; $i -lt $right.Frames.Count; $i++) {
    $canvas = New-Object System.Drawing.Bitmap (2 * $pw + $gap), ($ph + $labelH)
    $g = [System.Drawing.Graphics]::FromImage($canvas)
    $g.Clear([System.Drawing.Color]::FromArgb(13, 17, 23))
    # left: nearest captured frame
    $t = $LeftFromMs + $i * $StepMs
    $lf = $left | Sort-Object { [math]::Abs($_.Ms - $t) } | Select-Object -First 1
    $limg = [System.Drawing.Image]::FromFile($lf.File)
    $g.DrawImage($limg, (New-Object System.Drawing.Rectangle 0, $labelH, $LeftCrop[2], $LeftCrop[3]), $LeftCrop[0], $LeftCrop[1], $LeftCrop[2], $LeftCrop[3], [System.Drawing.GraphicsUnit]::Pixel)
    $limg.Dispose()
    # right: frame i of the existing GIF
    $rimg = To-Drawing $right.Frames[$i]
    $g.DrawImage($rimg, $pw + $gap, $labelH, $rimg.Width, $rimg.Height)
    $rimg.Dispose()
    $g.DrawString($LeftLabel, $font, [System.Drawing.Brushes]::White, (New-Object System.Drawing.RectangleF 0, 0, $pw, $labelH), $fmt)
    $g.DrawString($RightLabel, $font, [System.Drawing.Brushes]::White, (New-Object System.Drawing.RectangleF ($pw + $gap), 0, $pw, $labelH), $fmt)
    $g.Dispose()
    $enc.Frames.Add((To-Wpf $canvas))
    $canvas.Dispose()
}
$fs = [IO.File]::Create($Out); $enc.Save($fs); $fs.Dispose()
"wrote $Out with $($right.Frames.Count) frames"
