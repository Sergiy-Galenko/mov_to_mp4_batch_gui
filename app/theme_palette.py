"""Shared color tokens for QML, widget dialogs, and user theme files."""

import re

COLOR_GROUPS = {
    "surfaces": ["windowBackground", "sidebarBackground", "panelBackground", "panelSecondary", "input", "inputHover", "panelHover", "subtleFill", "disabledBg"],
    "text": ["textPrimary", "textSecondary", "textDisabled", "textOnAccent", "textOnMedia"],
    "borders": ["borderDefault", "borderMuted", "focusRing"],
    "actions": ["accent", "accentHover", "accentPressed", "accentSoft", "selectionBackground", "overlayHover", "overlayPressed", "progressTrack", "progressHighlight", "modalScrim"],
    "status": ["statusSuccess", "statusWarning", "statusError", "statusRunning", "successSoft", "warningSoft", "dangerSoft"],
    "media": ["mediaImage", "mediaVideo", "mediaAudio", "mediaSubtitle", "mediaFile", "mediaOverlay"],
}
COLOR_KEYS = frozenset(key for keys in COLOR_GROUPS.values() for key in keys)
THEME_MODES = ("dark", "light", "obsidian", "oled", "midnight", "high_contrast", "auto")

DARK_BASE = {
    "windowBackground": "#111318", "sidebarBackground": "#151820",
    "panelBackground": "#1B1E27", "panelSecondary": "#242834",
    "input": "#141720", "borderDefault": "#404757", "borderMuted": "#303644",
    "textPrimary": "#F2F4F8", "textSecondary": "#B7BECF", "textDisabled": "#8C95A8",
    "accent": "#7C9AFF", "statusSuccess": "#63D6A3", "statusWarning": "#F1C76B", "statusError": "#FF8296",
    "mediaImage": "#63D6A3", "mediaVideo": "#B5A0FF", "mediaAudio": "#F1C76B", "mediaSubtitle": "#6ED6E2",
    "mediaOverlay": "#141720", "textOnMedia": "#FFFFFF", "modalScrim": "#99000000",
}
PRESET_BASES = {
    "dark": DARK_BASE,
    "light": {
        **DARK_BASE,
        "windowBackground": "#F3F5FA", "sidebarBackground": "#FFFFFF", "panelBackground": "#FFFFFF",
        "panelSecondary": "#E9EDF5", "input": "#FFFFFF", "borderDefault": "#A9B3C5", "borderMuted": "#D2D8E4",
        "textPrimary": "#182033", "textSecondary": "#46536B", "textDisabled": "#64718A", "accent": "#3759DD",
        "statusSuccess": "#147D50", "statusWarning": "#906100", "statusError": "#C33350",
        "mediaImage": "#147D50", "mediaVideo": "#7541BB", "mediaAudio": "#906100", "mediaSubtitle": "#097887",
        "modalScrim": "#66000000",
    },
    "obsidian": {
        **DARK_BASE, "windowBackground": "#0D1117", "sidebarBackground": "#10151D",
        "panelBackground": "#161B22", "panelSecondary": "#21262D", "input": "#0D1117",
        "borderDefault": "#484F58", "borderMuted": "#30363D", "accent": "#79B8FF",
    },
    "oled": {
        **DARK_BASE, "windowBackground": "#000000", "sidebarBackground": "#000000",
        "panelBackground": "#080808", "panelSecondary": "#151515", "input": "#000000",
        "borderDefault": "#484848", "borderMuted": "#282828",
    },
    "midnight": {
        **DARK_BASE, "windowBackground": "#0B1020", "sidebarBackground": "#10172D",
        "panelBackground": "#151F38", "panelSecondary": "#202D4B", "input": "#0E172C",
        "borderDefault": "#46577D", "borderMuted": "#2F3D5E", "accent": "#A6AEFF",
    },
    "high_contrast": {
        **DARK_BASE, "windowBackground": "#000000", "sidebarBackground": "#000000",
        "panelBackground": "#000000", "panelSecondary": "#101010", "input": "#000000",
        "borderDefault": "#FFFFFF", "borderMuted": "#B0B0B0", "textPrimary": "#FFFFFF",
        "textSecondary": "#FFFFFF", "textDisabled": "#CCCCCC", "accent": "#FFFF00",
        "statusSuccess": "#00FF88", "statusWarning": "#FFFF00", "statusError": "#FF8888",
    },
}


def normalize_color(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", value.strip()):
        raise ValueError("Use #RGB, #RRGGBB or #AARRGGBB")
    value = value.strip().upper()
    return "#" + "".join(char * 2 for char in value[1:]) if len(value) == 4 else value


def mix(first: str, second: str, weight: float) -> str:
    first, second = first[-6:], second[-6:]
    return "#" + "".join(f"{round(int(first[i:i+2], 16) * (1 - weight) + int(second[i:i+2], 16) * weight):02X}" for i in (0, 2, 4))


def luminance(color: str) -> float:
    channels = [int(color[-6:][i:i+2], 16) / 255 for i in (0, 2, 4)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))


def contrast_ratio(first: str, second: str) -> float:
    values = sorted((luminance(first), luminance(second)))
    return (values[1] + 0.05) / (values[0] + 0.05)


def resolve_palette(mode: str = "dark", overrides: dict[str, str] | None = None) -> dict[str, str]:
    custom = overrides or {}
    base = {**PRESET_BASES.get(mode, DARK_BASE), **custom}
    panel, accent, text = base["panelBackground"], base["accent"], base["textPrimary"]
    soft = mix(panel, accent, 0.18)
    derived = {
        "accentHover": mix(accent, text, 0.16), "accentPressed": mix(accent, panel, 0.18),
        "textOnAccent": "#101218" if contrast_ratio(accent, "#101218") >= contrast_ratio(accent, "#FFFFFF") else "#FFFFFF",
        "inputHover": mix(base["input"], text, 0.05), "panelHover": mix(panel, text, 0.06),
        "subtleFill": mix(panel, text, 0.025), "disabledBg": base["panelSecondary"],
        "accentSoft": soft, "selectionBackground": soft, "focusRing": accent,
        "overlayHover": mix(panel, text, 0.06), "overlayPressed": mix(panel, text, 0.11),
        "progressTrack": base["borderMuted"], "progressHighlight": accent,
        "statusRunning": accent, "mediaFile": base["textSecondary"],
        "successSoft": mix(panel, base["statusSuccess"], 0.16),
        "warningSoft": mix(panel, base["statusWarning"], 0.16),
        "dangerSoft": mix(panel, base["statusError"], 0.16),
    }
    return {**base, **derived, **custom}
