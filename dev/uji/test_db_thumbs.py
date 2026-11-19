import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "app"))
from core import db, thumbs


def test_versi_skema(tmp_path):
    c = db.buka(tmp_path / "a.db")
    assert c.execute("PRAGMA user_version").fetchone()[0] == db.VERSI
    assert c.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


def test_migrasi_idempoten(tmp_path):
    p = tmp_path / "a.db"
    c = db.buka(p)
    c.execute("INSERT INTO source(serial, akar_relatif, huruf_terakhir, label) VALUES ('s', 'x', 'E:', 'l')")
    c.commit()
    c.close()
    c = db.buka(p)
    assert c.execute("SELECT count(*) FROM source").fetchone()[0] == 1


def test_tinggi_256(tmp_path):
    thumbs.buat(Image.new("RGB", (3000, 2000)), tmp_path, "ab" * 20)
    im = Image.open(thumbs.jalur(tmp_path, "ab" * 20, 256))
    assert im.size == (384, 256)


def test_sisi_panjang_1024(tmp_path):
    thumbs.buat(Image.new("RGB", (2000, 3000)), tmp_path, "cd" * 20)
    assert max(Image.open(thumbs.jalur(tmp_path, "cd" * 20, 1024)).size) == 1024


def test_tidak_memperbesar(tmp_path):
    thumbs.buat(Image.new("RGB", (100, 80)), tmp_path, "ef" * 20)
    assert Image.open(thumbs.jalur(tmp_path, "ef" * 20, 256)).size == (100, 80)
    assert Image.open(thumbs.jalur(tmp_path, "ef" * 20, 1024)).size == (100, 80)
