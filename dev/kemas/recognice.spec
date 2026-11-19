# Mode folder portabel. Model disalin terpisah oleh kemas.ps1, supaya bisa diganti tanpa membangun ulang.
from pathlib import Path

from importlib.util import find_spec

akar = Path(SPECPATH).parents[1]
# OpenVINO memuat plugin saat berjalan, jadi PyInstaller tidak melihatnya. Hanya kartu grafis dan pembaca ONNX;
# plugin prosesor dan NPU (±150 MB) tidak dipakai: tanpa kartu grafis, ONNX Runtime yang bekerja.
ov_libs = Path(find_spec("openvino").submodule_search_locations[0]) / "libs"  # diimpor butuh DLL VC++ dari models/runtime
OV_PERLU = ["openvino.dll", "openvino_intel_gpu_plugin.dll", "openvino_onnx_frontend.dll", "openvino_ir_frontend.dll",
            "tbb12.dll", "tbbbind_2_5.dll", "tbbmalloc.dll", "tbbmalloc_proxy.dll", "cache.json"]
a = Analysis(
    [str(akar / "app/main.py")],
    pathex=[str(akar / "app")],
    binaries=[(str(ov_libs / n), "openvino/libs") for n in OV_PERLU],
    datas=[(str(akar / "app/ui/qml"), "ui/qml")],
    hiddenimports=["pillow_heif", "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtQuickControls2", "openvino"],
    excludes=["pytest", "tkinter", "openvino.torch", "openvino.frontend.pytorch", "openvino.frontend.tensorflow",
              "openvino.frontend.jax", "openvino.frontend.paddle", "openvino.tools", "torch", "tensorflow"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Recognice", console=False, icon=str(akar / "dev/kemas/recognice.ico"))
coll = COLLECT(exe, a.binaries, a.datas, name="Recognice")
