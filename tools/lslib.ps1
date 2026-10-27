# Helpers for driving LSLib.dll directly (dot-source this file).
# Working files live next to the scripts: work\ (extracted .gr2s, exports, rebuilds) and lslib\ (LSLib's
# ExportTool zip unpacked as lslib\tool, with Packed\granny2.dll copied into Packed\Tools).
$Scratch = $PSScriptRoot
$LSTools = "$Scratch\lslib\tool\Packed\Tools"
$env:PATH = "$LSTools;$env:PATH"  # granny2.dll / LSLibNative.dll
[Environment]::CurrentDirectory = $LSTools
[void][Runtime.InteropServices.NativeLibrary]::Load("$LSTools\granny2.dll")
[void][Runtime.InteropServices.NativeLibrary]::Load("$LSTools\LSLibNative.dll")
$LSLib = [Reflection.Assembly]::LoadFrom("$LSTools\LSLib.dll")
$Flags = [Reflection.BindingFlags]'NonPublic,Public,Instance'

function New-Exporter {
    $ex = New-Object LSLib.Granny.Model.Exporter
    $ex.Options = New-Object LSLib.Granny.Model.ExporterOptions
    $ex.Options.LoadGameSettings([LSLib.LS.Enums.Game]::BaldursGate3)
    $ex
}

function Read-GR2([string]$path) {
    $ex = New-Exporter
    [LSLib.Granny.Model.Exporter].GetMethod('LoadGR2', $Flags).Invoke($ex, @($path))
}

function Read-GLTF([string]$path) {
    $ex = New-Exporter
    [LSLib.Granny.Model.Exporter].GetMethod('LoadGLTF', $Flags).Invoke($ex, @($path))
}

function Write-GR2([string]$path, $root) {
    $ex = New-Exporter
    [LSLib.Granny.Model.Exporter].GetMethod('SaveGR2', $Flags).Invoke($ex, @($path, $root))
}

function Show-Root($root) {
    "skeletons: $($root.Skeletons.Count)  models: $($root.Models.Count)  meshes: $($root.Meshes.Count)  animations: $($root.Animations.Count)  trackgroups: $($root.TrackGroups.Count)"
    foreach ($s in $root.Skeletons) { "  skeleton '$($s.Name)' bones=$($s.Bones.Count)" }
    foreach ($m in $root.Models) { "  model '$($m.Name)' skeleton='$($m.Skeleton.Name)' bindings=$($m.MeshBindings.Count)" }
}
