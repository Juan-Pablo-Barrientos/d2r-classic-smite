# Crop captured frames around the character and tile them into labelled contact sheets.
param(
    [string]$InDir = "$PSScriptRoot\capture",
    [string]$OutPrefix = "$PSScriptRoot\render\ingame",
    [int]$Step = 3,                       # use every Nth captured frame
    [int[]]$Crop = @(390, 150, 340, 300), # x, y, w, h inside the captured image
    [int]$Cols = 12, [int]$Rows = 4, [double]$Scale = 1.0,
    [int]$FromMs = 0, [int]$ToMs = [int]::MaxValue
)
Add-Type -AssemblyName System.Drawing
$files = Get-ChildItem $InDir -Filter *.jpg | Sort-Object Name | Where-Object {
    $ms = [int][regex]::Match($_.Name, '_(\d+)ms').Groups[1].Value
    $ms -ge $FromMs -and $ms -le $ToMs
}
$picked = for ($i = 0; $i -lt $files.Count; $i += $Step) { $files[$i] }
$tw = [int]($Crop[2] * $Scale); $th = [int]($Crop[3] * $Scale)
$font = New-Object System.Drawing.Font 'Consolas', 11
$per = $Cols * $Rows
for ($s = 0; $s * $per -lt $picked.Count; $s++) {
    $sheet = New-Object System.Drawing.Bitmap ($tw * $Cols), ($th * $Rows)
    $g = [System.Drawing.Graphics]::FromImage($sheet)
    $g.Clear([System.Drawing.Color]::Black)
    for ($k = 0; $k -lt $per -and $s * $per + $k -lt $picked.Count; $k++) {
        $f = $picked[$s * $per + $k]
        $img = [System.Drawing.Image]::FromFile($f.FullName)
        $dst = New-Object System.Drawing.Rectangle (($k % $Cols) * $tw), ([math]::Floor($k / $Cols) * $th), $tw, $th
        $g.DrawImage($img, $dst, $Crop[0], $Crop[1], $Crop[2], $Crop[3], [System.Drawing.GraphicsUnit]::Pixel)
        $img.Dispose()
        $ms = [regex]::Match($f.Name, '_(\d+)ms').Groups[1].Value
        $g.DrawString("$([int]$ms)ms", $font, [System.Drawing.Brushes]::Yellow, $dst.X + 3, $dst.Y + 3)
        $g.DrawRectangle([System.Drawing.Pens]::DimGray, $dst)
    }
    $out = '{0}_{1}.png' -f $OutPrefix, $s
    $sheet.Save($out, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $sheet.Dispose()
    "wrote $out"
}
