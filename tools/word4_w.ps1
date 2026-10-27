# Read the 4th (w) component of each mesh's Word4 positions straight from the decompressed GR2 section.
param([string[]]$Parts = @('legs_med_lod0', 'head_lod0', 'larm_med_lod0', 'torso_lit_lod0', 'torso_med_lod0', 'rarm_med_lod0', 'special1_med_lod0', 'special2_med_lod0'))
. "$PSScriptRoot\lslib.ps1"
$nat = [AppDomain]::CurrentDomain.GetAssemblies() | ? { $_.GetName().Name -eq 'LSLibNative' }
if (!$nat) { $nat = [Reflection.Assembly]::LoadFrom("$LSTools\LSLibNative.dll") }
$decompress = $nat.GetType('LSLib.Native.Granny2Compressor').GetMethod('Decompress4')

function Get-Section0([string]$path) {
    $b = [IO.File]::ReadAllBytes($path)
    $secoff = [BitConverter]::ToUInt32($b, 0x2C)
    $c, $off, $size, $dsize = 0..3 | % { [BitConverter]::ToUInt32($b, 0x20 + $secoff + $_ * 4) }
    $data = [byte[]]::new($size); [Array]::Copy($b, $off, $data, 0, $size)
    if ($c -eq 0) { return $data }
    $decompress.Invoke($null, @($data, [int]$dsize))
}

# Dump each part's raw section plus its meshes' first positions; word4_w.py does the byte search.
$outDir = "$Scratch\work\raw"; New-Item -ItemType Directory -Force $outDir | Out-Null
$targets = @()
foreach ($p in $Parts) {
    $path = "$Scratch\work\parts\$p.gr2"
    [IO.File]::WriteAllBytes("$outDir\$p.sec0", (Get-Section0 $path))
    foreach ($mesh in (Read-GR2 $path).Meshes) {
        $v0 = $mesh.PrimaryVertexData.Vertices[0].Position
        $targets += [pscustomobject]@{ part = $p; mesh = $mesh.Name; count = $mesh.PrimaryVertexData.Vertices.Count; x = $v0.X; y = $v0.Y; z = $v0.Z }
    }
}
$targets | ConvertTo-Json | Set-Content "$outDir\targets.json"
"dumped $($targets.Count) meshes to $outDir"
