$ErrorActionPreference = 'Stop'
$akar = Resolve-Path "$PSScriptRoot\..\.."
Set-Location $akar
$dist = "dist\Recognice"
# PyInstaller mengosongkan folder tujuan: data pemakai versi portabel dipindah dulu
$simpan = "dist\_data_simpan"
if (Test-Path "$dist\data") { Move-Item "$dist\data" $simpan }
try {
    & .venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --distpath dist --workpath build dev\kemas\recognice.spec
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller gagal" }
} finally {
    if (Test-Path $simpan) { New-Item -ItemType Directory -Force $dist | Out-Null; Move-Item $simpan "$dist\data" }
}
New-Item -ItemType Directory -Force "$dist\models\buffalo_l", "$dist\models\runtime" | Out-Null
Copy-Item models\buffalo_l\det_10g.onnx, models\buffalo_l\w600k_r50.onnx "$dist\models\buffalo_l"
Copy-Item models\runtime\*.dll "$dist\models\runtime"
Copy-Item models\MODEL.md "$dist\models"
Write-Host "Selesai: $dist\Recognice.exe"
