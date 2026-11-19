"""Deteksi SCRFD, penyejajaran 5 titik, dan embedding ArcFace.

Mesin hitung: OpenVINO di kartu grafis Intel bila ada (diukur 3-6x lebih cepat, dev/bench/mesin_hitung.py),
ONNX Runtime di prosesor sebagai cadangan. Keduanya memakai berkas model yang sama.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

_RUNTIME = Path(__file__).resolve().parents[2] / "models" / "runtime"

STRIDE = (8, 16, 32)
ANCHOR_PER_SEL = 2
TEMPLAT_112 = np.array(
    [[38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366], [41.5493, 92.3655], [70.7299, 92.2041]],
    dtype=np.float32,
)


@dataclass
class Wajah:
    kotak: np.ndarray  # x1 y1 x2 y2 pada koordinat gambar masukan
    titik: np.ndarray  # 5 x 2
    skor: float


_dll_siap = False
_ov = False  # False = belum dicoba
_alat = None
# Ukuran kumpulan wajah yang dikompilasi; sisanya diisi nol, lebih dari 8 dipecah. Tiap ukuran memakan ±150 MB RAM
# di kartu grafis terpadu; (1, 4, 8) sama cepatnya dengan (1, 2, 4, 8, 16, 32) tetapi 0,8 lawan 1,8 GB (HASIL.md).
BUCKET = (1, 4, 8)


def _siapkan_dll():
    global _dll_siap
    if not _dll_siap and _RUNTIME.is_dir():
        os.add_dll_directory(str(_RUNTIME))  # Windows ini tanpa Visual C++ Redistributable
    _dll_siap = True


def _openvino():
    """Modul openvino, atau None bila tidak terpasang atau tidak bisa dimuat."""
    global _ov
    if _ov is False:
        _siapkan_dll()
        try:
            import openvino
            _ov = openvino
        except (ImportError, OSError):
            _ov = None
    return _ov


def pilih_alat():
    """'GPU' bila OpenVINO melihat kartu grafis Intel, selain itu 'ort' (ONNX Runtime di prosesor)."""
    global _alat
    ov = _openvino()
    if ov is None:
        return "ort"
    if _alat is None:
        try:
            _alat = "GPU" if "GPU" in ov.Core().available_devices else "ort"
        except Exception:  # driver kartu grafis bermasalah
            _alat = "ort"
    return _alat


class SesiOpenVINO:
    """Antarmuka seperti sesi ONNX Runtime. Tiap bentuk masukan dikompilasi sekali; hasilnya disimpan di `cache`."""

    def __init__(self, jalur, alat, cache=None, bentuk=(), kumpulan=None):
        """`bentuk`: daftar bentuk masukan yang langsung dikompilasi. `kumpulan`: ukuran kumpulan yang dikompilasi;
        kumpulan lain diisi nol sampai ukuran terdekat. None = bentuk masukan dipakai apa adanya (detektor)."""
        ov = _openvino()
        if ov is None:
            raise RuntimeError("OpenVINO tidak tersedia")
        self.jalur, self.alat = str(jalur), alat
        self.core = ov.Core()
        if cache:
            os.makedirs(cache, exist_ok=True)
            self.core.set_property({"CACHE_DIR": str(cache)})
        self.nama = self.core.read_model(self.jalur).inputs[0].get_any_name()
        self.kumpulan = kumpulan
        self._kompilasi = {}
        for b in bentuk:
            self._model(tuple(b))  # gagal di sini, bukan di tengah pekerjaan, supaya bisa jatuh ke prosesor

    def _model(self, bentuk):
        if bentuk not in self._kompilasi:
            m = self.core.read_model(self.jalur)
            m.reshape({m.inputs[0]: list(bentuk)})
            self._kompilasi[bentuk] = self.core.compile_model(m, self.alat, {"PERFORMANCE_HINT": "LATENCY"})
        return self._kompilasi[bentuk]

    def get_inputs(self):
        return [SimpleNamespace(name=self.nama)]

    def run(self, _keluaran, masukan):
        x = next(iter(masukan.values()))
        n = x.shape[0]
        ukuran = self.kumpulan or (n,)
        if n > ukuran[-1]:
            bagian = [self.run(None, {self.nama: x[i:i + ukuran[-1]]}) for i in range(0, n, ukuran[-1])]
            return [np.concatenate(k) for k in zip(*bagian)]
        b = next(u for u in ukuran if u >= n)
        if b != n:
            x = np.concatenate([x, np.zeros((b - n, *x.shape[1:]), x.dtype)])
        m = self._model(tuple(x.shape))
        hasil = m(np.ascontiguousarray(x))
        keluar = [np.asarray(hasil[o]) for o in m.outputs]
        return [k[:n] for k in keluar] if b != n else keluar


def nama_mesin(sesi):
    alat = getattr(sesi, "alat", None)  # hanya sesi OpenVINO yang punya
    return f"openvino-{alat}" if alat else "ort"


def buat_sesi(jalur, benang, alat="ort", cache=None, bentuk=(), kumpulan=None):
    if alat != "ort":
        try:
            return SesiOpenVINO(jalur, alat, cache, bentuk, kumpulan)
        except Exception:  # kartu grafis atau OpenVINO bermasalah: prosesor tetap bisa
            pass
    # Dimuat di sini, supaya galeri tetap terbuka bila ONNX Runtime bermasalah
    _siapkan_dll()
    import onnxruntime as ort

    op = ort.SessionOptions()
    op.intra_op_num_threads = benang
    op.inter_op_num_threads = 1
    op.log_severity_level = 3  # bentuk keluaran SCRFD dinyatakan statis di ONNX; peringatan tiap inferensi
    return ort.InferenceSession(str(jalur), op, providers=["CPUExecutionProvider"])


def urai_scrfd(keluaran, tinggi, lebar, ambang):
    """Keluaran 9 tensor: skor x3, jarak kotak x3, jarak titik x3, urut stride 8/16/32."""
    skor_s, kotak_s, titik_s = [], [], []
    for i, stride in enumerate(STRIDE):
        skor = np.asarray(keluaran[i]).reshape(-1)
        jarak = np.asarray(keluaran[i + 3]).reshape(-1, 4) * stride
        tk = np.asarray(keluaran[i + 6]).reshape(-1, 10) * stride
        t, l = tinggi // stride, lebar // stride
        y, x = np.mgrid[:t, :l]
        pusat = (np.stack([x, y], -1).reshape(-1, 2).astype(np.float32) + 0.5) * stride
        pusat = np.repeat(pusat, ANCHOR_PER_SEL, axis=0)
        pilih = skor >= ambang
        p, d = pusat[pilih], jarak[pilih]
        skor_s.append(skor[pilih])
        kotak_s.append(np.concatenate([p - d[:, :2], p + d[:, 2:]], axis=1))
        titik_s.append(tk[pilih].reshape(-1, 5, 2) + p[:, None, :])
    return np.concatenate(skor_s), np.concatenate(kotak_s), np.concatenate(titik_s)


def nms(kotak, skor, iou=0.4):
    urut = skor.argsort()[::-1]
    tetap = []
    luas = (kotak[:, 2] - kotak[:, 0]).clip(0) * (kotak[:, 3] - kotak[:, 1]).clip(0)
    while urut.size:
        i, urut = urut[0], urut[1:]
        tetap.append(i)
        if not urut.size:
            break
        x1 = np.maximum(kotak[i, 0], kotak[urut, 0])
        y1 = np.maximum(kotak[i, 1], kotak[urut, 1])
        x2 = np.minimum(kotak[i, 2], kotak[urut, 2])
        y2 = np.minimum(kotak[i, 3], kotak[urut, 3])
        irisan = (x2 - x1).clip(0) * (y2 - y1).clip(0)
        urut = urut[irisan / (luas[i] + luas[urut] - irisan + 1e-9) <= iou]
    return tetap


class Detektor:
    def __init__(self, jalur, benang=2, alat="ort", cache=None):
        # kanvas utama dan kanvas penghalusan (pipa_wajah.SISI_HALUS) dikompilasi sekarang, bukan di tengah pekerjaan
        self.sesi = buat_sesi(jalur, benang, alat, cache, [(1, 3, 640, 640), (1, 3, 192, 192)])
        self.masuk = self.sesi.get_inputs()[0].name

    def deteksi(self, gambar, sisi=640, ambang=0.5):
        """`gambar` PIL RGB. Kanvas persegi `sisi` (kelipatan 32), diisi dari kiri atas."""
        skala = min(sisi / gambar.width, sisi / gambar.height, 1.0)
        kecil = gambar.resize((max(1, round(gambar.width * skala)), max(1, round(gambar.height * skala))),
                              Image.Resampling.BILINEAR) if skala < 1 else gambar
        kanvas = np.zeros((sisi, sisi, 3), np.float32)
        kanvas[:kecil.height, :kecil.width] = np.asarray(kecil, np.float32)
        blob = ((kanvas - 127.5) / 128.0).transpose(2, 0, 1)[None]
        skor, kotak, titik = urai_scrfd(self.sesi.run(None, {self.masuk: blob}), sisi, sisi, ambang)
        if not len(skor):
            return []
        return [Wajah(kotak[i] / skala, titik[i] / skala, float(skor[i])) for i in nms(kotak, skor)]


def similaritas(asal, tujuan):
    """Umeyama: matriks 2x3 yang memetakan `asal` ke `tujuan` (tanpa pencerminan)."""
    m_a, m_t = asal.mean(0), tujuan.mean(0)
    a, t = asal - m_a, tujuan - m_t
    u, s, vt = np.linalg.svd(t.T @ a / len(asal))
    d = np.array([1.0, np.sign(np.linalg.det(u) * np.linalg.det(vt)) or 1.0])
    r = u @ np.diag(d) @ vt
    c = (s * d).sum() / (a ** 2).sum(1).mean()
    return np.hstack([c * r, (m_t - c * r @ m_a)[:, None]])


def sejajarkan(gambar, titik):
    m = similaritas(np.asarray(titik, np.float64), TEMPLAT_112.astype(np.float64))
    # PIL butuh pemetaan keluaran ke masukan
    inv = np.linalg.inv(np.vstack([m, [0, 0, 1]]))[:2].reshape(-1)
    return gambar.transform((112, 112), Image.Transform.AFFINE, tuple(inv), Image.Resampling.BILINEAR)


class Pengenal:
    def __init__(self, jalur, benang=2, alat="ort", cache=None):
        # semua ukuran kumpulan sekarang: kompilasi di tengah pekerjaan menahan foto pertama tiap ukuran
        self.sesi = buat_sesi(jalur, benang, alat, cache, [(b, 3, 112, 112) for b in BUCKET], BUCKET)
        self.masuk = self.sesi.get_inputs()[0].name

    def embed(self, wajah_112):
        """Daftar PIL RGB 112x112; hasil baris ternormalisasi L2."""
        blob = (np.stack([np.asarray(w, np.float32) for w in wajah_112]) - 127.5) / 127.5
        v = self.sesi.run(None, {self.masuk: blob.transpose(0, 3, 1, 2)})[0]
        return v / np.linalg.norm(v, axis=1, keepdims=True)
