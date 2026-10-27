# Export one Paladin clip as glTF for Blender: full skeleton + body meshes + the clip's 'root' track group.
param(
    [string]$Clip = '1hs_skill1',
    [string]$Out = "$PSScriptRoot\work\glb\$Clip.gltf",
    [string[]]$Parts = @('head_lod0', 'torso_med_lod0', 'legs_med_lod0', 'larm_med_lod0', 'rarm_med_lod0', 'special1_med_lod0', 'special2_med_lod0'),
    [string]$Source = "$PSScriptRoot\work\in\combined_animations.gr2"
)
. "$PSScriptRoot\lslib.ps1"

$root = Read-GR2 "$Scratch\work\in\paladin_skeleton.gr2"
$model = $root.Models[0]
if (!$root.Meshes) { $root.Meshes = [Collections.Generic.List[LSLib.Granny.Model.Mesh]]::new() }
if (!$model.MeshBindings) { $model.MeshBindings = [Collections.Generic.List[LSLib.Granny.Model.MeshBinding]]::new() }
$scales = Get-Content "$Scratch\work\raw\scales.json" -Raw | ConvertFrom-Json -AsHashtable
foreach ($p in $Parts) {
    $part = Read-GR2 "$Scratch\work\parts\$p.gr2"
    foreach ($m in $part.Meshes) {
        # D2R's Word4 positions carry a per-mesh scale in w that LSLib drops (see word4_w.py)
        $s = $scales["$p/$($m.Name)"]
        if (!$s) { throw "no Word4 scale for $p/$($m.Name); run word4_w.ps1 + word4_w.py for it" }
        foreach ($v in $m.PrimaryVertexData.Vertices) { $v.Position = $v.Position * [single]$s }
        if (!$m.ExtendedData) { $m.ExtendedData = [LSLib.Granny.Model.DivinityMeshExtendedData]::Make() }
        if (!$m.ExtendedData.UserMeshProperties) { $m.ExtendedData.UserMeshProperties = [LSLib.Granny.Model.DivinityMeshExtendedData]::Make().UserMeshProperties }
        $root.Meshes.Add($m)
        $mb = New-Object LSLib.Granny.Model.MeshBinding; $mb.Mesh = $m
        $model.MeshBindings.Add($mb)
    }
}

$src = (Read-GR2 $Source).Animations | ? Name -eq $Clip
$tg = $src.TrackGroups | ? Name -eq 'root'
$a = New-Object LSLib.Granny.Model.Animation
foreach ($f in 'Name', 'Duration', 'TimeStep', 'Oversampling', 'DefaultLoopCount', 'Flags', 'ExtendedData') { $a.$f = $src.$f }
$a.TrackGroups = [Collections.Generic.List[LSLib.Granny.Model.TrackGroup]]::new(); $a.TrackGroups.Add($tg)
$root.Animations = [Collections.Generic.List[LSLib.Granny.Model.Animation]]::new(); $root.Animations.Add($a)
$root.TrackGroups = [Collections.Generic.List[LSLib.Granny.Model.TrackGroup]]::new(); $root.TrackGroups.Add($tg)

$ex = New-Exporter
$ex.Options.OutputPath = $Out
$ex.Options.OutputFormat = [LSLib.Granny.Model.ExportFormat]::GLTF
[LSLib.Granny.Model.Exporter].GetMethod('SaveGLTF', $Flags).Invoke($ex, @($root, $ex.Options))
"wrote $Out ($($root.Meshes.Count) meshes)"
