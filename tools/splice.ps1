# Put an edited clip (Blender .glb, fixed with fix_glb.py) back into the Paladin's combined.animations.
# Tracks Blender exported replace the clip's 'root' track group tracks of the same name; the rest stay.
# With -Feet (make_smite.py's <glb>.feet.json), the clip's foot IK targets are rewritten too: the game
# plants the feet with its own IK aimed by the L/R_IK_position vector tracks, so without this the feet
# stay on the original clip's footwork whatever the leg bones do.
param(
    [Parameter(Mandatory)][string]$Glb,
    [Parameter(Mandatory)][string]$Out,
    [string[]]$Clips = @('1hs_skill1'),
    [string]$Source = "$PSScriptRoot\work\in\combined_animations.gr2",
    [string]$Feet
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lslib.ps1"

$edited = (Read-GLTF $Glb).Animations[0]
$newTracks = @{}
foreach ($t in $edited.TrackGroups[0].TransformTracks) { $newTracks[$t.Name] = $t }

function New-LinearCurve([double[]]$times, [double[]]$values) {
    # uncompressed 1-D curve (Granny DaK32fC32f, format 1), linear between the samples
    $cd = New-Object LSLib.Granny.Model.CurveData.DaK32fC32f
    $cd.CurveDataHeader_DaK32fC32f = New-Object LSLib.Granny.Model.CurveData.CurveDataHeader
    $cd.CurveDataHeader_DaK32fC32f.Format = 1
    $cd.CurveDataHeader_DaK32fC32f.Degree = 1
    $cd.Knots = [Collections.Generic.List[single]]::new()
    $cd.Controls = [Collections.Generic.List[single]]::new()
    for ($i = 0; $i -lt $times.Count; $i++) { $cd.Knots.Add([single]$times[$i]); $cd.Controls.Add([single]$values[$i]) }
    $cd
}

$footCurves = $null
if ($Feet) {
    $fj = Get-Content $Feet -Raw | ConvertFrom-Json
    $t = [double[]]($fj.frames | % { $_.t })
    # Blender (x, y, z) with z up and -y forward -> Granny (x, z, -y), matching the original tracks
    $footCurves = @{}
    foreach ($side in 'L', 'R') {
        $footCurves["${side}_IK_positionX"] = [double[]]($fj.frames | % { $_.$side[0] })
        $footCurves["${side}_IK_positionY"] = [double[]]($fj.frames | % { $_.$side[2] })
        $footCurves["${side}_IK_positionZ"] = [double[]]($fj.frames | % { -$_.$side[1] })
    }
}

$root = Read-GR2 $Source
foreach ($clip in $Clips) {
    $anim = $root.Animations | ? Name -eq $clip
    if (!$anim) { throw "clip '$clip' not found" }
    if ([math]::Abs($anim.Duration - $edited.Duration) -gt 0.001) {
        Write-Warning "$clip lasts $($anim.Duration)s but the edit lasts $($edited.Duration)s; the game's timing comes from its own frame data, so keep the length the same."
    }
    $tg = $anim.TrackGroups | ? Name -eq 'root'
    $replaced = 0
    for ($i = 0; $i -lt $tg.TransformTracks.Count; $i++) {
        $old = $tg.TransformTracks[$i]
        $new = $newTracks[$old.Name]
        if (!$new) { continue }
        $new.Flags = $old.Flags
        $new.ParentAnimation = $anim
        $tg.TransformTracks[$i] = $new  # same slot keeps Granny's track order and LOD error list aligned
        $replaced++
    }
    $unused = $newTracks.Keys | ? { -not ($tg.TransformTracks | ? Name -eq $_) }
    "${clip}: replaced $replaced of $($tg.TransformTracks.Count) tracks" + $(if ($unused) { "; not in clip: $($unused -join ', ')" })
    if ($footCurves) {
        $done = @()
        foreach ($vt in $tg.VectorTracks) {
            if ($footCurves.ContainsKey($vt.Name)) {
                $vt.ValueCurve.CurveData = New-LinearCurve $t $footCurves[$vt.Name]
                $done += $vt.Name
            }
        }
        if ($done.Count -ne 6) { throw "${clip}: expected 6 foot IK tracks, rewrote $($done.Count) ($($done -join ', '))" }
        "${clip}: rewrote foot IK targets ($($done -join ', '))"
        # aim_location is where the original swing aims (it dips to the knees, then rises over the head);
        # the game's melee aim layer bends the upper body/weapon arm with it. Hold it at the resting aim point
        # (straight ahead at head height) so it doesn't pull this animation toward the old swing.
        foreach ($vt in $tg.VectorTracks | ? Name -like 'aim_location?') {
            $cd = $vt.ValueCurve.CurveData
            $rest = switch -regex ($cd.GetType().Name) {
                '^DaConstant32f$' { [double]$cd.Controls[0] }
                '^DaK(8|16)uC(8|16)u$' { $cd.KnotsControls[$cd.GetKnots().Count] * $cd.ControlScaleOffsets[0] + $cd.ControlScaleOffsets[1] }
                '^DaK32fC32f$' { [double]$cd.Controls[0] }
                default { throw "unhandled aim curve type $_" }
            }
            $vt.ValueCurve.CurveData = New-LinearCurve @(0.0, [double]$anim.Duration) @($rest, $rest)
            "${clip}: $($vt.Name) held at $([math]::Round($rest, 3))"
        }
    }
}

Write-GR2 $Out $root
"wrote $Out"
