from pathlib import Path

from PIL import Image, ImageDraw

KECIL = 256
BESAR = 1024


def jalur(akar, sha1, ukuran):
    return Path(akar) / sha1[:2] / f"{sha1}.{ukuran}.jpg"


def buat(gambar, akar, sha1):
    """`KECIL` = tinggi, supaya baris galeri setinggi itu tetap tajam; `BESAR` = sisi panjang."""
    tujuan = jalur(akar, sha1, BESAR)
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    besar = gambar.copy()
    besar.thumbnail((BESAR, BESAR), Image.Resampling.BICUBIC, reducing_gap=2.0)
    besar.save(tujuan, "JPEG", quality=82)
    kecil = besar
    if besar.height > KECIL:
        kecil = besar.resize((max(1, round(besar.width * KECIL / besar.height)), KECIL), Image.Resampling.BICUBIC,
                             reducing_gap=2.0)
    kecil.save(jalur(akar, sha1, KECIL), "JPEG", quality=78)


def potong_bulat(akar, sha1, kotak, sisi=192):
    """Potongan persegi bertepi di sekitar wajah, dengan alfa lingkaran. `kotak` relatif terhadap pratinjau."""
    with Image.open(jalur(akar, sha1, BESAR)) as im:
        im = im.convert("RGB")
    x1, y1, x2, y2 = kotak[0] * im.width, kotak[1] * im.height, kotak[2] * im.width, kotak[3] * im.height
    s = max(max(x2 - x1, y2 - y1) * 1.5, 8)
    s = min(s, im.width, im.height)
    kiri = min(max((x1 + x2 - s) / 2, 0), im.width - s)
    atas = min(max((y1 + y2 - s) / 2, 0), im.height - s)
    hasil = im.crop((round(kiri), round(atas), round(kiri + s), round(atas + s))).resize((sisi, sisi), Image.Resampling.BICUBIC)
    topeng = Image.new("L", (sisi * 4, sisi * 4), 0)
    ImageDraw.Draw(topeng).ellipse((0, 0, sisi * 4 - 1, sisi * 4 - 1), fill=255)
    hasil.putalpha(topeng.resize((sisi, sisi), Image.Resampling.LANCZOS))
    return hasil
