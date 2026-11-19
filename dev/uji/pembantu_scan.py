"""Fungsi olah pengganti untuk proses pekerja di uji (harus bisa diimpor oleh proses anak)."""
import os

from core import scanner


def olah_mati(data, akar):
    if data.startswith(b"MATI"):
        os._exit(1)
    return scanner.olah(data, akar)


def olah_disk_penuh(data, akar):
    raise OSError(28, "No space left on device")
