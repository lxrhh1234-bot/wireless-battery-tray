"""Minimalist light-mode Tkinter taskbar flyout and settings window."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import tkinter as tk
from typing import Any, Callable

from hid_devices import DEVICE_DEFINITIONS, DeviceBatteryStatus

# Clean White / Antigravity-Gemini-GPT Light Palette
BG_WHITE = "#FFFFFF"
BG_SURFACE = "#F8FAFC"
BG_HOVER = "#F1F5F9"
BORDER_HAIRLINE = "#E2E8F0"
TEXT_PRIMARY = "#0F172A"
TEXT_SECONDARY = "#64748B"

COLOR_GREEN = "#10B981"
BG_GREEN_SOFT = "#ECFDF5"
COLOR_BLUE = "#2563EB"
BG_BLUE_SOFT = "#EFF6FF"
COLOR_AMBER = "#D97706"
BG_AMBER_SOFT = "#FFFBEB"
COLOR_RED = "#DC2626"
BG_RED_SOFT = "#FEF2F2"
COLOR_GRAY = "#94A3B8"
BG_GRAY_SOFT = "#F1F5F9"

SPI_GETWORKAREA = 48


def _get_work_area() -> tuple[int, int, int, int]:
    rect = wintypes.RECT()
    if ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0):
        return rect.left, rect.top, rect.right, rect.bottom
    return 0, 0, 1920, 1032


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


class BatteryFlyout(tk.Toplevel):
    """Compact white flyout anchored directly above the tray icon on the taskbar."""

    def __init__(
        self,
        parent: tk.Tk,
        statuses: list[DeviceBatteryStatus],
        aliases: dict[str, str],
        anchor_x: int,
        hide_disconnected: bool,
        on_refresh: Callable[[], None],
        on_open_settings: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        super().__init__(parent)
        self.withdraw()
        self.hide_disconnected = hide_disconnected
        self.on_refresh = on_refresh
        self.on_open_settings = on_open_settings
        self.on_exit = on_exit

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.configure(bg=BORDER_HAIRLINE)

        root_frame = tk.Frame(self, bg=BG_WHITE, padx=12, pady=10)
        root_frame.pack(fill="both", expand=True, padx=1, pady=1)

        # Compact Header
        header = tk.Frame(root_frame, bg=BG_WHITE)
        header.pack(fill="x", pady=(0, 8))

        tk.Label(
            header,
            text="设备电量",
            font=("Microsoft YaHei UI", 9, "bold"),
            fg=TEXT_PRIMARY,
            bg=BG_WHITE,
        ).pack(side="left")

        actions = tk.Frame(header, bg=BG_WHITE)
        actions.pack(side="right")
        self._link_btn(actions, "刷新", self.on_refresh).pack(side="left", padx=(0, 8))
        self._link_btn(actions, "设置", self._handle_settings).pack(side="left", padx=(0, 8))
        self._link_btn(actions, "退出", self._handle_exit, muted=True).pack(side="left")

        # Compact Device Rows
        self.list_frame = tk.Frame(root_frame, bg=BG_WHITE)
        self.list_frame.pack(fill="both", expand=True)
        self.render_devices(statuses, aliases)

        # Position centered on tray icon X, flush above taskbar
        self.update_idletasks()
        win_w = 246
        win_h = self.winfo_reqheight()
        wa_left, _t, wa_right, wa_bottom = _get_work_area()
        pos_x = max(wa_left + 8, min(anchor_x - win_w // 2, wa_right - win_w - 8))
        pos_y = wa_bottom - win_h - 6
        self.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
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
    ) -> None:
        if hide_disconnected is not None:
            self.hide_disconnected = hide_disconnected
        visible = [st for st in statuses if st.dongle_present or not self.hide_disconnected]

        sig = tuple(
            (st.key, aliases.get(st.key, st.name), st.battery, st.charging, st.dongle_present, st.awake)
            for st in visible
        )
        if sig == getattr(self, "_last_render_sig", None):
            return
        self._last_render_sig = sig

        for child in self.list_frame.winfo_children():
            child.destroy()

        if not visible:
            tk.Label(
                self.list_frame,
                text="未检测到已连接的 2.4GHz 设备",
                font=("Microsoft YaHei UI", 8),
                fg=TEXT_SECONDARY,
                bg=BG_SURFACE,
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
                    pill_text = f"休眠 {st.battery}%"
                else:
                    pill_text = f"{st.battery}%"
            elif st.dongle_present:
                pill_text = "休眠"
            else:
                pill_text = "未连接"

            tk.Label(
                top,
                text=pill_text,
                font=("Microsoft YaHei UI", 8, "bold"),
                fg=fg_color if st.battery is not None else TEXT_SECONDARY,
                bg=soft_bg,
                padx=6,
                pady=1,
            ).pack(side="right")

            # Clean 3px progress bar
            bar = tk.Canvas(row_card, height=3, bg=BORDER_HAIRLINE, highlightthickness=0)
            bar.pack(fill="x", pady=(5, 0))
            if st.battery is not None and st.battery > 0:
                fill_w = max(3, int(202 * (st.battery / 100.0)))
                bar.create_rectangle(0, 0, fill_w, 3, fill=fg_color, outline="")

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
    """Minimalist white Settings window for device aliases, startup, and refresh interval."""

    def __init__(
        self,
        parent: tk.Tk,
        config: dict[str, Any],
        startup_enabled: bool,
        on_save: Callable[[dict[str, Any], bool], None],
    ) -> None:
        super().__init__(parent)
        self.on_save = on_save
        self.title("设置 - 2.4GHz 电量监控")
        self.configure(bg=BG_WHITE)
        self.resizable(False, False)
        self.attributes("-topmost", True)

        body = tk.Frame(self, bg=BG_WHITE, padx=20, pady=16)
        body.pack(fill="both", expand=True)

        # 1. Device Aliases
        self._section_title(body, "设备名称")
        alias_box = tk.Frame(
            body, bg=BG_SURFACE, padx=10, pady=8, highlightbackground=BORDER_HAIRLINE, highlightthickness=1
        )
        alias_box.pack(fill="x", pady=(4, 12))

        self.alias_vars: dict[str, tk.StringVar] = {}
        for key, default_name, tag, _ in DEVICE_DEFINITIONS:
            row = tk.Frame(alias_box, bg=BG_SURFACE)
            row.pack(fill="x", pady=3)
            tk.Label(
                row,
                text=tag,
                font=("Microsoft YaHei UI", 8, "bold"),
                fg=TEXT_SECONDARY,
                bg=BG_HOVER,
                width=3,
                pady=2,
            ).pack(side="left", padx=(0, 8))
            var = tk.StringVar(value=config["aliases"].get(key, default_name))
            self.alias_vars[key] = var
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
        self._section_title(body, "系统")
        sys_box = tk.Frame(
            body, bg=BG_SURFACE, padx=10, pady=8, highlightbackground=BORDER_HAIRLINE, highlightthickness=1
        )
        sys_box.pack(fill="x", pady=(4, 14))

        self.startup_var = tk.BooleanVar(value=startup_enabled)
        tk.Checkbutton(
            sys_box,
            text="开机自动启动",
            variable=self.startup_var,
            font=("Microsoft YaHei UI", 9),
            fg=TEXT_PRIMARY,
            bg=BG_SURFACE,
            selectcolor=BG_WHITE,
            activebackground=BG_SURFACE,
        ).pack(anchor="w")

        self.hide_disc_var = tk.BooleanVar(value=bool(config.get("hide_disconnected", False)))
        tk.Checkbutton(
            sys_box,
            text="隐藏未连接接收器的设备",
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
            text="显示已连接的蓝牙设备电量",
            variable=self.show_bt_var,
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
            text="低电量桌面提醒（≤ %）:",
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
            text="后台刷新间隔（秒）:",
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
            text="取消",
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
            text="保存",
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
        w, h = 360, self.winfo_reqheight()
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

    def _save(self) -> None:
        try:
            poll_sec = max(10, min(300, int(self.poll_var.get())))
        except Exception:
            poll_sec = 30
        try:
            thresh = max(5, min(50, int(self.thresh_var.get())))
        except Exception:
            thresh = 20
        new_cfg = {
            "poll_interval": poll_sec,
            "low_battery_notify": bool(self.notify_var.get()),
            "low_battery_threshold": thresh,
            "hide_disconnected": bool(self.hide_disc_var.get()),
            "show_bluetooth": bool(self.show_bt_var.get()),
            "aliases": {k: v.get().strip() or k for k, v in self.alias_vars.items()},
        }
        self.on_save(new_cfg, self.startup_var.get())
        self.destroy()
