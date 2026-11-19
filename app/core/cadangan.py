"""Cadangan library.db dan pengaturan. Thumbnail bisa dibuat ulang, jadi tidak ikut."""
import os
import shutil
import sqlite3
import time
from pathlib import Path

from core import db

IKUT = ("pengaturan.json", "gold.json")
TANDA = "pulihkan.txt"


def buat(data, tujuan):
    data, folder = Path(data), Path(tujuan) / f"Recognice-cadangan-{time.strftime('%Y%m%d-%H%M%S')}"
    folder.mkdir(parents=True)
    asal, ke = sqlite3.connect(data / "library.db"), sqlite3.connect(folder / "library.db")
    try:
        asal.backup(ke)
    finally:
        ke.close()
        asal.close()
    for n in IKUT:
        if (data / n).exists():
            shutil.copy2(data / n, folder / n)
    return folder


def periksa(folder):
    p = Path(folder) / "library.db"
    try:
        c = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True)
        try:
            baik = c.execute("PRAGMA quick_check").fetchone()[0] == "ok"
            versi = c.execute("PRAGMA user_version").fetchone()[0]
        finally:
            c.close()
    except sqlite3.Error:
        raise ValueError("Berkas cadangan rusak.") from None
    if not baik:
        raise ValueError("Berkas cadangan rusak.")
    if versi > db.VERSI:
        raise ValueError("Cadangan dibuat oleh versi aplikasi yang lebih baru.")


def jadwalkan(data, folder):
    """Database sedang dipakai, jadi penggantian dilakukan saat aplikasi dibuka berikutnya."""
    periksa(folder)
    (Path(data) / TANDA).write_text(str(folder), encoding="utf-8")


def terapkan_bila_ada(data):
    data = Path(data)
    tanda = data / TANDA
    if not tanda.exists():
        return False
    folder = Path(tanda.read_text(encoding="utf-8").strip())
    periksa(folder)
    os.replace(data / "library.db", data / "library.db.sebelum-pulih")  # data lama tidak dibuang
    for akhiran in ("-wal", "-shm"):
        (data / f"library.db{akhiran}").unlink(missing_ok=True)
    shutil.copy2(folder / "library.db", data / "library.db")
    for n in IKUT:
        if (folder / n).exists():
            shutil.copy2(folder / n, data / n)
    tanda.unlink()
    return True
