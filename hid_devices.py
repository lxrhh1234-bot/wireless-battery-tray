"""Windows HID device discovery and 2.4GHz peripheral battery readers."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import time
from typing import Callable

setupapi = ctypes.windll.setupapi
hid = ctypes.windll.hid
kernel32 = ctypes.windll.kernel32

DIGCF_PRESENT = 0x02
DIGCF_DEVICEINTERFACE = 0x10
INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x01
FILE_SHARE_WRITE = 0x02
OPEN_EXISTING = 3
FILE_FLAG_OVERLAPPED = 0x40000000
WAIT_OBJECT_0 = 0
ERROR_IO_PENDING = 997


class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_ubyte * 8),
    ]


class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("InterfaceClassGuid", GUID),
        ("Flags", wintypes.DWORD),
        ("Reserved", ctypes.POINTER(ctypes.c_ulong)),
    ]


class HIDD_ATTRIBUTES(ctypes.Structure):
    _fields_ = [
        ("Size", wintypes.ULONG),
        ("VendorID", wintypes.USHORT),
        ("ProductID", wintypes.USHORT),
        ("VersionNumber", wintypes.USHORT),
    ]


class HIDP_CAPS(ctypes.Structure):
    _fields_ = [
        ("Usage", wintypes.USHORT),
        ("UsagePage", wintypes.USHORT),
        ("InputReportByteLength", wintypes.USHORT),
        ("OutputReportByteLength", wintypes.USHORT),
        ("FeatureReportByteLength", wintypes.USHORT),
        ("Reserved", wintypes.USHORT * 17),
        ("NumberLinkCollectionNodes", wintypes.USHORT),
        ("NumberInputButtonCaps", wintypes.USHORT),
        ("NumberInputValueCaps", wintypes.USHORT),
        ("NumberInputDataIndices", wintypes.USHORT),
        ("NumberOutputButtonCaps", wintypes.USHORT),
        ("NumberOutputValueCaps", wintypes.USHORT),
        ("NumberOutputDataIndices", wintypes.USHORT),
        ("NumberFeatureButtonCaps", wintypes.USHORT),
        ("NumberFeatureValueCaps", wintypes.USHORT),
        ("NumberFeatureDataIndices", wintypes.USHORT),
    ]


class OVERLAPPED(ctypes.Structure):
    _fields_ = [
        ("Internal", ctypes.POINTER(ctypes.c_ulong)),
        ("InternalHigh", ctypes.POINTER(ctypes.c_ulong)),
        ("Offset", wintypes.DWORD),
        ("OffsetHigh", wintypes.DWORD),
        ("hEvent", ctypes.c_void_p),
    ]


# Configure ctypes signatures for 64-bit safety
setupapi.SetupDiGetClassDevsW.restype = ctypes.c_void_p
setupapi.SetupDiDestroyDeviceInfoList.argtypes = [ctypes.c_void_p]
setupapi.SetupDiEnumDeviceInterfaces.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.POINTER(GUID),
    wintypes.DWORD,
    ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
]
setupapi.SetupDiGetDeviceInterfaceDetailW.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    ctypes.c_void_p,
]
kernel32.CreateFileW.restype = ctypes.c_void_p
kernel32.CreateFileW.argtypes = [
    wintypes.LPCWSTR,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.c_void_p,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.c_void_p,
]
kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
kernel32.CreateEventW.restype = ctypes.c_void_p
kernel32.CreateEventW.argtypes = [
    ctypes.c_void_p,
    wintypes.BOOL,
    wintypes.BOOL,
    wintypes.LPCWSTR,
]
kernel32.WaitForSingleObject.argtypes = [ctypes.c_void_p, wintypes.DWORD]
kernel32.GetOverlappedResult.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(OVERLAPPED),
    ctypes.POINTER(wintypes.DWORD),
    wintypes.BOOL,
]
kernel32.CancelIo.argtypes = [ctypes.c_void_p]
kernel32.WriteFile.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    ctypes.POINTER(OVERLAPPED),
]
kernel32.ReadFile.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    ctypes.POINTER(OVERLAPPED),
]
hid.HidD_GetHidGuid.argtypes = [ctypes.POINTER(GUID)]
hid.HidD_GetAttributes.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDD_ATTRIBUTES)]
hid.HidD_GetPreparsedData.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDP_CAPS)]
hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
hid.HidD_SetFeature.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.ULONG]
hid.HidD_GetFeature.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.ULONG]


@dataclass
class DeviceBatteryStatus:
    """Represents the current battery status of a 2.4GHz wireless device."""

    key: str
    name: str
    short_label: str
    battery: int | None = None
    charging: bool = False
    dongle_present: bool = False
    awake: bool = False
    last_updated: float = 0.0

    def display_text(self) -> str:
        if not self.dongle_present:
            return f"{self.name}: 未连接接收器"
        if self.battery is None:
            return f"{self.name}: 休眠/未开机"
        suffix = " (充电中)" if self.charging else ""
        stale = "" if self.awake else " [休眠]"
        return f"{self.name}: {self.battery}%{suffix}{stale}"


def find_hid_path(vid: int, pid: int, usage_page: int, usage: int) -> str | None:
    """Find the Windows HID device path matching VID/PID and UsagePage/Usage."""
    hid_guid = GUID()
    hid.HidD_GetHidGuid(ctypes.byref(hid_guid))

    hdev = setupapi.SetupDiGetClassDevsW(
        ctypes.byref(hid_guid), None, None, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
    )
    if hdev == INVALID_HANDLE_VALUE:
        return None

    idx = 0
    if_data = SP_DEVICE_INTERFACE_DATA()
    if_data.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
    matched_path: str | None = None
    cb_size = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6

    try:
        while setupapi.SetupDiEnumDeviceInterfaces(
            hdev, None, ctypes.byref(hid_guid), idx, ctypes.byref(if_data)
        ):
            idx += 1
            req_size = wintypes.DWORD(0)
            setupapi.SetupDiGetDeviceInterfaceDetailW(
                hdev, ctypes.byref(if_data), None, 0, ctypes.byref(req_size), None
            )
            if req_size.value == 0:
                continue

            buf = ctypes.create_string_buffer(req_size.value)
            ctypes.cast(buf, ctypes.POINTER(wintypes.DWORD))[0] = cb_size
            if not setupapi.SetupDiGetDeviceInterfaceDetailW(
                hdev, ctypes.byref(if_data), buf, req_size.value, None, None
            ):
                continue

            path = ctypes.wstring_at(ctypes.addressof(buf) + 4)
            handle = kernel32.CreateFileW(
                path, 0, FILE_SHARE_READ | FILE_SHARE_WRITE, None, OPEN_EXISTING, 0, None
            )
            if handle == INVALID_HANDLE_VALUE:
                continue

            attrs = HIDD_ATTRIBUTES()
            attrs.Size = ctypes.sizeof(HIDD_ATTRIBUTES)
            hid.HidD_GetAttributes(handle, ctypes.byref(attrs))

            pp_data = ctypes.c_void_p()
            caps = HIDP_CAPS()
            has_caps = False
            if hid.HidD_GetPreparsedData(handle, ctypes.byref(pp_data)):
                hid.HidP_GetCaps(pp_data, ctypes.byref(caps))
                hid.HidD_FreePreparsedData(pp_data)
                has_caps = True

            kernel32.CloseHandle(handle)

            if (
                has_caps
                and attrs.VendorID == vid
                and attrs.ProductID == pid
                and caps.UsagePage == usage_page
                and caps.Usage == usage
            ):
                matched_path = path
                break
    finally:
        setupapi.SetupDiDestroyDeviceInfoList(hdev)

    return matched_path


def _open_rw(path: str, overlapped: bool = True) -> int | None:
    flags = FILE_FLAG_OVERLAPPED if overlapped else 0
    h = kernel32.CreateFileW(
        path,
        GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        None,
        OPEN_EXISTING,
        flags,
        None,
    )
    if h == INVALID_HANDLE_VALUE:
        return None
    return h


def _write_overlapped(handle: int, data: list[int], timeout_ms: int = 400) -> bool:
    evt = kernel32.CreateEventW(None, True, False, None)
    ov = OVERLAPPED()
    ov.hEvent = evt
    wbuf = (ctypes.c_ubyte * len(data))(*data)
    nwritten = wintypes.DWORD(0)
    try:
        ok = kernel32.WriteFile(handle, wbuf, len(data), ctypes.byref(nwritten), ctypes.byref(ov))
        if ok:
            return True
        if kernel32.GetLastError() == ERROR_IO_PENDING:
            if kernel32.WaitForSingleObject(evt, timeout_ms) == WAIT_OBJECT_0:
                kernel32.GetOverlappedResult(handle, ctypes.byref(ov), ctypes.byref(nwritten), False)
                return True
            kernel32.CancelIo(handle)
        return False
    finally:
        kernel32.CloseHandle(evt)


def _read_overlapped(handle: int, size: int, timeout_ms: int = 350) -> bytes | None:
    evt = kernel32.CreateEventW(None, True, False, None)
    ov = OVERLAPPED()
    ov.hEvent = evt
    rbuf = (ctypes.c_ubyte * size)()
    nread = wintypes.DWORD(0)
    try:
        ok = kernel32.ReadFile(handle, rbuf, size, ctypes.byref(nread), ctypes.byref(ov))
        if ok:
            return bytes(rbuf[: nread.value])
        if kernel32.GetLastError() == ERROR_IO_PENDING:
            if kernel32.WaitForSingleObject(evt, timeout_ms) == WAIT_OBJECT_0:
                kernel32.GetOverlappedResult(handle, ctypes.byref(ov), ctypes.byref(nread), False)
                return bytes(rbuf[: nread.value])
            kernel32.CancelIo(handle)
        return None
    finally:
        kernel32.CloseHandle(evt)


def poll_rog_pelta() -> tuple[bool, int | None, bool]:
    """Query ASUS ROG PELTA (2.4GHz) headset battery via 0xCC 0x12 0x07."""
    path = find_hid_path(0x0B05, 0x1B84, 0xFF00, 0x0001)
    if not path:
        return False, None, False
    h = _open_rw(path, overlapped=True)
    if not h:
        return True, None, False
    try:
        cmd = [0xCC, 0x12, 0x07] + [0x00] * 61
        if not _write_overlapped(h, cmd):
            return True, None, False
        for _ in range(4):
            res = _read_overlapped(h, 64, timeout_ms=300)
            if not res:
                break
            if len(res) >= 8 and res[0] == 0xCC and res[1] == 0x12 and res[2] == 0x07:
                state = res[5]
                pct = res[6]
                if state != 0xFF and 0 <= pct <= 100:
                    return True, pct, (state == 0x01)
                return True, None, False
        return True, None, False
    finally:
        kernel32.CloseHandle(h)


def poll_mchose_a7() -> tuple[bool, int | None, bool]:
    """Query MCHOSE A7 Pro mouse battery via 65-byte Feature Report 0x11."""
    path = find_hid_path(0x5253, 0x1021, 0xFF01, 0x0001)
    if not path:
        return False, None, False
    h = _open_rw(path, overlapped=False)
    if not h:
        return True, None, False
    try:
        buf = (ctypes.c_ubyte * 65)(*([0xFF] * 65))
        buf[0] = 0x11
        buf[1] = 0xF9
        if not hid.HidD_SetFeature(h, buf, 65):
            return True, None, False
        time.sleep(0.08)
        rbuf = (ctypes.c_ubyte * 65)()
        rbuf[0] = 0x11
        if not hid.HidD_GetFeature(h, rbuf, 65):
            return True, None, False
        raw = bytes(rbuf)
        dec = bytes(b ^ 0xFF for b in raw[2:])
        if len(dec) >= 12 and dec[0] == 0x53 and dec[1] == 0x52:
            charging = dec[10] == 0x01
            pct = dec[11]
            if 1 <= pct <= 100:
                return True, pct, charging
        return True, None, False
    finally:
        kernel32.CloseHandle(h)


def poll_compx_24g() -> tuple[bool, int | None, bool]:
    """Query Compx 2.4G Wireless Receiver (3554:FA09) battery via 0x13 0x05."""
    path = find_hid_path(0x3554, 0xFA09, 0xFF02, 0x0002)
    if not path:
        return False, None, False
    h = _open_rw(path, overlapped=True)
    if not h:
        return True, None, False
    try:
        cmd = [0x13, 0x05] + [0x00] * 18
        if not _write_overlapped(h, cmd):
            return True, None, False
        for _ in range(4):
            res = _read_overlapped(h, 20, timeout_ms=300)
            if not res:
                break
            if len(res) >= 8 and res[0] == 0x13 and res[1] == 0x0A:
                pct = res[6]
                charging = (res[7] == 0x01) or ((res[7] & 0x10) != 0)
                if 0 <= pct <= 100:
                    return True, pct, charging
                return True, None, False
        return True, None, False
    finally:
        kernel32.CloseHandle(h)


DEVICE_DEFINITIONS: list[tuple[str, str, str, Callable[[], tuple[bool, int | None, bool]]]] = [
    ("rog_pelta", "ROG PELTA 耳机", "耳", poll_rog_pelta),
    ("mchose_a7", "MCHOSE A7 Pro 鼠标", "鼠", poll_mchose_a7),
    ("compx_24g", "Compx 2.4G 键盘", "键", poll_compx_24g),
]


class _DEVPROPKEY(ctypes.Structure):
    _fields_ = [("fmtid", GUID), ("pid", wintypes.ULONG)]


class _SP_DEVINFO_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("ClassGuid", GUID),
        ("DevInst", wintypes.DWORD),
        ("Reserved", ctypes.POINTER(ctypes.c_ulong)),
    ]


_DIGCF_ALLCLASSES = 0x04
_SPDRP_DEVICEDESC = 0x00000000
_SPDRP_FRIENDLYNAME = 0x0000000C
_DEVPKEY_BATT = _DEVPROPKEY(
    GUID(0x104EA319, 0x6EE2, 0x4701, (ctypes.c_ubyte * 8)(0xBD, 0x47, 0x8D, 0xDB, 0xF4, 0x25, 0xBB, 0xE5)),
    2,
)
_DEVPKEY_IS_CONNECTED = _DEVPROPKEY(
    GUID(0x83DA6326, 0x97A6, 0x4088, (ctypes.c_ubyte * 8)(0x94, 0x53, 0xA1, 0x92, 0x3F, 0x57, 0x3B, 0x29)),
    15,
)

setupapi.SetupDiEnumDeviceInfo.argtypes = [
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(_SP_DEVINFO_DATA),
]
setupapi.SetupDiGetDevicePropertyW.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(_SP_DEVINFO_DATA),
    ctypes.POINTER(_DEVPROPKEY),
    ctypes.POINTER(wintypes.ULONG),
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    wintypes.DWORD,
]
setupapi.SetupDiGetDeviceRegistryPropertyW.argtypes = [
    ctypes.c_void_p,
    ctypes.POINTER(_SP_DEVINFO_DATA),
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    ctypes.c_void_p,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]


def _clean_bt_name(raw_name: str) -> str:
    for suffix in (" Hands-Free AG", " Avrcp Transport", " Stereo"):
        if raw_name.endswith(suffix):
            raw_name = raw_name[: -len(suffix)]
    return raw_name.strip() or "蓝牙设备"


def poll_bluetooth_devices() -> list[DeviceBatteryStatus]:
    """Query currently connected Windows Bluetooth devices that report battery level."""
    hdev = setupapi.SetupDiGetClassDevsW(None, None, None, DIGCF_PRESENT | _DIGCF_ALLCLASSES)
    if hdev == INVALID_HANDLE_VALUE:
        return []

    now = time.time()
    seen: dict[str, DeviceBatteryStatus] = {}
    dev = _SP_DEVINFO_DATA()
    dev.cbSize = ctypes.sizeof(_SP_DEVINFO_DATA)
    idx = 0

    try:
        while setupapi.SetupDiEnumDeviceInfo(hdev, idx, ctypes.byref(dev)):
            idx += 1
            ptype = wintypes.ULONG()
            req = wintypes.DWORD()
            batt_val = ctypes.c_ubyte(0)
            if not setupapi.SetupDiGetDevicePropertyW(
                hdev,
                ctypes.byref(dev),
                ctypes.byref(_DEVPKEY_BATT),
                ctypes.byref(ptype),
                ctypes.byref(batt_val),
                1,
                ctypes.byref(req),
                0,
            ):
                continue

            conn_val = ctypes.c_byte(0)
            if not setupapi.SetupDiGetDevicePropertyW(
                hdev,
                ctypes.byref(dev),
                ctypes.byref(_DEVPKEY_IS_CONNECTED),
                ctypes.byref(ptype),
                ctypes.byref(conn_val),
                1,
                ctypes.byref(req),
                0,
            ) or conn_val.value == 0:
                continue

            pct = int(batt_val.value)
            if not (0 <= pct <= 100):
                continue

            name_buf = ctypes.create_unicode_buffer(256)
            if not setupapi.SetupDiGetDeviceRegistryPropertyW(
                hdev, ctypes.byref(dev), _SPDRP_FRIENDLYNAME, None, name_buf, 512, None
            ):
                setupapi.SetupDiGetDeviceRegistryPropertyW(
                    hdev, ctypes.byref(dev), _SPDRP_DEVICEDESC, None, name_buf, 512, None
                )

            clean_name = _clean_bt_name(name_buf.value)
            key = f"bt_{clean_name}"
            if key not in seen:
                seen[key] = DeviceBatteryStatus(
                    key=key,
                    name=f"{clean_name} (蓝牙)",
                    short_label="蓝",
                    battery=pct,
                    charging=False,
                    dongle_present=True,
                    awake=True,
                    last_updated=now,
                )
    finally:
        setupapi.SetupDiDestroyDeviceInfoList(hdev)

    return list(seen.values())
