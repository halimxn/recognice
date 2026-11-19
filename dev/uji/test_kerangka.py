import ast
import os
import sys
from pathlib import Path

AKAR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(AKAR / "app"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_qml_terbuka_tanpa_galat(tmp_path):
    from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    from PySide6.QtGui import QGuiApplication

    import main

    galat = []

    def tangkap(jenis, _konteks, pesan):
        if jenis != QtMsgType.QtDebugMsg:
            galat.append(pesan)

    lama = qInstallMessageHandler(tangkap)
    try:
        app = QGuiApplication.instance() or QGuiApplication([])
        mesin = main.buat_mesin_qml(tmp_path, mulai_wajah=False)
        app.processEvents()
        assert mesin.rootObjects(), galat
        assert mesin.rootObjects()[0].property("title") == "Recognice"
        # penanda offscreen soal font/DPI bukan galat QML
        assert not [g for g in galat if "qml" in g.lower()], galat
    finally:
        qInstallMessageHandler(lama)


def test_core_tanpa_qt():
    for berkas in (AKAR / "app" / "core").rglob("*.py"):
        for simpul in ast.walk(ast.parse(berkas.read_text(encoding="utf-8"))):
            nama = []
            if isinstance(simpul, ast.Import):
                nama = [a.name for a in simpul.names]
            elif isinstance(simpul, ast.ImportFrom):
                nama = [simpul.module or ""]
            assert not any(n.startswith("PySide6") for n in nama), berkas
