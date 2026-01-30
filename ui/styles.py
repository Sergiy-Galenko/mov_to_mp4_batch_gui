# -*- coding: utf-8 -*-
import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional

SPACE_1 = 8
SPACE_2 = 16
SPACE_3 = 24
SPACE_4 = 32

THEMES: Dict[str, Dict[str, str]] = {
    "light": {
        "bg": "#F9FAFB",
        "panel": "#FFFFFF",
        "text": "#111827",
        "muted": "#6B7280",
        "accent": "#2563EB",
        "accent_alt": "#1D4ED8",
        "border": "#E5E7EB",
        "success": "#0F766E",
        "warn": "#B45309",
        "error": "#B91C1C",
    },
    "dark": {
        "bg": "#0F172A",
        "panel": "#111827",
        "text": "#F8FAFC",
        "muted": "#94A3B8",
        "accent": "#3B82F6",
        "accent_alt": "#2563EB",
        "border": "#1F2937",
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

    base_family = "Segoe UI"
    base_font = (base_family, 11)
    title_font = (base_family, 16, "bold")
    subtitle_font = (base_family, 10)
    label_font = (base_family, 11, "bold")
    style.configure("TFrame", background=colors["bg"])
    style.configure("Panel.TFrame", background=colors["panel"])
    style.configure("Card.TFrame", background=colors["panel"], borderwidth=1, relief="solid")
    style.configure("TLabel", background=colors["panel"], foreground=colors["text"], font=base_font)
    style.configure("Muted.TLabel", background=colors["panel"], foreground=colors["muted"], font=base_font)
    style.configure("Title.TLabel", background=colors["panel"], foreground=colors["text"], font=title_font)
    style.configure("Subtitle.TLabel", background=colors["panel"], foreground=colors["muted"], font=subtitle_font)

    style.configure(
        "TButton",
        background=colors["accent"],
        foreground=colors["panel"],
        padding=(SPACE_2, SPACE_1),
        borderwidth=0,
        relief="flat",
    )
    style.map(
        "TButton",
        background=[("active", colors["accent_alt"]), ("disabled", colors["border"])],
        foreground=[("active", colors["panel"]), ("disabled", colors["muted"])],
    )
    style.configure(
        "Secondary.TButton",
        background=colors["panel"],
        foreground=colors["text"],
        padding=(SPACE_2, SPACE_1),
        borderwidth=1,
        relief="solid",
        bordercolor=colors["border"],
    )
    style.map(
        "Secondary.TButton",
        background=[("active", colors["bg"]), ("disabled", colors["bg"])],
        foreground=[("active", colors["text"]), ("disabled", colors["muted"])],
    )
    style.configure(
        "Ghost.TButton",
        background=colors["bg"],
        foreground=colors["accent"],
        padding=(SPACE_2, SPACE_1),
        borderwidth=0,
        relief="flat",
    )
    style.map(
        "Ghost.TButton",
        background=[("active", colors["panel"]), ("disabled", colors["bg"])],
        foreground=[("active", colors["accent_alt"]), ("disabled", colors["muted"])],
    )

    style.configure(
        "TEntry",
        fieldbackground=colors["panel"],
        foreground=colors["text"],
        padding=(SPACE_1, SPACE_1),
        bordercolor=colors["border"],
    )
    style.configure(
        "TSpinbox",
        fieldbackground=colors["panel"],
        foreground=colors["text"],
        padding=(SPACE_1, SPACE_1),
        bordercolor=colors["border"],
    )
    style.configure(
        "TCombobox",
        fieldbackground=colors["panel"],
        foreground=colors["text"],
        padding=(SPACE_1, SPACE_1),
        bordercolor=colors["border"],
    )
    style.map("TCombobox", fieldbackground=[("readonly", colors["panel"])], bordercolor=[("focus", colors["accent"])])
    style.map(
        "TEntry",
        fieldbackground=[("disabled", colors["bg"])],
        foreground=[("disabled", colors["muted"])],
    )
    style.map("TEntry", bordercolor=[("focus", colors["accent"])])
    style.map("TSpinbox", bordercolor=[("focus", colors["accent"])])
    style.configure("TCheckbutton", background=colors["panel"], foreground=colors["text"], padding=(SPACE_1, SPACE_1))
    style.map("TCheckbutton", foreground=[("disabled", colors["muted"])])

    style.configure("TNotebook", background=colors["panel"], tabmargins=(SPACE_2, SPACE_1, SPACE_2, 0))
    style.configure("TNotebook.Tab", padding=(SPACE_2, SPACE_1), background=colors["panel"], foreground=colors["text"])
    style.map(
        "TNotebook.Tab",
        background=[("selected", colors["accent"])],
        foreground=[("selected", colors["panel"])],
    )

    style.configure("TLabelframe", background=colors["panel"], foreground=colors["text"], bordercolor=colors["border"], borderwidth=1, relief="solid")
    style.configure("TLabelframe.Label", background=colors["panel"], foreground=colors["text"], font=label_font)

    style.configure("Horizontal.TProgressbar", background=colors["accent"], troughcolor=colors["panel"])

    root.configure(background=colors["bg"])
    return colors
