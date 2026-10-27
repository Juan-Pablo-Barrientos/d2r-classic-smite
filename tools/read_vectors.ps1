# Print a clip's vector tracks (foot IK targets, FK/IK weights, aim) sampled at their knots.
param([string]$Clip = '1hs_skill1', [string]$Source = "$PSScriptRoot\work\in\combined_animations.gr2", [switch]$Full)
. "$PSScriptRoot\lslib.ps1"

function Get-Series($curve) {
    # returns @(@{t; v}) for the 1-D curve types used by vector tracks
    $cd = $curve.CurveData
    $name = $cd.GetType().Name
    if ($name -eq 'DaConstant32f') { return , @([pscustomobject]@{ t = 0.0; v = [double]$cd.Controls[0] }) }
    if ($name -match '^DaK(8|16)uC(8|16)u$') {
        $knots = $cd.GetKnots()
        $n = $knots.Count
        $scale = $cd.ControlScaleOffsets[0]; $offset = $cd.ControlScaleOffsets[1]
        $out = for ($i = 0; $i -lt $n; $i++) { [pscustomobject]@{ t = [double]$knots[$i]; v = $cd.KnotsControls[$n + $i] * $scale + $offset } }
        return , @($out)
    }
    if ($name -eq 'DaK32fC32f') {
        $knots = $cd.Knots; $out = for ($i = 0; $i -lt $knots.Count; $i++) { [pscustomobject]@{ t = [double]$knots[$i]; v = [double]$cd.Controls[$i] } }
        return , @($out)
    }
    throw "unhandled curve type $name"
}

$anim = (Read-GR2 $Source).Animations | ? Name -eq $Clip
$tg = $anim.TrackGroups | ? Name -eq 'root'
foreach ($vt in $tg.VectorTracks | Sort-Object Name) {
    $s = Get-Series $vt.ValueCurve
    $vals = $s | % { $_.v }
    '{0,-15} {1,-13} n={2,-3} first={3,8:N3} min={4,8:N3} max={5,8:N3} last={6,8:N3}' -f $vt.Name, $vt.ValueCurve.CurveData.GetType().Name, $s.Count, $vals[0], ($vals | Measure -Minimum).Minimum, ($vals | Measure -Maximum).Maximum, $vals[-1]
    if ($Full) { '    ' + (($s | % { '{0:N2}:{1:N2}' -f $_.t, $_.v }) -join '  ') }
}
