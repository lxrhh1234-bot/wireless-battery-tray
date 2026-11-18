"""Configuration persistence for the 2.4GHz Wireless Battery Tray app."""

from __future__ import annotations

import json
import os
from typing import Any

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG: dict[str, Any] = {
    "poll_interval": 30,
    "low_battery_notify": True,
    "low_battery_threshold": 20,
    "hide_disconnected": False,
    "show_bluetooth": True,
    "aliases": {
        "rog_pelta": "ROG PELTA 耳机",
        "mchose_a7": "MCHOSE A7 Pro 鼠标",
        "compx_24g": "Compx 2.4G 键盘",
    },
}


def load_config() -> dict[str, Any]:
    """Load configuration from config.json, merging with defaults."""
    cfg: dict[str, Any] = {
        "poll_interval": DEFAULT_CONFIG["poll_interval"],
        "low_battery_notify": DEFAULT_CONFIG["low_battery_notify"],
        "low_battery_threshold": DEFAULT_CONFIG["low_battery_threshold"],
        "hide_disconnected": DEFAULT_CONFIG["hide_disconnected"],
        "show_bluetooth": DEFAULT_CONFIG["show_bluetooth"],
        "aliases": dict(DEFAULT_CONFIG["aliases"]),
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                if "poll_interval" in data:
                    cfg["poll_interval"] = int(data["poll_interval"])
                if "low_battery_notify" in data:
                    cfg["low_battery_notify"] = bool(data["low_battery_notify"])
                if "low_battery_threshold" in data:
                    cfg["low_battery_threshold"] = int(data["low_battery_threshold"])
                if "hide_disconnected" in data:
                    cfg["hide_disconnected"] = bool(data["hide_disconnected"])
                if "show_bluetooth" in data:
                    cfg["show_bluetooth"] = bool(data["show_bluetooth"])
                if isinstance(data.get("aliases"), dict):
                    cfg["aliases"].update(data["aliases"])
        except Exception:
            pass
    return cfg


def save_config(cfg: dict[str, Any]) -> None:
    """Persist configuration to config.json."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
