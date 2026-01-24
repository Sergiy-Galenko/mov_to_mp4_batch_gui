# -*- coding: utf-8 -*-
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional

THEMES: Dict[str, Dict[str, str]] = {
    "light": {
        "bg": "#F7F5F2",
        "panel": "#FFFFFF",
        "text": "#1F2933",
        "muted": "#6B7280",
        "accent": "#2B6CB0",
        "accent_alt": "#1E4E8C",
        "border": "#E2E8F0",
        "success": "#0F766E",
        "warn": "#B45309",
        "error": "#B91C1C",
    },
    "dark": {
        "bg": "#1F2933",
        "panel": "#273142",
        "text": "#F3F4F6",
        "muted": "#9CA3AF",
        "accent": "#4DD0A7",
        "accent_alt": "#2E9E7B",
        "border": "#374151",
        "success": "#34D399",
        "warn": "#FBBF24",
        "error": "#F87171",
    },
}


def load_custom_theme(path: Path) -> Optional[Dict[str, str]]:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            merged = dict(THEMES["light"])
            merged.update({k: str(v) for k, v in data.items()})
            return merged
    except Exception:
        return None
    return None


def save_custom_theme(path: Path, theme: Dict[str, str]) -> None:
    try:
        with path.open("w", encoding="utf-8") as fh:
            json.dump(theme, fh, ensure_ascii=False, indent=2)
    except Exception:
        return


def apply_theme(root: tk.Tk, theme_name: str, custom: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    if theme_name == "custom" and custom:
        colors = custom
    else:
        colors = THEMES.get(theme_name, THEMES["light"])
    style = ttk.Style(root)
    style.theme_use("clam")

    base_font = ("Segoe UI", 10)
    title_font = ("Segoe UI Semibold", 14)
    style.configure("TFrame", background=colors["bg"])
    style.configure("Panel.TFrame", background=colors["panel"])
    style.configure("TLabel", background=colors["bg"], foreground=colors["text"], font=base_font)
    style.configure("Muted.TLabel", background=colors["bg"], foreground=colors["muted"], font=base_font)
    style.configure("Title.TLabel", background=colors["bg"], foreground=colors["text"], font=title_font)

    style.configure("TButton", background=colors["accent"], foreground=colors["panel"], padding=(10, 6))
    style.map(
        "TButton",
        background=[("active", colors["accent_alt"])],
        foreground=[("active", colors["panel"])],
    )
    style.configure("Secondary.TButton", background=colors["panel"], foreground=colors["text"], padding=(10, 6))
    style.map(
        "Secondary.TButton",
        background=[("active", colors["bg"])],
        foreground=[("active", colors["text"])],
    )

    style.configure("TEntry", fieldbackground=colors["panel"], foreground=colors["text"])
    style.configure("TCombobox", fieldbackground=colors["panel"], foreground=colors["text"])
    style.map("TCombobox", fieldbackground=[("readonly", colors["panel"])])

    style.configure("TNotebook", background=colors["bg"], tabmargins=(8, 4, 8, 0))
    style.configure("TNotebook.Tab", padding=(14, 8), background=colors["panel"], foreground=colors["text"])
    style.map(
        "TNotebook.Tab",
        background=[("selected", colors["accent"])],
        foreground=[("selected", colors["panel"])],
    )

    style.configure("TLabelframe", background=colors["bg"], foreground=colors["text"], bordercolor=colors["border"])
    style.configure("TLabelframe.Label", background=colors["bg"], foreground=colors["text"], font=("Segoe UI Semibold", 10))

    style.configure("Horizontal.TProgressbar", background=colors["accent"], troughcolor=colors["panel"])

    root.configure(background=colors["bg"])
    return colors
