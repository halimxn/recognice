"""Menyalin foto ke folder lain. Foto asli hanya dibaca dan berkas yang sudah ada tidak pernah ditimpa."""
import json
import os
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from core import library, scanner


@dataclass
class HasilEkspor:
    disalin: int = 0
    gagal: int = 0
    tak_terhubung: int = 0
    dibatalkan: bool = False


def _di_dalam(jalur, akar):
    a, b = os.path.normcase(os.path.abspath(jalur)), os.path.normcase(os.path.abspath(akar))
    return a == b or a.startswith(b.rstrip("\\") + "\\")


def _salin(asli, tujuan, nama):
    """Salin lewat nama sementara; `os.rename` di Windows gagal bila nama sudah ada."""
    dasar, ext = os.path.splitext(nama)
    sementara = os.path.join(tujuan, f".{dasar}.{os.getpid()}.tmp")
    shutil.copy2(scanner._panjang(asli), sementara)
    try:
        if os.path.getsize(sementara) != os.path.getsize(scanner._panjang(asli)):
            raise OSError("ukuran salinan berbeda")
        i = 0
        while True:
            calon = os.path.join(tujuan, f"{dasar}_{i}{ext}" if i else nama)
            try:
                os.rename(sementara, calon)
                return calon
            except FileExistsError:
                i += 1
    finally:
        if os.path.exists(sementara):
            os.remove(sementara)


def ekspor(c, saring, tujuan, folder_jurnal, batal=None, lapor=None):
    foto = library.semua_foto(c, saring)
    akar = {sid: library.akar_sumber(c, sid) for sid in {f.source_id for f in foto}}
    for a in akar.values():
        if a and _di_dalam(tujuan, a):
            raise ValueError("Folder tujuan berada di dalam sumber foto.")
    os.makedirs(tujuan, exist_ok=True)
    Path(folder_jurnal).mkdir(parents=True, exist_ok=True)
    r = HasilEkspor()
    with open(Path(folder_jurnal) / f"ekspor-{time.strftime('%Y%m%d-%H%M%S')}.jsonl", "a", encoding="utf-8") as j:
        def catat(**isi):
            j.write(json.dumps(isi, ensure_ascii=False) + "\n")
            j.flush()

        for n, f in enumerate(foto, 1):
            if batal and batal.is_set():
                r.dibatalkan = True
                break
            if not akar[f.source_id]:
                r.tak_terhubung += 1
                continue
            asli = os.path.join(akar[f.source_id], f.jalur_rel.replace("/", "\\"))
            catat(aksi="mulai", asal=asli)
            try:
                hasil = _salin(asli, tujuan, f.jalur_rel.rsplit("/", 1)[-1])
                catat(aksi="selesai", asal=asli, tujuan=hasil)
                r.disalin += 1
            except OSError as e:
                catat(aksi="gagal", asal=asli, galat=repr(e)[:200])
                r.gagal += 1
            if lapor:
                lapor(n, len(foto))
    return r
