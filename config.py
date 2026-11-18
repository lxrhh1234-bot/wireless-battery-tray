"""Configuration persistence for the 2.4GHz & Bluetooth Wireless Battery Tray app."""

from __future__ import annotations

import json
import os
import sys
from typing import Any

_BASE_DIR = (
    os.path.dirname(os.path.abspath(sys.executable))
    if getattr(sys, "frozen", False)
    else os.path.dirname(os.path.abspath(__file__))
)
CONFIG_PATH = os.path.join(_BASE_DIR, "config.json")

DEFAULT_CONFIG: dict[str, Any] = {
    "language": "zh",
    "poll_interval": 30,
    "low_battery_notify": True,
    "low_battery_threshold": 20,
    "hide_disconnected": True,
    "show_bluetooth": True,
    "auto_probe_generic": True,
    "aliases": {},
}


def load_config() -> dict[str, Any]:
    """Load configuration from config.json, merging with defaults."""
    cfg: dict[str, Any] = {
        "language": DEFAULT_CONFIG["language"],
        "poll_interval": DEFAULT_CONFIG["poll_interval"],
        "low_battery_notify": DEFAULT_CONFIG["low_battery_notify"],
        "low_battery_threshold": DEFAULT_CONFIG["low_battery_threshold"],
        "hide_disconnected": DEFAULT_CONFIG["hide_disconnected"],
        "show_bluetooth": DEFAULT_CONFIG["show_bluetooth"],
        "auto_probe_generic": DEFAULT_CONFIG["auto_probe_generic"],
        "aliases": {},
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                if data.get("language") in ("zh", "en"):
                    cfg["language"] = data["language"]
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
                if "auto_probe_generic" in data:
                    cfg["auto_probe_generic"] = bool(data["auto_probe_generic"])
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
