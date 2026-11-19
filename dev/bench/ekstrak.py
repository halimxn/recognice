"""Ekstrak hanya berkas ONNX yang dibutuhkan, tanpa memakai jalur dari arsip."""
import hashlib
import sys
import zipfile
from pathlib import Path

arsip, tujuan, *nama = sys.argv[1:]
Path(tujuan).mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(arsip) as z:
    print([(i.filename, round(i.file_size / 1e6, 1)) for i in z.infolist() if not i.is_dir()])
    for i in z.infolist():
        dasar = i.filename.replace("\\", "/").rsplit("/", 1)[-1]
        if dasar in nama:
            p = Path(tujuan) / dasar
            p.write_bytes(z.read(i))
            print(dasar, hashlib.sha256(p.read_bytes()).hexdigest())
