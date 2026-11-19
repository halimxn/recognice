import sqlite3
from pathlib import Path

MIGRASI = [
    """
    CREATE TABLE source(
        id INTEGER PRIMARY KEY,
        serial TEXT NOT NULL,
        akar_relatif TEXT NOT NULL,
        huruf_terakhir TEXT NOT NULL,
        label TEXT NOT NULL,
        terakhir_pindai INTEGER,
        UNIQUE(serial, akar_relatif, huruf_terakhir)
    );
    CREATE TABLE photo(
        id INTEGER PRIMARY KEY,
        source_id INTEGER NOT NULL REFERENCES source(id) ON DELETE CASCADE,
        rel TEXT NOT NULL,
        ukuran INTEGER NOT NULL,
        mtime_ns INTEGER NOT NULL,
        sha1 TEXT,
        lebar INTEGER NOT NULL DEFAULT 0,
        tinggi INTEGER NOT NULL DEFAULT 0,
        taken_at INTEGER NOT NULL DEFAULT 0,
        sumber_tanggal TEXT NOT NULL DEFAULT 'mtime',
        status TEXT NOT NULL,
        galat TEXT,
        UNIQUE(source_id, rel)
    );
    CREATE INDEX photo_urut ON photo(status, taken_at DESC, id DESC);
    CREATE INDEX photo_sha1 ON photo(sha1);
    """,
    """
    ALTER TABLE photo ADD COLUMN wajah_model TEXT;
    ALTER TABLE photo ADD COLUMN wajah_galat TEXT;
    CREATE TABLE face(
        id INTEGER PRIMARY KEY,
        photo_id INTEGER NOT NULL REFERENCES photo(id) ON DELETE CASCADE,
        x1 REAL NOT NULL, y1 REAL NOT NULL, x2 REAL NOT NULL, y2 REAL NOT NULL,
        titik BLOB NOT NULL,
        skor REAL NOT NULL,
        lebar_px REAL NOT NULL,
        tajam REAL NOT NULL,
        frontal REAL NOT NULL,
        kualitas REAL NOT NULL,
        embedding BLOB NOT NULL,
        model TEXT NOT NULL
    );
    CREATE INDEX face_photo ON face(photo_id);
    CREATE INDEX photo_wajah ON photo(status, wajah_model);
    """,
    """
    CREATE TABLE person(
        id INTEGER PRIMARY KEY,
        nama TEXT,
        tersembunyi INTEGER NOT NULL DEFAULT 0,
        dibuat INTEGER NOT NULL
    );
    ALTER TABLE face ADD COLUMN person_id INTEGER REFERENCES person(id) ON DELETE SET NULL;
    ALTER TABLE face ADD COLUMN state TEXT NOT NULL DEFAULT 'baru';
    CREATE TABLE batasan(
        face_a INTEGER NOT NULL REFERENCES face(id) ON DELETE CASCADE,
        face_b INTEGER NOT NULL REFERENCES face(id) ON DELETE CASCADE,
        jenis TEXT NOT NULL,
        PRIMARY KEY(face_a, face_b)
    );
    CREATE INDEX face_person ON face(person_id);
    """,
    """
    CREATE INDEX face_person_kualitas ON face(person_id, kualitas);
    """,
]
VERSI = len(MIGRASI)


def buka(jalur):
    Path(jalur).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(jalur, timeout=30)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA synchronous=NORMAL")
    versi = c.execute("PRAGMA user_version").fetchone()[0]
    for i, sql in enumerate(MIGRASI[versi:], versi + 1):
        try:
            c.executescript(f"BEGIN;\n{sql}\nPRAGMA user_version={i};\nCOMMIT;")
        except Exception:
            if c.in_transaction:
                c.rollback()  # setengah jadi berarti aplikasi tidak bisa dibuka lagi
            raise
    return c
