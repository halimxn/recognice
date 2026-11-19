"""Bilah judul buatan sendiri yang tetap berperilaku seperti jendela Windows.

Windows yang mengurus geser, ubah ukuran, Aero Snap, dan menu Snap Layouts; aplikasi hanya
menjawab WM_NCHITTEST "bagian jendela mana yang ada di titik ini".
"""
import ctypes
from ctypes import wintypes

from PySide6.QtCore import Property, QAbstractNativeEventFilter, QCoreApplication, QMetaObject, QObject, QPoint, Q_ARG, Q_RETURN_ARG, Qt, Signal, Slot
from PySide6.QtGui import QGuiApplication

TEPI = 5
TINGGI_JUDUL = 48  # sama dengan Theme.tinggiJudul

HTCLIENT, HTCAPTION, HTMAXBUTTON = 1, 2, 9
HTLEFT, HTRIGHT, HTTOP, HTTOPLEFT, HTTOPRIGHT, HTBOTTOM, HTBOTTOMLEFT, HTBOTTOMRIGHT = 10, 11, 12, 13, 14, 15, 16, 17

WM_NCCALCSIZE, WM_NCHITTEST, WM_NCMOUSEMOVE, WM_NCLBUTTONDOWN, WM_NCLBUTTONUP, WM_NCMOUSELEAVE = 0x83, 0x84, 0xA0, 0xA1, 0xA2, 0x2A2
GWL_STYLE, WS_CAPTION, WS_THICKFRAME, WS_MINIMIZEBOX, WS_MAXIMIZEBOX, WS_SYSMENU = -16, 0xC00000, 0x40000, 0x20000, 0x10000, 0x80000
SWP_GANTI_BINGKAI = 0x0027  # FRAMECHANGED | NOMOVE | NOSIZE | NOZORDER
SM_CXSIZEFRAME, SM_CXPADDEDBORDER = 32, 92
DWMWA_WINDOW_CORNER_PREFERENCE = 33


def kode_hit(x, y, lebar, tinggi, tepi, tinggi_judul, kontrol, maksimal):
    """Kode WM_NCHITTEST untuk titik (x, y) di dalam jendela. `kontrol`: "", "kontrol", atau "maks"."""
    if not maksimal:
        kiri, kanan, atas, bawah = x < tepi, x >= lebar - tepi, y < tepi, y >= tinggi - tepi
        if atas and kiri:
            return HTTOPLEFT
        if atas and kanan:
            return HTTOPRIGHT
        if bawah and kiri:
            return HTBOTTOMLEFT
        if bawah and kanan:
            return HTBOTTOMRIGHT
        if kiri:
            return HTLEFT
        if kanan:
            return HTRIGHT
        if atas:
            return HTTOP
        if bawah:
            return HTBOTTOM
    if y < tinggi_judul:
        return HTMAXBUTTON if kontrol == "maks" else HTCLIENT if kontrol else HTCAPTION
    return HTCLIENT


class _NCCALCSIZE(ctypes.Structure):
    _fields_ = [("rgrc", wintypes.RECT * 3), ("lppos", ctypes.c_void_p)]


class _Filter(QAbstractNativeEventFilter):
    def __init__(self, bingkai):
        super().__init__()
        self.b = bingkai

    def nativeEventFilter(self, jenis, pesan):
        msg = wintypes.MSG.from_address(int(pesan))
        if msg.hWnd != self.b.hwnd or msg.message not in (WM_NCCALCSIZE, WM_NCHITTEST, WM_NCMOUSEMOVE, WM_NCLBUTTONDOWN, WM_NCLBUTTONUP, WM_NCMOUSELEAVE):
            return False, 0
        try:
            return self.b.tangani(msg)
        except Exception:  # pengecualian di sini menjatuhkan seluruh aplikasi
            return False, 0


