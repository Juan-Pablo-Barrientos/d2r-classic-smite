# Turn captured frames into a GIF: frames nearest to FromMs, FromMs+StepMs, ... up to ToMs, cropped.
# WPF's GifBitmapEncoder writes the frames (with its own palette per frame) but no timing or loop
# info; gif_fix.py adds those afterwards.
param(
    [Parameter(Mandatory)][string]$Out,
    [int]$FromMs, [int]$ToMs,
    [int]$StepMs = 40,
    [int[]]$Crop = @(430, 110, 290, 330),
    [string]$InDir = "$PSScriptRoot\capture"
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName PresentationCore, WindowsBase
$frames = Get-ChildItem $InDir -Filter *.jpg | Sort-Object Name | % {
    [pscustomobject]@{ File = $_.FullName; Ms = [int][regex]::Match($_.Name, '_(\d+)ms').Groups[1].Value }
}
$enc = New-Object System.Windows.Media.Imaging.GifBitmapEncoder
$rect = New-Object System.Windows.Int32Rect $Crop[0], $Crop[1], $Crop[2], $Crop[3]
$used = @()
for ($t = $FromMs; $t -le $ToMs; $t += $StepMs) {
    $f = $frames | Sort-Object { [math]::Abs($_.Ms - $t) } | Select-Object -First 1
    $stream = [IO.File]::OpenRead($f.File)
    $dec = New-Object System.Windows.Media.Imaging.JpegBitmapDecoder $stream, 'PreservePixelFormat', 'OnLoad'
    $stream.Dispose()
    $cropped = New-Object System.Windows.Media.Imaging.CroppedBitmap $dec.Frames[0], $rect  # not $crop: PowerShell names ignore case
    $enc.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($cropped))
    $used += $f.Ms
}
$fs = [IO.File]::Create($Out)
$enc.Save($fs)
$fs.Dispose()
"wrote $Out with $($used.Count) frames ($($used[0])..$($used[-1]) ms)"
