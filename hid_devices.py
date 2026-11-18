"""Windows HID auto-discovery, 2.4GHz peripheral protocols, and Bluetooth PnP battery reader."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
import time

setupapi = ctypes.windll.setupapi
hid = ctypes.windll.hid
kernel32 = ctypes.windll.kernel32

DIGCF_PRESENT = 0x02
DIGCF_ALLCLASSES = 0x04
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


class _DEVPROPKEY(ctypes.Structure):
    _fields_ = [("fmtid", GUID), ("pid", wintypes.ULONG)]


class _SP_DEVINFO_DATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("ClassGuid", GUID),
        ("DevInst", wintypes.DWORD),
        ("Reserved", ctypes.POINTER(ctypes.c_ulong)),
    ]


# Configure 64-bit safe ctypes signatures
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
hid.HidD_GetProductString.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.ULONG]
hid.HidD_GetPreparsedData.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
hid.HidP_GetCaps.argtypes = [ctypes.c_void_p, ctypes.POINTER(HIDP_CAPS)]
hid.HidD_FreePreparsedData.argtypes = [ctypes.c_void_p]
hid.HidD_SetFeature.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.ULONG]
hid.HidD_GetFeature.argtypes = [ctypes.c_void_p, ctypes.c_void_p, wintypes.ULONG]


@dataclass
class DeviceBatteryStatus:
    """Represents the current battery status of a 2.4GHz or Bluetooth device."""

    key: str
    name: str
    short_label: str
    battery: int | None = None
    charging: bool = False
    dongle_present: bool = False
    awake: bool = False
    last_updated: float = 0.0


@dataclass
class HidInterfaceInfo:
    """Metadata for a present Windows HID interface."""

    vid: int
    pid: int
    usage_page: int
    usage: int
    in_len: int
    out_len: int
    feat_len: int
    product: str
    path: str


def _enumerate_hid_interfaces() -> list[HidInterfaceInfo]:
    """Enumerate all present HID interfaces in a single pass."""
    hid_guid = GUID()
    hid.HidD_GetHidGuid(ctypes.byref(hid_guid))

    hdev = setupapi.SetupDiGetClassDevsW(
        ctypes.byref(hid_guid), None, None, DIGCF_PRESENT | DIGCF_DEVICEINTERFACE
    )
    if hdev == INVALID_HANDLE_VALUE:
        return []

    items: list[HidInterfaceInfo] = []
    idx = 0
    if_data = SP_DEVICE_INTERFACE_DATA()
    if_data.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
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

            prod_buf = ctypes.create_unicode_buffer(128)
            hid.HidD_GetProductString(handle, prod_buf, 256)

            pp_data = ctypes.c_void_p()
            caps = HIDP_CAPS()
            has_caps = False
            if hid.HidD_GetPreparsedData(handle, ctypes.byref(pp_data)):
                hid.HidP_GetCaps(pp_data, ctypes.byref(caps))
                hid.HidD_FreePreparsedData(pp_data)
                has_caps = True

            kernel32.CloseHandle(handle)

            if has_caps and attrs.VendorID != 0:
                items.append(
                    HidInterfaceInfo(
                        vid=attrs.VendorID,
                        pid=attrs.ProductID,
                        usage_page=caps.UsagePage,
                        usage=caps.Usage,
                        in_len=caps.InputReportByteLength,
                        out_len=caps.OutputReportByteLength,
                        feat_len=caps.FeatureReportByteLength,
                        product=prod_buf.value.strip(),
                        path=path,
                    )
                )
    finally:
        setupapi.SetupDiDestroyDeviceInfoList(hdev)

    return items


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


def _write_overlapped(handle: int, data: list[int], timeout_ms: int = 350) -> bool:
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


def _read_overlapped(handle: int, size: int, timeout_ms: int = 250) -> bytes | None:
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


def _query_rog_pelta(info: HidInterfaceInfo) -> tuple[int | None, bool]:
    """Query ASUS ROG PELTA (2.4GHz) headset battery via 0xCC 0x12 0x07."""
    h = _open_rw(info.path, overlapped=True)
    if not h:
        return None, False
    try:
        cmd = [0xCC, 0x12, 0x07] + [0x00] * 61
        if not _write_overlapped(h, cmd):
            return None, False
        for _ in range(4):
            res = _read_overlapped(h, 64, timeout_ms=250)
            if not res:
                break
            if len(res) >= 8 and res[0] == 0xCC and res[1] == 0x12 and res[2] == 0x07:
                state, pct = res[5], res[6]
                if state != 0xFF and 0 <= pct <= 100:
                    return pct, (state == 0x01)
                return None, False
        return None, False
    finally:
        kernel32.CloseHandle(h)


def _query_mchose_realtek(info: HidInterfaceInfo) -> tuple[int | None, bool]:
    """Query MCHOSE Realtek-based 2.4GHz mouse battery via 65-byte Feature Report 0x11."""
    h = _open_rw(info.path, overlapped=False)
    if not h:
        return None, False
    try:
        buf = (ctypes.c_ubyte * 65)(*([0xFF] * 65))
        buf[0] = 0x11
        buf[1] = 0xF9
        if not hid.HidD_SetFeature(h, buf, 65):
            return None, False
        time.sleep(0.08)
        rbuf = (ctypes.c_ubyte * 65)()
        rbuf[0] = 0x11
        if not hid.HidD_GetFeature(h, rbuf, 65):
            return None, False
        dec = bytes(b ^ 0xFF for b in bytes(rbuf)[2:])
        if len(dec) >= 12 and dec[0] == 0x53 and dec[1] == 0x52:
            charging = dec[10] == 0x01
            pct = dec[11]
            if 1 <= pct <= 100:
                return pct, charging
        return None, False
    finally:
        kernel32.CloseHandle(h)


def _query_compx_24g(info: HidInterfaceInfo) -> tuple[int | None, bool]:
    """Query Compx 2.4G wireless receiver (VID 0x3554) battery via 0x13 0x05."""
    h = _open_rw(info.path, overlapped=True)
    if not h:
        return None, False
    try:
        cmd = [0x13, 0x05] + [0x00] * 18
        if not _write_overlapped(h, cmd):
            return None, False
        for _ in range(4):
            res = _read_overlapped(h, 20, timeout_ms=250)
            if not res:
                break
            if len(res) >= 8 and res[0] == 0x13 and res[1] == 0x0A:
                pct = res[6]
                charging = (res[7] == 0x01) or ((res[7] & 0x10) != 0)
                if 0 <= pct <= 100:
                    return pct, charging
                return None, False
        return None, False
    finally:
        kernel32.CloseHandle(h)


def _hidpp_xfer(h: int, dev_idx: int, feat_idx: int, func_sw: int, params: list[int]) -> bytes | None:
    pkt = [0x11, dev_idx, feat_idx, func_sw] + params
    pkt += [0x00] * (20 - len(pkt))
    if not _write_overlapped(h, pkt, timeout_ms=200):
        return None
    for _ in range(4):
        res = _read_overlapped(h, 20, timeout_ms=200)
        if not res:
            break
        if len(res) >= 8 and res[0] == 0x11 and res[1] == dev_idx:
            if res[2] == 0xFF:  # HID++ error response
                return None
            if res[2] == feat_idx:
                return res
    return None


def _query_logitech_hidpp(info: HidInterfaceInfo) -> list[tuple[str, int | None, bool]]:
    """Query Logitech HID++ 2.0 receivers (Lightspeed / Unifying / Bolt) for connected devices."""
    h = _open_rw(info.path, overlapped=True)
    if not h:
        return []
    results: list[tuple[str, int | None, bool]] = []
    try:
        # 0xFF = direct receiver/device; 0x01..0x06 = Unifying/Bolt paired slots
        for dev_idx in (0xFF, 0x01, 0x02, 0x03):
            # Try UnifiedBattery (0x1004) first, then BatteryLevelStatus (0x1000)
            for feat_id, is_unified in ((0x1004, True), (0x1000, False)):
                resp = _hidpp_xfer(h, dev_idx, 0x00, 0x0A, [(feat_id >> 8) & 0xFF, feat_id & 0xFF])
                if not resp or resp[4] == 0:
                    continue
                feat_idx = resp[4]
                batt_resp = _hidpp_xfer(h, dev_idx, feat_idx, 0x1A if is_unified else 0x0A, [])
                if batt_resp:
                    pct = batt_resp[4]
                    if 0 <= pct <= 100:
                        charging = batt_resp[6] in (1, 2, 3) if not is_unified else batt_resp[6] in (1, 2, 3)
                        slot_suffix = "" if dev_idx == 0xFF else f" #{dev_idx}"
                        label = (info.product or "Logitech 2.4G") + slot_suffix
                        results.append((label, pct, charging))
                        break
            if dev_idx == 0xFF and results:
                break
    finally:
        kernel32.CloseHandle(h)
    return results


def _razer_xfer(h: int, tx_id: int, cmd_id: int) -> bytes | None:
    req = bytearray(91)  # Report ID 0x00 + 90-byte Razer payload
    req[0] = 0x00
    req[1] = 0x00  # Status: new command
    req[2] = tx_id
    req[6] = 0x02  # Data size
    req[7] = 0x07  # Command class: Power
    req[8] = cmd_id
    crc = 0
    for b in req[3:89]:
        crc ^= b
    req[89] = crc
    buf = (ctypes.c_ubyte * 91)(*req)
    if not hid.HidD_SetFeature(h, buf, 91):
        return None
    time.sleep(0.05)
    rbuf = (ctypes.c_ubyte * 91)()
    if not hid.HidD_GetFeature(h, rbuf, 91):
        return None
    raw = bytes(rbuf)
    payload = raw[1:] if len(raw) == 91 else raw
    if len(payload) >= 90 and payload[0] == 0x02:
        return payload
    return None


def _query_razer(info: HidInterfaceInfo) -> tuple[int | None, bool]:
    """Query Razer wireless mouse/headset battery via 90-byte Feature Report (VID 0x1532)."""
    h = _open_rw(info.path, overlapped=False)
    if not h:
        return None, False
    try:
        for tx_id in (0x1F, 0x3F, 0xFF):
            resp = _razer_xfer(h, tx_id, 0x80)
            if resp is not None:
                raw_batt = resp[9]
                pct = max(0, min(100, round((raw_batt / 255.0) * 100)))
                chg_resp = _razer_xfer(h, tx_id, 0x84)
                charging = bool(chg_resp and chg_resp[9] == 1)
                return pct, charging
        return None, False
    finally:
        kernel32.CloseHandle(h)


def _query_vgn_atk(info: HidInterfaceInfo) -> tuple[int | None, bool]:
    """Query VGN / VXE / ATK wireless mice via 17-byte 0x08 0x04 HID protocol."""
    h = _open_rw(info.path, overlapped=True)
    if not h:
        return None, False
    try:
        pkt = [0x08, 0x04] + [0x00] * 14
        cs = (0x55 - sum(pkt)) & 0xFF
        pkt.append(cs)
        if not _write_overlapped(h, pkt, timeout_ms=250):
            return None, False
        for _ in range(4):
            res = _read_overlapped(h, 17, timeout_ms=250)
            if not res:
                break
            if len(res) >= 8 and res[0] == 0x08 and res[1] == 0x04:
                pct = res[6]
                charging = res[7] in (1, 2)
                if 0 <= pct <= 100:
                    return pct, charging
                return None, False
        return None, False
    finally:
        kernel32.CloseHandle(h)


def _query_corsair_bragi(info: HidInterfaceInfo) -> tuple[int | None, bool]:
    """Query Corsair Bragi 2.4G peripherals (VID 0x1B1C, UsagePage 0xFF42)."""
    h = _open_rw(info.path, overlapped=True)
    if not h:
        return None, False
    try:
        out_len = max(info.out_len, 64)
        in_len = max(info.in_len, 64)
        cmd = [0x00, 0x07, 0x01, 0x0F] + [0x00] * (out_len - 4)
        if not _write_overlapped(h, cmd, timeout_ms=250):
            return None, False
        for _ in range(4):
            res = _read_overlapped(h, in_len, timeout_ms=250)
            if not res:
                break
            if len(res) >= 6 and res[3] == 0x0F:
                raw_val = res[4] | (res[5] << 8)
                pct = raw_val // 10 if raw_val > 100 else raw_val
                if 0 <= pct <= 100:
                    return pct, False
        return None, False
    finally:
        kernel32.CloseHandle(h)


def _query_rapoo(info: HidInterfaceInfo) -> tuple[int | None, bool]:
    """Query Rapoo 2.4G wireless mice (VID 0x24AE) via 0xBB telemetry report."""
    h = _open_rw(info.path, overlapped=True)
    if not h:
        return None, False
    try:
        in_len = max(info.in_len, 7)
        for _ in range(3):
            res = _read_overlapped(h, in_len, timeout_ms=250)
            if not res:
                break
            if len(res) >= 7 and res[0] == 0xBB:
                charging = res[5] == 0x02
                pct = res[6]
                if 0 <= pct <= 100:
                    return pct, charging
        return None, False
    finally:
        kernel32.CloseHandle(h)


_KNOWN_VIDS = {0x0B05, 0x5253, 0x3554, 0x046D, 0x1532, 0x373B, 0x1B1C, 0x24AE, 0x045E, 0x054C, 0x057E}
_PROBE_CACHE: dict[str, str | None] = {}


def scan_hid_summary() -> str:
    """Read-only diagnostic scan of connected USB HID interfaces for troubleshooting."""
    lines: list[str] = []
    seen: set[tuple[int, int, int, int, int, int, int]] = set()
    for info in _enumerate_hid_interfaces():
        if "vid_" not in info.path.lower():
            continue
        sig = (info.vid, info.pid, info.usage_page, info.usage, info.in_len, info.out_len, info.feat_len)
        if sig in seen:
            continue
        seen.add(sig)
        prod = info.product or "(Unknown)"
        lines.append(
            f"VID={info.vid:04X} PID={info.pid:04X} UP={info.usage_page:04X} U={info.usage:04X} "
            f"In={info.in_len} Out={info.out_len} Feat={info.feat_len} | {prod}"
        )
    return "\n".join(lines) if lines else "未检测到 USB HID 设备"


def poll_all_24g_devices(auto_probe_generic: bool = True) -> list[DeviceBatteryStatus]:
    """Auto-discover and poll all supported 2.4GHz HID devices currently connected."""
    now = time.time()
    interfaces = _enumerate_hid_interfaces()
    devices: list[DeviceBatteryStatus] = []
    seen_keys: set[str] = set()

    for info in interfaces:
        # 1. ASUS ROG PELTA (2.4GHz)
        if info.vid == 0x0B05 and info.pid == 0x1B84 and info.usage_page == 0xFF00 and info.usage == 0x0001:
            key = "hid_0b05_1b84"
            if key not in seen_keys:
                seen_keys.add(key)
                pct, charging = _query_rog_pelta(info)
                devices.append(
                    DeviceBatteryStatus(
                        key=key,
                        name=info.product or "ROG PELTA 耳机",
                        short_label="耳",
                        battery=pct,
                        charging=charging,
                        dongle_present=True,
                        awake=pct is not None,
                        last_updated=now if pct is not None else 0.0,
                    )
                )

        # 2. MCHOSE Realtek 2.4G series (VID 0x5253, UsagePage 0xFF01, Feat 65)
        elif info.vid == 0x5253 and info.usage_page == 0xFF01 and info.usage == 0x0001 and info.feat_len == 65:
            key = f"hid_{info.vid:04x}_{info.pid:04x}"
            if key not in seen_keys:
                seen_keys.add(key)
                pct, charging = _query_mchose_realtek(info)
                devices.append(
                    DeviceBatteryStatus(
                        key=key,
                        name=info.product or "MCHOSE 2.4G 设备",
                        short_label="鼠",
                        battery=pct,
                        charging=charging,
                        dongle_present=True,
                        awake=pct is not None,
                        last_updated=now if pct is not None else 0.0,
                    )
                )

        # 3. Compx 2.4G generic receivers (VID 0x3554, UsagePage 0xFF02, 20-byte frames)
        elif info.vid == 0x3554 and info.usage_page == 0xFF02 and info.usage == 0x0002 and info.out_len == 20:
            key = f"hid_{info.vid:04x}_{info.pid:04x}"
            if key not in seen_keys:
                seen_keys.add(key)
                pct, charging = _query_compx_24g(info)
                prod = info.product
                if not prod or prod == "2.4G Wireless Receiver":
                    prod = "Compx 2.4G 键鼠"
                devices.append(
                    DeviceBatteryStatus(
                        key=key,
                        name=prod,
                        short_label="键",
                        battery=pct,
                        charging=charging,
                        dongle_present=True,
                        awake=pct is not None,
                        last_updated=now if pct is not None else 0.0,
                    )
                )

        # 4. Logitech HID++ 2.0 receivers (VID 0x046D, UsagePage 0xFF00, 20-byte long reports)
        elif info.vid == 0x046D and info.usage_page == 0xFF00 and info.in_len == 20 and info.out_len == 20:
            key_prefix = f"hid_{info.vid:04x}_{info.pid:04x}"
            if key_prefix not in seen_keys:
                seen_keys.add(key_prefix)
                for idx, (label, pct, charging) in enumerate(_query_logitech_hidpp(info)):
                    devices.append(
                        DeviceBatteryStatus(
                            key=f"{key_prefix}_{idx}",
                            name=label,
                            short_label="罗",
                            battery=pct,
                            charging=charging,
                            dongle_present=True,
                            awake=pct is not None,
                            last_updated=now if pct is not None else 0.0,
                        )
                    )

        # 5. Razer 2.4G wireless peripherals (VID 0x1532, 90/91-byte Feature Report)
        elif info.vid == 0x1532 and info.feat_len >= 90:
            key = f"hid_{info.vid:04x}_{info.pid:04x}"
            if key not in seen_keys:
                seen_keys.add(key)
                pct, charging = _query_razer(info)
                devices.append(
                    DeviceBatteryStatus(
                        key=key,
                        name=info.product or "Razer 2.4G 设备",
                        short_label="雷",
                        battery=pct,
                        charging=charging,
                        dongle_present=True,
                        awake=pct is not None,
                        last_updated=now if pct is not None else 0.0,
                    )
                )

        # 6. VGN / VXE / ATK 2.4G mice (VID 0x373B or 0x3554, 17-byte 0x08 0x04 reports)
        elif info.vid in (0x373B, 0x3554) and info.in_len == 17 and info.out_len == 17 and info.usage_page >= 0xFF00:
            key = f"hid_{info.vid:04x}_{info.pid:04x}"
            if key not in seen_keys:
                seen_keys.add(key)
                pct, charging = _query_vgn_atk(info)
                devices.append(
                    DeviceBatteryStatus(
                        key=key,
                        name=info.product or "VGN/ATK 2.4G 鼠标",
                        short_label="鼠",
                        battery=pct,
                        charging=charging,
                        dongle_present=True,
                        awake=pct is not None,
                        last_updated=now if pct is not None else 0.0,
                    )
                )

        # 7. Corsair Bragi 2.4G peripherals (VID 0x1B1C, UsagePage 0xFF42)
        elif info.vid == 0x1B1C and info.usage_page == 0xFF42:
            key = f"hid_{info.vid:04x}_{info.pid:04x}"
            if key not in seen_keys:
                seen_keys.add(key)
                pct, charging = _query_corsair_bragi(info)
                devices.append(
                    DeviceBatteryStatus(
                        key=key,
                        name=info.product or "Corsair 2.4G 设备",
                        short_label="船",
                        battery=pct,
                        charging=charging,
                        dongle_present=True,
                        awake=pct is not None,
                        last_updated=now if pct is not None else 0.0,
                    )
                )

        # 8. Rapoo 2.4G wireless mice (VID 0x24AE, vendor interface pushing 0xBB reports)
        elif info.vid == 0x24AE and info.usage_page >= 0xFF00 and info.in_len >= 7:
            key = f"hid_{info.vid:04x}_{info.pid:04x}"
            if key not in seen_keys:
                seen_keys.add(key)
                pct, charging = _query_rapoo(info)
                devices.append(
                    DeviceBatteryStatus(
                        key=key,
                        name=info.product or "Rapoo 2.4G 鼠标",
                        short_label="柏",
                        battery=pct,
                        charging=charging,
                        dongle_present=True,
                        awake=pct is not None,
                        last_updated=now if pct is not None else 0.0,
                    )
                )

        # 9. Safe cached auto-probe for unknown USB 2.4G receivers using common 17/20-byte protocols
        elif (
            auto_probe_generic
            and "vid_" in info.path.lower()
            and info.vid not in _KNOWN_VIDS
            and info.usage_page >= 0xFF00
            and ((info.in_len == 17 and info.out_len == 17) or (info.in_len == 20 and info.out_len == 20))
        ):
            key = f"hid_{info.vid:04x}_{info.pid:04x}"
            if key in seen_keys:
                continue
            cached = _PROBE_CACHE.get(info.path, "UNPROBED")
            if cached is None:
                continue
            proto = cached
            pct, charging = None, False
            if proto == "UNPROBED":
                if info.in_len == 17:
                    pct, charging = _query_vgn_atk(info)
                    proto = "vgn17" if pct is not None else None
                else:
                    pct, charging = _query_compx_24g(info)
                    proto = "compx20" if pct is not None else None
                _PROBE_CACHE[info.path] = proto
            elif proto == "vgn17":
                pct, charging = _query_vgn_atk(info)
            elif proto == "compx20":
                pct, charging = _query_compx_24g(info)

            if proto is not None:
                seen_keys.add(key)
                devices.append(
                    DeviceBatteryStatus(
                        key=key,
                        name=info.product or f"2.4G 设备 ({info.vid:04X}:{info.pid:04X})",
                        short_label="无",
                        battery=pct,
                        charging=charging,
                        dongle_present=True,
                        awake=pct is not None,
                        last_updated=now if pct is not None else 0.0,
                    )
                )

    return devices


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