class Bingkai(QObject):
    berubah = Signal()

    def __init__(self):
        super().__init__()
        self.hwnd = None
        self._win = None
        self._filter = None
        self._sorot = self._tekan = False

    @Property(bool, notify=berubah)
    def maksDisorot(self):
        return self._sorot

    @Property(bool, notify=berubah)
    def maksDitekan(self):
        return self._tekan

    def _set(self, sorot, tekan):
        if (sorot, tekan) != (self._sorot, self._tekan):
            self._sorot, self._tekan = sorot, tekan
            self.berubah.emit()

    def pasang(self, win):
        if QGuiApplication.platformName() != "windows":
            return
        self._win = win
        self.hwnd = int(win.winId())
        u = ctypes.windll.user32
        u.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        u.SetWindowLongPtrW.argtypes = (wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t)
        gaya = u.GetWindowLongPtrW(wintypes.HWND(self.hwnd), GWL_STYLE)
        # Gaya ini yang memberi bayangan, sudut bulat, animasi, dan Snap dari Windows
        u.SetWindowLongPtrW(wintypes.HWND(self.hwnd), GWL_STYLE, gaya | WS_CAPTION | WS_THICKFRAME | WS_MINIMIZEBOX | WS_MAXIMIZEBOX | WS_SYSMENU)
        nilai = ctypes.c_int(2)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(wintypes.HWND(self.hwnd), DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(nilai), 4)
        self._filter = _Filter(self)
        QCoreApplication.instance().installNativeEventFilter(self._filter)
        u.SetWindowPos(wintypes.HWND(self.hwnd), None, 0, 0, 0, 0, SWP_GANTI_BINGKAI)

    def _maksimal(self):
        return bool(ctypes.windll.user32.IsZoomed(wintypes.HWND(self.hwnd)))

    def _kontrol_di(self, x, y):
        hasil = QMetaObject.invokeMethod(self._win, "kontrolDi", Qt.ConnectionType.DirectConnection, Q_RETURN_ARG("QVariant"), Q_ARG("QVariant", x), Q_ARG("QVariant", y))
        return hasil or ""

    @Slot()
    def alihMaksimal(self):
        if self._win is None:
            return
        if self._maksimal():
            self._win.showNormal()
        else:
            self._win.showMaximized()

    def tangani(self, msg):
        u = ctypes.windll.user32
        if msg.message == WM_NCCALCSIZE:
            if not msg.wParam:
                return False, 0
            if self._maksimal():  # jendela penuh meluas sebesar bingkai ke luar layar
                r = _NCCALCSIZE.from_address(msg.lParam).rgrc[0]
                f = u.GetSystemMetrics(SM_CXSIZEFRAME) + u.GetSystemMetrics(SM_CXPADDEDBORDER)
                r.left += f
                r.top += f
                r.right -= f
                r.bottom -= f
            return True, 0
        if msg.message == WM_NCHITTEST:
            p = wintypes.POINT(ctypes.c_short(msg.lParam & 0xFFFF).value, ctypes.c_short((msg.lParam >> 16) & 0xFFFF).value)
            u.ScreenToClient(wintypes.HWND(self.hwnd), ctypes.byref(p))
            r = wintypes.RECT()
            u.GetClientRect(wintypes.HWND(self.hwnd), ctypes.byref(r))
            s = self._win.devicePixelRatio()
            x, y = p.x / s, p.y / s
            kontrol = self._kontrol_di(x, y) if 0 <= y < TINGGI_JUDUL else ""
            hasil = kode_hit(x, y, r.right / s, r.bottom / s, TEPI, TINGGI_JUDUL, kontrol, self._maksimal())
            self._set(hasil == HTMAXBUTTON, self._tekan and hasil == HTMAXBUTTON)
            return True, hasil
        if msg.message == WM_NCMOUSELEAVE:
            self._set(False, False)
            return False, 0
        if msg.wParam == HTMAXBUTTON:  # jangan biarkan Windows menggambar tombol lamanya
            if msg.message == WM_NCLBUTTONDOWN:
                self._set(True, True)
                return True, 0
            if msg.message == WM_NCLBUTTONUP:
                ditekan = self._tekan
                self._set(True, False)
                if ditekan:
                    self.alihMaksimal()
                return True, 0
        elif msg.message != WM_NCMOUSEMOVE:
            self._set(False, False)
        return False, 0
