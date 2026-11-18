"""Minimalist light-mode Tkinter taskbar flyout and settings window."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import tkinter as tk
from typing import Any, Callable

from PIL import Image, ImageDraw, ImageTk

from hid_devices import DeviceBatteryStatus, scan_hid_summary
from i18n import tr

# Clean White / Antigravity-Gemini-GPT Light Palette
BG_WHITE = "#FFFFFF"
BG_SURFACE = "#F8FAFC"
BG_HOVER = "#F1F5F9"
BORDER_HAIRLINE = "#E2E8F0"
TEXT_PRIMARY = "#0F172A"
TEXT_SECONDARY = "#64748B"

COLOR_GREEN = "#22C55E"
BG_GREEN_SOFT = "#ECFDF5"
COLOR_BLUE = "#3B82F6"
BG_BLUE_SOFT = "#EFF6FF"
COLOR_AMBER = "#F59E0B"
BG_AMBER_SOFT = "#FFFBEB"
COLOR_RED = "#EF4444"
BG_RED_SOFT = "#FEF2F2"
COLOR_GRAY = "#94A3B8"
BG_GRAY_SOFT = "#F1F5F9"

SPI_GETWORKAREA = 48


def _get_work_area() -> tuple[int, int, int, int]:
    rect = wintypes.RECT()
    if ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
        return rect.left, rect.top, rect.right, rect.bottom
    return 0, 0, 1920, 1032


def _apply_rounded_corners(win: tk.Toplevel, width: int, height: int) -> None:
    """Apply native Windows 11 DWM rounded corners (or Win10 region fallback)."""
    try:
        win.update_idletasks()
        hwnd = win.winfo_id()
        top_hwnd = ctypes.windll.user32.GetParent(hwnd) or hwnd
        pref = ctypes.c_int(2)  # DWMWCP_ROUND
        hr = ctypes.windll.dwmapi.DwmSetWindowAttribute(
            wintypes.HWND(top_hwnd), 33, ctypes.byref(pref), 4
        )
        if hr != 0:
            rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, width + 1, height + 1, 16, 16)
            ctypes.windll.user32.SetWindowRgn(wintypes.HWND(top_hwnd), rgn, True)
    except Exception:
        pass


def _status_palette(pct: int | None, charging: bool) -> tuple[str, str]:
    if pct is None:
        return COLOR_GRAY, BG_GRAY_SOFT
    if charging:
        return COLOR_BLUE, BG_BLUE_SOFT
    if pct >= 50:
        return COLOR_GREEN, BG_GREEN_SOFT
    if pct >= 20:
        return COLOR_AMBER, BG_AMBER_SOFT
    return COLOR_RED, BG_RED_SOFT


def _infer_device_kind(st: DeviceBatteryStatus, display_name: str) -> str:
    lower = display_name.lower()
    if any(k in lower for k in ("鼠标", "mouse", "a7", "gpw", "viper", "basilisk", "rapoo", "vgn", "atk", "vxe")):
        return "mouse"
    if any(k in lower for k in ("键盘", "keyboard", "f75", "hi75", "g75", "g87", "compx")):
        return "keyboard"
    if any(k in lower for k in ("耳机", "headset", "pelta", "enco", "airpods", "buds", "arctis", "hs80")):
        return "headset"
    if any(k in lower for k in ("手柄", "controller", "xbox", "dualsense")):
        return "gamepad"
    if st.short_label == "鼠":
        return "mouse"
    if st.short_label == "键":
        return "keyboard"
    if st.short_label == "耳":
        return "headset"
    return "wireless"


_ICON_CACHE: dict[str, ImageTk.PhotoImage] = {}


def _get_device_photo(kind: str) -> ImageTk.PhotoImage:
    """Render and cache a crisp 18x18 anti-aliased device icon."""
    if kind in _ICON_CACHE:
        return _ICON_CACHE[kind]

    hi = 36
    img = Image.new("RGBA", (hi, hi), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    fg = (71, 85, 105, 255)  # #475569 slate

    if kind == "mouse":
        d.rounded_rectangle([9, 3, 27, 33], radius=9, outline=fg, width=3)
        d.line([18, 3, 18, 15], fill=fg, width=2)
        d.rounded_rectangle([16, 8, 20, 14], radius=2, fill=fg)
    elif kind == "keyboard":
        d.rounded_rectangle([2, 8, 34, 28], radius=4, outline=fg, width=3)
        for x in (7, 13, 19, 25):
            d.rectangle([x, 13, x + 3, 16], fill=fg)
        d.rectangle([10, 20, 26, 23], fill=fg)
    elif kind == "headset":
        d.arc([5, 4, 31, 30], start=180, end=360, fill=fg, width=3)
        d.rounded_rectangle([4, 17, 10, 29], radius=3, fill=fg)
        d.rounded_rectangle([26, 17, 32, 29], radius=3, fill=fg)
    elif kind == "gamepad":
        d.rounded_rectangle([3, 10, 33, 27], radius=6, outline=fg, width=3)
        d.line([10, 15, 10, 22], fill=fg, width=2)
        d.line([7, 18, 14, 18], fill=fg, width=2)
        d.ellipse([22, 15, 25, 18], fill=fg)
        d.ellipse([26, 19, 29, 22], fill=fg)
    else:
        d.arc([4, 10, 32, 38], start=220, end=320, fill=fg, width=3)
        d.arc([10, 16, 26, 32], start=220, end=320, fill=fg, width=3)
        d.ellipse([16, 24, 20, 28], fill=fg)

    photo = ImageTk.PhotoImage(img.resize((18, 18), Image.Resampling.LANCZOS))
    _ICON_CACHE[kind] = photo
    return photo


def _make_device_icon(parent: tk.Frame, bg: str, kind: str) -> tk.Label:
    """Return a Label displaying the crisp 18x18 device icon."""
    photo = _get_device_photo(kind)
    lbl = tk.Label(parent, image=photo, bg=bg, bd=0)
    lbl._img_ref = photo  # keep reference
    return lbl


class BatteryFlyout(tk.Toplevel):
    """Compact white flyout anchored directly above the tray icon on the taskbar."""

    def __init__(
        self,
        parent: tk.Tk,
        statuses: list[DeviceBatteryStatus],
        aliases: dict[str, str],
        anchor_x: int,
        hide_disconnected: bool,
        lang: str,
        on_refresh: Callable[[], None],
        on_open_settings: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self.withdraw()
        self.lang = lang
        self.hide_disconnected = hide_disconnected
        self.on_refresh = on_refresh
        self.on_open_settings = on_open_settings
        self.on_exit = on_exit

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=BG_WHITE)

        root_frame = tk.Frame(self, bg=BG_WHITE, padx=14, pady=12)
        root_frame.pack(fill="both", expand=True)

        # Compact Header
        header = tk.Frame(root_frame, bg=BG_WHITE)
        header.pack(fill="x", pady=(0, 8))

        tk.Label(
            header,
            text=tr(lang, "flyout_title"),
            font=("Microsoft YaHei UI", 9, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_WHITE,
        ).pack(side="left")

        actions = tk.Frame(header, bg=BG_WHITE)
        actions.pack(side="right")
        self._link_btn(actions, tr(lang, "refresh"), self.on_refresh).pack(side="left", padx=(0, 8))
        self._link_btn(actions, tr(lang, "settings"), self._handle_settings).pack(side="left", padx=(0, 8))
        self._link_btn(actions, tr(lang, "exit"), self._handle_exit, muted=True).pack(side="left")

        # Compact Device Rows
        self.list_frame = tk.Frame(root_frame, bg=BG_WHITE)
        self.list_frame.pack(fill="both", expand=True)
        self.render_devices(statuses, aliases, hide_disconnected=hide_disconnected, lang=lang)

        # Position centered on tray icon X, flush above taskbar
        self.update_idletasks()
        win_w = 246
        win_h = self.winfo_reqheight()
        wa_left, _t, wa_right, wa_bottom = _get_work_area()
        pos_x = max(wa_left + 8, min(anchor_x - win_w // 2, wa_right - win_w - 8))
        pos_y = wa_bottom - win_h - 6
        self.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        _apply_rounded_corners(self, win_w, win_h)
        self.deiconify()
        self.lift()
        self.focus_force()

        self.bind("<FocusOut>", self._on_focus_out)
        self.bind("<Escape>", lambda _e: self.destroy())

    def _link_btn(
        self, parent: tk.Frame, text: str, command: Callable[[], None], muted: bool = False
    ) -> tk.Label:
        base_fg = TEXT_SECONDARY if muted else COLOR_BLUE
        lbl = tk.Label(
            parent,
            text=text,
            font=("Microsoft YaHei UI", 8),
            fg=base_fg,
            bg=BG_WHITE,
            cursor="hand2",
        )
        lbl.bind("<Enter>", lambda _e: lbl.configure(fg=TEXT_PRIMARY))
        lbl.bind("<Leave>", lambda _e: lbl.configure(fg=base_fg))
        lbl.bind("<Button-1>", lambda _e: command())
        return lbl

    def render_devices(
        self,
        statuses: list[DeviceBatteryStatus],
        aliases: dict[str, str],
        hide_disconnected: bool | None = None,
        lang: str | None = None,
    ) -> None:
        if hide_disconnected is not None:
            self.hide_disconnected = hide_disconnected
        if lang is not None:
            self.lang = lang
        visible = [st for st in statuses if st.dongle_present or not self.hide_disconnected]

        sig = (
            self.lang,
            tuple(
                (st.key, aliases.get(st.key, st.name), st.battery, st.charging, st.dongle_present, st.awake)
                for st in visible
            ),
        )
        if sig == getattr(self, "_last_render_sig", None):
            return
        self._last_render_sig = sig

        for child in self.list_frame.winfo_children():
            child.destroy()

        if not visible:
            tk.Label(
                self.list_frame,
                text=tr(self.lang, "empty_devices"),
                font=("Microsoft YaHei UI", 8),
                fg=TEXT_SECONDARY,
                bg=BG_SURFACE,
                justify="center",
                pady=12,
            ).pack(fill="x")
            return

        for idx, st in enumerate(visible):
            name = aliases.get(st.key, st.name)
            fg_color, soft_bg = _status_palette(st.battery, st.charging)

            row_card = tk.Frame(self.list_frame, bg=BG_SURFACE, padx=9, pady=7)
            pad_bottom = 0 if idx == len(visible) - 1 else 6
            row_card.pack(fill="x", pady=(0, pad_bottom))

            top = tk.Frame(row_card, bg=BG_SURFACE)
            top.pack(fill="x")

            kind = _infer_device_kind(st, name)
            _make_device_icon(top, BG_SURFACE, kind).pack(side="left", padx=(0, 6))

            tk.Label(
                top,
                text=name,
                font=("Microsoft YaHei UI", 8, "bold"),
                fg=TEXT_PRIMARY,
                bg=BG_SURFACE,
                anchor="w",
            ).pack(side="left")

            if st.battery is not None:
                if st.charging:
                    pill_text = f"⚡ {st.battery}%"
                elif not st.awake:
                    pill_text = f"{tr(self.lang, 'sleep')} {st.battery}%"
                else:
                    pill_text = f"{st.battery}%"
            elif st.dongle_present:
                pill_text = tr(self.lang, "sleep")
            else:
                pill_text = tr(self.lang, "offline")

            tk.Label(
                top,
                text=pill_text,
                font=("Microsoft YaHei UI", 8, "bold"),
                fg=fg_color if st.battery is not None else TEXT_SECONDARY,
                bg=soft_bg,
                padx=6,
                pady=1,
            ).pack(side="right")

            bar = tk.Canvas(row_card, height=5, bg=BORDER_HAIRLINE, highlightthickness=0)
            bar.pack(fill="x", pady=(6, 0))
            if st.battery is not None and st.battery > 0:
                fill_w = max(5, int(202 * (st.battery / 100.0)))
                bar.create_rectangle(0, 0, fill_w, 5, fill=fg_color, outline="")

    def _on_focus_out(self, _event: tk.Event) -> None:
        self.after(100, self._check_close)

    def _check_close(self) -> None:
        if self.winfo_exists() and self.focus_get() is None:
            self.destroy()

    def _handle_settings(self) -> None:
        self.destroy()
        self.on_open_settings()

    def _handle_exit(self) -> None:
        self.destroy()
        self.on_exit()


class SettingsWindow(tk.Toplevel):
    """Minimalist white Settings window for device aliases, language, startup, and refresh interval."""

    def __init__(
        self,
        parent: tk.Tk,
        config: dict[str, Any],
        discovered_devices: list[DeviceBatteryStatus],
        startup_enabled: bool,
        on_save: Callable[[dict[str, Any], bool], None],
    ) -> None:
        super().__init__(parent)
        self.on_save = on_save
        self.lang = config.get("language", "zh")
        self._existing_aliases = dict(config.get("aliases", {}))
        self.title(tr(self.lang, "settings_title"))
        self.configure(bg=BG_WHITE)
        self.resizable(False, False)
        self.attributes("-topmost", True)

        body = tk.Frame(self, bg=BG_WHITE, padx=20, pady=16)
        body.pack(fill="both", expand=True)

        # 1. Device Aliases
        self._section_title(body, tr(self.lang, "sec_devices"))
        alias_box = tk.Frame(
            body, bg=BG_SURFACE, padx=10, pady=8, highlightbackground=BORDER_HAIRLINE, highlightthickness=1
        )
        alias_box.pack(fill="x", pady=(4, 12))

        self.alias_vars: dict[str, tk.StringVar] = {}
        if not discovered_devices:
            tk.Label(
                alias_box,
                text=tr(self.lang, "no_devices_detected"),
                font=("Microsoft YaHei UI", 8),
                fg=TEXT_SECONDARY,
                bg=BG_SURFACE,
                pady=4,
            ).pack(fill="x")
        else:
            for st in discovered_devices:
                row = tk.Frame(alias_box, bg=BG_SURFACE)
                row.pack(fill="x", pady=3)
                display_name = self._existing_aliases.get(st.key, st.name)
                kind = _infer_device_kind(st, display_name)
                _make_device_icon(row, BG_SURFACE, kind).pack(side="left", padx=(0, 8))
                var = tk.StringVar(value=display_name)
                self.alias_vars[st.key] = var
                tk.Entry(
                    row,
                    textvariable=var,
                    font=("Microsoft YaHei UI", 9),
                    fg=TEXT_PRIMARY,
                    bg=BG_WHITE,
                    relief="flat",
                    highlightthickness=1,
                    highlightbackground=BORDER_HAIRLINE,
                ).pack(side="left", fill="x", expand=True, ipady=2)

        # 2. System
        self._section_title(body, tr(self.lang, "sec_system"))
        sys_box = tk.Frame(
            body, bg=BG_SURFACE, padx=10, pady=8, highlightbackground=BORDER_HAIRLINE, highlightthickness=1
        )
        sys_box.pack(fill="x", pady=(4, 14))

        lang_row = tk.Frame(sys_box, bg=BG_SURFACE)
        lang_row.pack(fill="x", pady=(0, 4))
        tk.Label(
            lang_row,
            text=tr(self.lang, "lang_label"),
            font=("Microsoft YaHei UI", 9),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
        ).pack(side="left")
        self.lang_var = tk.StringVar(value=self.lang)
        for val, lbl in (("en", "English"), ("zh", "中文")):
            tk.Radiobutton(
                lang_row,
                text=lbl,
                variable=self.lang_var,
                value=val,
                font=("Microsoft YaHei UI", 9),
                fg=TEXT_PRIMARY,
                bg=BG_SURFACE,
                selectcolor=BG_WHITE,
                activebackground=BG_SURFACE,
            ).pack(side="right", padx=(6, 0))

        self.startup_var = tk.BooleanVar(value=startup_enabled)
        tk.Checkbutton(
            sys_box,
            text=tr(self.lang, "startup"),
            variable=self.startup_var,
            font=("Microsoft YaHei UI", 9),
            fg=TEXT_PRIMARY,
            bg=BG_SURFACE,
            selectcolor=BG_WHITE,
            activebackground=BG_SURFACE,
        ).pack(anchor="w")

        self.hide_disc_var = tk.BooleanVar(value=bool(config.get("hide_disconnected", True)))
        tk.Checkbutton(
            sys_box,
            text=tr(self.lang, "hide_disconnected"),
            variable=self.hide_disc_var,
            font=("Microsoft YaHei UI", 9),
            fg=TEXT_PRIMARY,
            bg=BG_SURFACE,
            selectcolor=BG_WHITE,
            activebackground=BG_SURFACE,
        ).pack(anchor="w", pady=(3, 0))

        self.show_bt_var = tk.BooleanVar(value=bool(config.get("show_bluetooth", True)))
        tk.Checkbutton(
            sys_box,
            text=tr(self.lang, "show_bluetooth"),
            variable=self.show_bt_var,
            font=("Microsoft YaHei UI", 9),
            fg=TEXT_PRIMARY,
            bg=BG_SURFACE,
            selectcolor=BG_WHITE,
            activebackground=BG_SURFACE,
        ).pack(anchor="w", pady=(3, 0))

        self.auto_probe_var = tk.BooleanVar(value=bool(config.get("auto_probe_generic", True)))
        tk.Checkbutton(
            sys_box,
            text=tr(self.lang, "auto_probe"),
            variable=self.auto_probe_var,
            font=("Microsoft YaHei UI", 9),
            fg=TEXT_PRIMARY,
            bg=BG_SURFACE,
            selectcolor=BG_WHITE,
            activebackground=BG_SURFACE,
        ).pack(anchor="w", pady=(3, 0))

        notify_row = tk.Frame(sys_box, bg=BG_SURFACE)
        notify_row.pack(fill="x", pady=(3, 0))
        self.notify_var = tk.BooleanVar(value=bool(config.get("low_battery_notify", True)))
        tk.Checkbutton(
            notify_row,
            text=tr(self.lang, "low_batt_alert"),
            variable=self.notify_var,
            font=("Microsoft YaHei UI", 9),
            fg=TEXT_PRIMARY,
            bg=BG_SURFACE,
            selectcolor=BG_WHITE,
            activebackground=BG_SURFACE,
        ).pack(side="left")
        self.thresh_var = tk.IntVar(value=int(config.get("low_battery_threshold", 20)))
        tk.Spinbox(
            notify_row,
            from_=5,
            to=50,
            textvariable=self.thresh_var,
            width=5,
            font=("Microsoft YaHei UI", 9),
            fg=TEXT_PRIMARY,
            bg=BG_WHITE,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_HAIRLINE,
        ).pack(side="right")

        poll_row = tk.Frame(sys_box, bg=BG_SURFACE)
        poll_row.pack(fill="x", pady=(6, 0))
        tk.Label(
            poll_row,
            text=tr(self.lang, "poll_interval"),
            font=("Microsoft YaHei UI", 9),
            fg=TEXT_SECONDARY,
            bg=BG_SURFACE,
        ).pack(side="left")
        self.poll_var = tk.IntVar(value=int(config.get("poll_interval", 30)))
        tk.Spinbox(
            poll_row,
            from_=10,
            to=300,
            textvariable=self.poll_var,
            width=6,
            font=("Microsoft YaHei UI", 9),
            fg=TEXT_PRIMARY,
            bg=BG_WHITE,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_HAIRLINE,
        ).pack(side="right")

        # Footer Buttons
        btn_row = tk.Frame(body, bg=BG_WHITE)
        btn_row.pack(fill="x")

        tk.Button(
            btn_row,
            text=tr(self.lang, "scan_hid"),
            command=self._open_scan_dialog,
            font=("Microsoft YaHei UI", 8),
            fg=COLOR_BLUE,
            bg=BG_BLUE_SOFT,
            activebackground=BG_HOVER,
            relief="flat",
            padx=10,
            pady=5,
            cursor="hand2",
        ).pack(side="left")

        tk.Button(
            btn_row,
            text=tr(self.lang, "cancel"),
            command=self.destroy,
            font=("Microsoft YaHei UI", 9),
            fg=TEXT_PRIMARY,
            bg=BG_SURFACE,
            activebackground=BG_HOVER,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_HAIRLINE,
            padx=14,
            pady=5,
            cursor="hand2",
        ).pack(side="right", padx=(8, 0))

        tk.Button(
            btn_row,
            text=tr(self.lang, "save"),
            command=self._save,
            font=("Microsoft YaHei UI", 9, "bold"),
            fg=BG_WHITE,
            bg=TEXT_PRIMARY,
            activebackground="#1E293B",
            activeforeground=BG_WHITE,
            relief="flat",
            padx=16,
            pady=5,
            cursor="hand2",
        ).pack(side="right")

        self.update_idletasks()
        w, h = 380, self.winfo_reqheight()
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.focus_force()

    def _section_title(self, parent: tk.Frame, text: str) -> None:
        tk.Label(
            parent,
            text=text,
            font=("Microsoft YaHei UI", 9, "bold"),
            fg=TEXT_SECONDARY,
            bg=BG_WHITE,
            anchor="w",
        ).pack(fill="x")

    def _open_scan_dialog(self) -> None:
        win = tk.Toplevel(self)
        win.title(tr(self.lang, "scan_title"))
        win.configure(bg=BG_WHITE)
        win.attributes("-topmost", True)
        frame = tk.Frame(win, bg=BG_WHITE, padx=14, pady=12)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text=tr(self.lang, "scan_desc"),
            font=("Microsoft YaHei UI", 9),
            fg=TEXT_SECONDARY,
            bg=BG_WHITE,
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        txt = tk.Text(
            frame,
            font=("Consolas", 9),
            fg=TEXT_PRIMARY,
            bg=BG_SURFACE,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_HAIRLINE,
            width=72,
            height=14,
        )
        txt.pack(fill="both", expand=True)
        summary = scan_hid_summary()
        txt.insert("1.0", summary)
        txt.configure(state="disabled")

        def copy_all() -> None:
            win.clipboard_clear()
            win.clipboard_append(summary)

        btn_f = tk.Frame(frame, bg=BG_WHITE)
        btn_f.pack(fill="x", pady=(8, 0))
        tk.Button(
            btn_f,
            text=tr(self.lang, "copy_all"),
            command=copy_all,
            font=("Microsoft YaHei UI", 9),
            fg=BG_WHITE,
            bg=TEXT_PRIMARY,
            relief="flat",
            padx=12,
            pady=4,
            cursor="hand2",
        ).pack(side="right")

    def _save(self) -> None:
        try:
            poll_sec = max(10, min(300, int(self.poll_var.get())))
        except Exception:
            poll_sec = 30
        try:
            thresh = max(5, min(50, int(self.thresh_var.get())))
        except Exception:
            thresh = 20
        merged_aliases = dict(self._existing_aliases)
        for k, v in self.alias_vars.items():
            val = v.get().strip()
            if val:
                merged_aliases[k] = val
        new_cfg = {
            "language": self.lang_var.get(),
            "poll_interval": poll_sec,
            "low_battery_notify": bool(self.notify_var.get()),
            "low_battery_threshold": thresh,
            "hide_disconnected": bool(self.hide_disc_var.get()),
            "show_bluetooth": bool(self.show_bt_var.get()),
            "auto_probe_generic": bool(self.auto_probe_var.get()),
            "aliases": merged_aliases,
        }
        self.on_save(new_cfg, self.startup_var.get())
        self.destroy()
