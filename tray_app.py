"""Windows System Tray application for real-time 2.4GHz peripheral battery monitoring."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import sys
import threading
import time
import tkinter as tk
import winreg

from PIL import Image, ImageDraw

from config import load_config, save_config
from hid_devices import DeviceBatteryStatus, poll_all_24g_devices, poll_bluetooth_devices
from i18n import tr
from ui_windows import BatteryFlyout, SettingsWindow

user32 = ctypes.windll.user32
shell32 = ctypes.windll.shell32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

# Window & Tray constants
WM_USER = 0x0400
WM_TRAYICON = WM_USER + 1
WM_COMMAND = 0x0111
WM_DESTROY = 0x0002

WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205

NIM_ADD = 0x00000000
NIM_MODIFY = 0x00000001
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004
NIF_INFO = 0x00000010
NIIF_WARNING = 0x00000002
ERROR_ALREADY_EXISTS = 183

MF_STRING = 0x00000000
MF_SEPARATOR = 0x00000800
TPM_LEFTALIGN = 0x0000
TPM_BOTTOMALIGN = 0x0020
TPM_RIGHTBUTTON = 0x0002

DIB_RGB_COLORS = 0
BI_RGB = 0

STARTUP_REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_REG_NAME = "WirelessBatteryTray"

CMD_SHOW_POPUP = 1001
CMD_REFRESH = 1002
CMD_SETTINGS = 1003
CMD_EXIT = 1099

WNDPROC = ctypes.WINFUNCTYPE(
    ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM
)


class WNDCLASSEXW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.UINT),
        ("style", wintypes.UINT),
        ("lpfnWndProc", WNDPROC),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
        ("hIconSm", wintypes.HICON),
    ]


class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
        ("dwState", wintypes.DWORD),
        ("dwStateMask", wintypes.DWORD),
        ("szInfo", wintypes.WCHAR * 256),
        ("uVersion", wintypes.UINT),
        ("szInfoTitle", wintypes.WCHAR * 64),
        ("dwInfoFlags", wintypes.DWORD),
        ("guidItem", ctypes.c_ubyte * 16),
        ("hBalloonIcon", wintypes.HICON),
    ]


class POINT(ctypes.Structure):
    _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]


class MSG(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", POINT),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class ICONINFO(ctypes.Structure):
    _fields_ = [
        ("fIcon", wintypes.BOOL),
        ("xHotspot", wintypes.DWORD),
        ("yHotspot", wintypes.DWORD),
        ("hbmMask", wintypes.HBITMAP),
        ("hbmColor", wintypes.HBITMAP),
    ]


# 64-bit safe ctypes signatures
user32.DefWindowProcW.restype = ctypes.c_ssize_t
user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.RegisterClassExW.argtypes = [ctypes.POINTER(WNDCLASSEXW)]
user32.CreateWindowExW.restype = wintypes.HWND
user32.DestroyWindow.argtypes = [wintypes.HWND]
user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
user32.PostQuitMessage.argtypes = [ctypes.c_int]
user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
user32.CreatePopupMenu.restype = wintypes.HMENU
user32.AppendMenuW.argtypes = [wintypes.HMENU, wintypes.UINT, ctypes.c_size_t, wintypes.LPCWSTR]
user32.TrackPopupMenu.argtypes = [
    wintypes.HMENU,
    wintypes.UINT,
    ctypes.c_int,
    ctypes.c_int,
    ctypes.c_int,
    wintypes.HWND,
    ctypes.c_void_p,
]
user32.DestroyMenu.argtypes = [wintypes.HMENU]
user32.SetForegroundWindow.argtypes = [wintypes.HWND]
user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
user32.CreateIconIndirect.restype = wintypes.HICON
user32.CreateIconIndirect.argtypes = [ctypes.POINTER(ICONINFO)]
user32.DestroyIcon.argtypes = [wintypes.HICON]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
gdi32.CreateDIBSection.restype = wintypes.HBITMAP
gdi32.CreateDIBSection.argtypes = [
    wintypes.HDC,
    ctypes.c_void_p,
    wintypes.UINT,
    ctypes.POINTER(ctypes.c_void_p),
    wintypes.HANDLE,
    wintypes.DWORD,
]
gdi32.CreateBitmap.restype = wintypes.HBITMAP
gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]


def pil_to_hicon(img: Image.Image) -> int:
    """Convert an RGBA PIL Image into a Windows HICON."""
    rgba = img.convert("RGBA")
    w, h = rgba.size
    b, g, r, a = rgba.split()
    bgra = Image.merge("RGBA", (b, g, r, a)).tobytes()

    bmi = BITMAPINFOHEADER()
    bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bmi.biWidth = w
    bmi.biHeight = -h
    bmi.biPlanes = 1
    bmi.biBitCount = 32
    bmi.biCompression = BI_RGB

    bits_ptr = ctypes.c_void_p()
    hbm_color = gdi32.CreateDIBSection(
        None, ctypes.byref(bmi), DIB_RGB_COLORS, ctypes.byref(bits_ptr), None, 0
    )
    ctypes.memmove(bits_ptr, bgra, len(bgra))
    hbm_mask = gdi32.CreateBitmap(w, h, 1, 1, None)

    icon_info = ICONINFO()
    icon_info.fIcon = True
    icon_info.hbmMask = hbm_mask
    icon_info.hbmColor = hbm_color

    hicon = user32.CreateIconIndirect(ctypes.byref(icon_info))
    gdi32.DeleteObject(hbm_color)
    gdi32.DeleteObject(hbm_mask)
    return hicon


def render_app_icon() -> Image.Image:
    """Render a static, minimalist rounded-square white icon with a golden-yellow lightning bolt."""
    hi = 128
    img = Image.new("RGBA", (hi, hi), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Pure white rounded-square (squircle) with subtle hairline border
    draw.rounded_rectangle(
        [5, 5, hi - 6, hi - 6],
        radius=34,
        fill=(255, 255, 255, 255),
        outline=(226, 232, 240, 255),
        width=4,
    )

    # Bold golden-yellow lightning bolt centered in the squircle
    bolt = [
        (72, 22),
        (36, 69),
        (60, 69),
        (52, 106),
        (92, 57),
        (67, 57),
    ]
    draw.polygon(bolt, fill=(245, 158, 11, 255), outline=(217, 119, 6, 255), width=2)

    return img.resize((64, 64), Image.Resampling.LANCZOS)


def is_startup_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, STARTUP_REG_NAME)
            return True
    except OSError:
        return False


def set_startup_enabled(enable: bool) -> None:
    if getattr(sys, "frozen", False):
        cmd = f'"{os.path.abspath(sys.executable)}"'
    else:
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable
        script_path = os.path.abspath(__file__)
        cmd = f'"{pythonw}" "{script_path}"'
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STARTUP_REG_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enable:
            winreg.SetValueEx(key, STARTUP_REG_NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(key, STARTUP_REG_NAME)
            except FileNotFoundError:
                pass


class BatteryTrayApp:
    """Lightweight tray app with static icon, taskbar-docked flyout, and background HID polling."""

    def __init__(self) -> None:
        self.config = load_config()
        self.statuses: dict[str, DeviceBatteryStatus] = {}
        self.bt_statuses: list[DeviceBatteryStatus] = []
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.refresh_event = threading.Event()
        self.hwnd: int = 0
        self.app_hicon: int = 0
        self._last_tip: str = ""
        self._notified_low: set[str] = set()
        self._wndproc_ref = WNDPROC(self._wndproc)

        self.root = tk.Tk()
        self.root.withdraw()
        self.popup_win: BatteryFlyout | None = None
        self.settings_win: SettingsWindow | None = None

    def _poll_once(self) -> None:
        try:
            discovered_24g = poll_all_24g_devices(
                auto_probe_generic=bool(self.config.get("auto_probe_generic", True))
            )
        except Exception:
            discovered_24g = []

        present_keys = {d.key for d in discovered_24g}
        with self.lock:
            for key, st in self.statuses.items():
                if key not in present_keys:
                    st.dongle_present = False
                    st.awake = False

            for d in discovered_24g:
                existing = self.statuses.get(d.key)
                if existing is None:
                    self.statuses[d.key] = d
                else:
                    existing.dongle_present = True
                    existing.name = d.name
                    if d.battery is not None:
                        existing.battery = d.battery
                        existing.charging = d.charging
                        existing.awake = True
                        existing.last_updated = d.last_updated
                    else:
                        existing.awake = False

        for d in discovered_24g:
            if d.battery is not None:
                alias = self.config["aliases"].get(d.key, d.name)
                self._check_low_battery(d.key, alias, d.battery, d.charging)

        if self.config.get("show_bluetooth", True):
            try:
                bt_list = poll_bluetooth_devices()
            except Exception:
                bt_list = []
            with self.lock:
                self.bt_statuses = bt_list
            for bt in bt_list:
                if bt.battery is not None:
                    self._check_low_battery(bt.key, bt.name, bt.battery, bt.charging)
        else:
            with self.lock:
                self.bt_statuses = []

    def _check_low_battery(self, key: str, alias: str, pct: int, charging: bool) -> None:
        if not self.config.get("low_battery_notify", True):
            return
        threshold = int(self.config.get("low_battery_threshold", 20))
        if charging or pct > threshold + 5:
            self._notified_low.discard(key)
            return
        if pct <= threshold and key not in self._notified_low:
            self._notified_low.add(key)
            lang = self.config.get("language", "zh")
            self._send_balloon(
                tr(lang, "low_batt_title"),
                tr(lang, "low_batt_msg").format(alias=alias, pct=pct),
            )

    def _send_balloon(self, title: str, message: str) -> None:
        if not self.hwnd:
            return
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self.hwnd
        nid.uID = 1
        nid.uFlags = NIF_INFO
        nid.szInfoTitle = title[:63]
        nid.szInfo = message[:255]
        nid.dwInfoFlags = NIIF_WARNING
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))

    def _poll_loop(self) -> None:
        while not self.stop_event.is_set():
            self._poll_once()
            self._update_tooltip()
            self.root.after(0, self._refresh_popup_if_open)
            interval = max(10, int(self.config.get("poll_interval", 30)))
            self.refresh_event.wait(timeout=interval)
            self.refresh_event.clear()

    def _refresh_popup_if_open(self) -> None:
        if self.popup_win and self.popup_win.winfo_exists():
            with self.lock:
                snapshot = list(self.statuses.values()) + list(self.bt_statuses)
            self.popup_win.render_devices(
                snapshot,
                self.config["aliases"],
                hide_disconnected=bool(self.config.get("hide_disconnected", True)),
                lang=self.config.get("language", "zh"),
            )

    def _build_tooltip(self) -> str:
        aliases = self.config["aliases"]
        lang = self.config.get("language", "zh")
        with self.lock:
            parts = []
            for st in list(self.statuses.values()) + list(self.bt_statuses):
                label = aliases.get(st.key, st.name)
                if st.dongle_present and st.battery is not None:
                    chg = "⚡" if st.charging else ""
                    parts.append(f"{label}: {st.battery}%{chg}")
                elif st.dongle_present:
                    parts.append(f"{label}: {tr(lang, 'sleep')}")
            if not parts:
                return tr(lang, "tooltip_empty")
            return " | ".join(parts)[:127]

    def _update_tooltip(self) -> None:
        if not self.hwnd:
            return
        tip = self._build_tooltip()
        if tip == self._last_tip:
            return
        self._last_tip = tip
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self.hwnd
        nid.uID = 1
        nid.uFlags = NIF_TIP
        nid.szTip = tip
        shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))

    def _open_popup(self, anchor_x: int) -> None:
        if self.popup_win and self.popup_win.winfo_exists():
            self.popup_win.destroy()
            self.popup_win = None
            return
        self._show_flyout(anchor_x)

    def _show_flyout(self, anchor_x: int) -> None:
        with self.lock:
            snapshot = list(self.statuses.values()) + list(self.bt_statuses)
        self.popup_win = BatteryFlyout(
            parent=self.root,
            statuses=snapshot,
            aliases=self.config["aliases"],
            anchor_x=anchor_x,
            hide_disconnected=bool(self.config.get("hide_disconnected", True)),
            lang=self.config.get("language", "zh"),
            on_refresh=lambda: self.refresh_event.set(),
            on_open_settings=self._open_settings,
            on_exit=self._request_exit,
        )
        # Immediately trigger a background refresh whenever the user opens the flyout
        self.refresh_event.set()

    def _open_settings(self) -> None:
        if self.settings_win and self.settings_win.winfo_exists():
            self.settings_win.lift()
            self.settings_win.focus_force()
            return
        with self.lock:
            snapshot = list(self.statuses.values()) + list(self.bt_statuses)
        self.settings_win = SettingsWindow(
            parent=self.root,
            config=self.config,
            discovered_devices=snapshot,
            startup_enabled=is_startup_enabled(),
            on_save=self._apply_settings,
        )

    def _apply_settings(self, new_cfg: dict, startup_enabled: bool) -> None:
        self.config = new_cfg
        save_config(new_cfg)
        set_startup_enabled(startup_enabled)
        with self.lock:
            for key, st in self.statuses.items():
                st.name = new_cfg["aliases"].get(key, st.name)
        self._update_tooltip()
        self.refresh_event.set()

    def _request_exit(self) -> None:
        self.stop_event.set()
        self.refresh_event.set()
        if self.hwnd:
            user32.PostMessageW(self.hwnd, WM_DESTROY, 0, 0)
        self.root.after(0, self.root.quit)

    def _show_context_menu(self) -> None:
        lang = self.config.get("language", "zh")
        hmenu = user32.CreatePopupMenu()
        user32.AppendMenuW(hmenu, MF_STRING, CMD_SHOW_POPUP, tr(lang, "menu_view"))
        user32.AppendMenuW(hmenu, MF_STRING, CMD_REFRESH, tr(lang, "menu_refresh"))
        user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(hmenu, MF_STRING, CMD_SETTINGS, tr(lang, "menu_settings"))
        user32.AppendMenuW(hmenu, MF_SEPARATOR, 0, None)
        user32.AppendMenuW(hmenu, MF_STRING, CMD_EXIT, tr(lang, "menu_exit"))

        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        user32.SetForegroundWindow(self.hwnd)
        user32.TrackPopupMenu(
            hmenu, TPM_LEFTALIGN | TPM_BOTTOMALIGN | TPM_RIGHTBUTTON, pt.x, pt.y, 0, self.hwnd, None
        )
        user32.DestroyMenu(hmenu)

    def _wndproc(self, hwnd: int, msg: int, wparam: int, lparam: int) -> int:
        if msg == WM_TRAYICON:
            if lparam == WM_LBUTTONUP:
                pt = POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                self.root.after(0, lambda x=pt.x: self._open_popup(x))
            elif lparam == WM_RBUTTONUP:
                self._show_context_menu()
            return 0
        if msg == WM_COMMAND:
            cmd_id = wparam & 0xFFFF
            if cmd_id == CMD_SHOW_POPUP:
                pt = POINT()
                user32.GetCursorPos(ctypes.byref(pt))
                self.root.after(0, lambda x=pt.x: self._open_popup(x))
            elif cmd_id == CMD_REFRESH:
                self.refresh_event.set()
            elif cmd_id == CMD_SETTINGS:
                self.root.after(0, self._open_settings)
            elif cmd_id == CMD_EXIT:
                self._request_exit()
            return 0
        if msg == WM_DESTROY:
            nid = NOTIFYICONDATAW()
            nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
            nid.hWnd = hwnd
            nid.uID = 1
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid))
            if self.app_hicon:
                user32.DestroyIcon(self.app_hicon)
                self.app_hicon = 0
            user32.PostQuitMessage(0)
            return 0
        return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    def _tray_thread(self) -> None:
        hinst = kernel32.GetModuleHandleW(None)
        cls_name = "WirelessBatteryTrayWnd"
        wc = WNDCLASSEXW()
        wc.cbSize = ctypes.sizeof(WNDCLASSEXW)
        wc.lpfnWndProc = self._wndproc_ref
        wc.hInstance = hinst
        wc.lpszClassName = cls_name
        user32.RegisterClassExW(ctypes.byref(wc))

        self.hwnd = user32.CreateWindowExW(
            0, cls_name, "2.4GHz Battery Tray", 0, 0, 0, 0, 0, None, None, hinst, None
        )
        self.app_hicon = pil_to_hicon(render_app_icon())
        nid = NOTIFYICONDATAW()
        nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        nid.hWnd = self.hwnd
        nid.uID = 1
        nid.uFlags = NIF_MESSAGE | NIF_ICON | NIF_TIP
        nid.uCallbackMessage = WM_TRAYICON
        nid.hIcon = self.app_hicon
        nid.szTip = "2.4GHz 设备电量监控"
        shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))

        msg = MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def run(self) -> None:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass

        threading.Thread(target=self._tray_thread, daemon=True).start()
        threading.Thread(target=self._poll_loop, daemon=True).start()
        self.root.mainloop()


if __name__ == "__main__":
    _mutex = kernel32.CreateMutexW(None, False, "Local\\WirelessBatteryTray_SingleInstance")
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        if _mutex:
            kernel32.CloseHandle(_mutex)
        sys.exit(0)
    try:
        BatteryTrayApp().run()
    finally:
        if _mutex:
            kernel32.CloseHandle(_mutex)
