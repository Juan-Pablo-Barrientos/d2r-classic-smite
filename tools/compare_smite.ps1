# Compare the Smite clip in a glTF (from Blender, fixed with fix_glb.py) against the game's original.
param([string]$Glb, [string]$Clip = '1hs_skill1', [string]$Reference, [switch]$ExactOnly)
. "$PSScriptRoot\lslib.ps1"

$b = Read-GLTF $Glb
Show-Root $b
foreach ($an in $b.Animations) { "anim '$($an.Name)' dur=$($an.Duration) step=$($an.TimeStep) tgs=$($an.TrackGroups.Count) tracks=$($an.TrackGroups[0].TransformTracks.Count)" }

if ($Reference) {
    $orig = (Read-GLTF $Reference).Animations[0].TrackGroups[0]
} else {
    $anims = Read-GR2 "$Scratch\work\in\combined_animations.gr2"
    $orig = ($anims.Animations | ? Name -eq $Clip).TrackGroups | ? Name -eq 'root'
}
$new = $b.Animations[0].TrackGroups[0]

function Nearest($kf, $t) { $kf.Keyframes.Values | Sort-Object { [math]::Abs($_.Time - $t) } | Select-Object -First 1 }

$maxR = 0; $maxT = 0; $worstR = ''; $worstT = ''; $missing = @()
foreach ($ot in $orig.TransformTracks) {
    $nt = $new.TransformTracks | ? Name -eq $ot.Name
    if (!$nt) { $missing += $ot.Name; continue }
    $ok = $ot.ToKeyframes(); $nk = $nt.ToKeyframes()
    # keys can carry rotation only or translation only, so interpolate each from its own keys
    $rotKeys = @($ok.Keyframes.Values | ? HasRotation | Sort-Object Time)
    $posKeys = @($ok.Keyframes.Values | ? HasTranslation | Sort-Object Time)
    function Bracket($keys, $t) {
        $i = 0; while ($i -lt $keys.Count - 2 -and $keys[$i + 1].Time -le $t) { $i++ }
        $k0 = $keys[$i]; $k1 = $keys[[math]::Min($i + 1, $keys.Count - 1)]
        $u = if ($k1.Time -gt $k0.Time) { [math]::Clamp(($t - $k0.Time) / ($k1.Time - $k0.Time), 0, 1) } else { 0 }
        $k0, $k1, [single]$u
    }
    foreach ($n in $nk.Keyframes.Values) {
        # evaluate the reference at this key's time (linear between its keys)
        $t = $n.Time
        if ($ExactOnly -and -not ($ok.Keyframes.Values | ? { [math]::Abs($_.Time - $t) -lt 0.004 })) { continue }
        $o = [pscustomobject]@{ HasRotation = $rotKeys.Count -gt 0; HasTranslation = $posKeys.Count -gt 0; Rotation = $null; Translation = $null }
        if ($o.HasRotation) { $r0, $r1, $u = Bracket $rotKeys $t; $o.Rotation = [OpenTK.Mathematics.Quaternion]::Slerp($r0.Rotation, $r1.Rotation, $u) }
        if ($o.HasTranslation) { $p0, $p1, $u = Bracket $posKeys $t; $o.Translation = [OpenTK.Mathematics.Vector3]::Lerp($p0.Translation, $p1.Translation, $u) }
        $script:compared++
        if ($o.HasRotation -and $n.HasRotation) {
            $p = $o.Rotation; $q = $n.Rotation
            $err = 1 - [math]::Abs($p.X * $q.X + $p.Y * $q.Y + $p.Z * $q.Z + $p.W * $q.W)
            if ($err -gt $maxR) { $maxR = $err; $worstR = "$($ot.Name)@$t" }
        }
        if ($o.HasTranslation -and $n.HasTranslation) {
            $e = ($o.Translation - $n.Translation).Length
            if ($e -gt $maxT) { $maxT = $e; $worstT = "$($ot.Name)@$t" }
        }
    }
}
"keys compared: $compared"
"missing tracks: $($missing.Count) $($missing -join ',')"
"max rotation error (1-|dot|): $maxR at $worstR"
"max translation error: $maxT at $worstT"
