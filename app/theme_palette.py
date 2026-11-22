"""Shared color tokens for QML, widget dialogs, and user theme files."""

import re
import sys

COLOR_GROUPS = {
    "surfaces": [
        "windowBackground",
        "sidebarBackground",
        "panelBackground",
        "panelSecondary",
        "input",
        "inputHover",
        "panelHover",
        "subtleFill",
        "disabledBg",
    ],
    "text": ["textPrimary", "textSecondary", "textDisabled", "textOnAccent", "textOnMedia"],
    "borders": ["borderDefault", "borderMuted", "focusRing"],
    "actions": [
        "accent",
        "accentHover",
        "accentPressed",
        "accentSoft",
        "selectionBackground",
        "overlayHover",
        "overlayPressed",
        "progressTrack",
        "progressHighlight",
        "modalScrim",
    ],
    "status": ["statusSuccess", "statusWarning", "statusError", "statusRunning", "successSoft", "warningSoft", "dangerSoft"],
    "media": ["mediaImage", "mediaVideo", "mediaAudio", "mediaSubtitle", "mediaFile", "mediaOverlay"],
}
COLOR_KEYS = frozenset(key for keys in COLOR_GROUPS.values() for key in keys)
THEME_MODES = ("dark", "light", "obsidian", "oled", "midnight", "high_contrast", "auto")

DARK_BASE = {
    "windowBackground": "#0C0C0C",
    "sidebarBackground": "#111111",
    "panelBackground": "#181818",
    "panelSecondary": "#242424",
    "input": "#101010",
    "borderDefault": "#505050",
    "borderMuted": "#333333",
    "textPrimary": "#F5F5F5",
    "textSecondary": "#BDBDBD",
    "textDisabled": "#929292",
    "accent": "#EEEEEE",
    "statusSuccess": "#E0E0E0",
    "statusWarning": "#C4C4C4",
    "statusError": "#FFFFFF",
    "mediaImage": "#D6D6D6",
    "mediaVideo": "#E8E8E8",
    "mediaAudio": "#BDBDBD",
    "mediaSubtitle": "#CCCCCC",
    "mediaOverlay": "#101010",
    "textOnMedia": "#FFFFFF",
    "modalScrim": "#AA000000",
}

PRESET_BASES = {
    "dark": DARK_BASE,
    "light": {
        **DARK_BASE,
        "windowBackground": "#F3F5FA",
        "sidebarBackground": "#FFFFFF",
        "panelBackground": "#FFFFFF",
        "panelSecondary": "#E9EDF5",
        "input": "#FFFFFF",
        "borderDefault": "#A9B3C5",
        "borderMuted": "#D2D8E4",
        "textPrimary": "#182033",
        "textSecondary": "#46536B",
        "textDisabled": "#64718A",
        "accent": "#3759DD",
        "statusSuccess": "#147D50",
        "statusWarning": "#906100",
        "statusError": "#C33350",
        "mediaImage": "#147D50",
        "mediaVideo": "#7541BB",
        "mediaAudio": "#906100",
        "mediaSubtitle": "#097887",
        "modalScrim": "#66000000",
    },
    "obsidian": {
        **DARK_BASE,
        "windowBackground": "#0D1117",
        "sidebarBackground": "#10151D",
        "panelBackground": "#161B22",
        "panelSecondary": "#21262D",
        "input": "#0D1117",
        "borderDefault": "#484F58",
        "borderMuted": "#30363D",
        "accent": "#79B8FF",
    },
    "oled": {
        **DARK_BASE,
        "windowBackground": "#000000",
        "sidebarBackground": "#000000",
        "panelBackground": "#080808",
        "panelSecondary": "#151515",
        "input": "#000000",
        "borderDefault": "#484848",
        "borderMuted": "#282828",
    },
    "midnight": {
        **DARK_BASE,
        "windowBackground": "#0B1020",
        "sidebarBackground": "#10172D",
        "panelBackground": "#151F38",
        "panelSecondary": "#202D4B",
        "input": "#0E172C",
        "borderDefault": "#46577D",
        "borderMuted": "#2F3D5E",
        "accent": "#A6AEFF",
    },
    "high_contrast": {
        **DARK_BASE,
        "windowBackground": "#000000",
        "sidebarBackground": "#000000",
        "panelBackground": "#000000",
        "panelSecondary": "#101010",
        "input": "#000000",
        "borderDefault": "#FFFFFF",
        "borderMuted": "#B0B0B0",
        "textPrimary": "#FFFFFF",
        "textSecondary": "#FFFFFF",
        "textDisabled": "#CCCCCC",
        "accent": "#FFFF00",
        "statusSuccess": "#00FF88",
        "statusWarning": "#FFFF00",
        "statusError": "#FF8888",
    },
}


# System Settings surfaces on macOS; Fluent-style surfaces on Windows.
PLATFORM_BASES = {
    "macos": {
        "dark": {
            "windowBackground": "#282827",
            "sidebarBackground": "#2D2C2B",
            "panelBackground": "#323231",
            "panelSecondary": "#464645",
            "input": "#3C3C3B",
            "borderDefault": "#686867",
            "borderMuted": "#414140",
            "textPrimary": "#F2F2F2",
            "textSecondary": "#B8B8B7",
            "textDisabled": "#959594",
            "accent": "#0070EA",
            "statusSuccess": "#32D74B",
            "statusWarning": "#FFD60A",
            "statusError": "#FF6961",
            "mediaImage": "#30D158",
            "mediaVideo": "#BF5AF2",
            "mediaAudio": "#FF9F0A",
            "mediaSubtitle": "#64D2FF",
        },
        "light": {
            "windowBackground": "#F5F5F5",
            "sidebarBackground": "#E9E8E7",
            "panelBackground": "#FFFFFF",
            "panelSecondary": "#E4E4E4",
            "input": "#FFFFFF",
            "borderDefault": "#B7B7B7",
            "borderMuted": "#DEDEDE",
            "textPrimary": "#232323",
            "textSecondary": "#626262",
            "textDisabled": "#777777",
            "accent": "#0069D9",
            "statusSuccess": "#22863A",
            "statusWarning": "#926000",
            "statusError": "#C42B27",
        },
    },
    "windows": {
        "dark": {
            "windowBackground": "#202020",
            "sidebarBackground": "#202020",
            "panelBackground": "#2B2B2B",
            "panelSecondary": "#373737",
            "input": "#323232",
            "borderDefault": "#6B6B6B",
            "borderMuted": "#404040",
            "textPrimary": "#F5F5F5",
            "textSecondary": "#C4C4C4",
            "textDisabled": "#A0A0A0",
            "accent": "#60CDFF",
            "statusSuccess": "#6CCB5F",
            "statusWarning": "#FCE100",
            "statusError": "#FF99A4",
            "mediaImage": "#6CCB5F",
            "mediaVideo": "#C7A0FF",
            "mediaAudio": "#FFB75E",
            "mediaSubtitle": "#60CDFF",
        },
        "light": {
            "windowBackground": "#F3F3F3",
            "sidebarBackground": "#F3F3F3",
            "panelBackground": "#FFFFFF",
            "panelSecondary": "#F9F9F9",
            "input": "#FFFFFF",
            "borderDefault": "#A0A0A0",
            "borderMuted": "#E0E0E0",
            "textPrimary": "#1A1A1A",
            "textSecondary": "#5D5D5D",
            "textDisabled": "#737373",
            "accent": "#0067C0",
        },
    },
}


def detect_platform(platform_name: str | None = None) -> str:
    name = platform_name or sys.platform
    if name in {"darwin", "osx", "macos"}:
        return "macos"
    if name in {"win32", "windows"}:
        return "windows"
    return "linux"


def normalize_color(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", value.strip()):
        raise ValueError("Use #RGB, #RRGGBB or #AARRGGBB")
    value = value.strip().upper()
    return "#" + "".join(char * 2 for char in value[1:]) if len(value) == 4 else value


def mix(first: str, second: str, weight: float) -> str:
    first, second = first[-6:], second[-6:]
    return "#" + "".join(f"{round(int(first[i : i + 2], 16) * (1 - weight) + int(second[i : i + 2], 16) * weight):02X}" for i in (0, 2, 4))


def luminance(color: str) -> float:
    channels = [int(color[-6:][i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))


def contrast_ratio(first: str, second: str) -> float:
    values = sorted((luminance(first), luminance(second)))
    return (values[1] + 0.05) / (values[0] + 0.05)


def resolve_palette(mode: str = "dark", overrides: dict[str, str] | None = None, platform_name: str | None = None) -> dict[str, str]:
    custom = overrides or {}
    platform = detect_platform(platform_name)
    platform_base = PLATFORM_BASES.get(platform, PLATFORM_BASES["windows"]).get(mode, {})
    base = {**PRESET_BASES.get(mode, DARK_BASE), **platform_base, **custom}
    panel, accent, text = base["panelBackground"], base["accent"], base["textPrimary"]
    soft = mix(panel, accent, 0.18)
    derived = {
        "accentHover": mix(accent, text, 0.16),
        "accentPressed": mix(accent, panel, 0.18),
        "textOnAccent": "#111111" if contrast_ratio(accent, "#111111") >= contrast_ratio(accent, "#FFFFFF") else "#FFFFFF",
        "inputHover": mix(base["input"], text, 0.05),
        "panelHover": mix(panel, text, 0.06),
        "subtleFill": mix(panel, text, 0.025),
        "disabledBg": base["panelSecondary"],
        "accentSoft": soft,
        "selectionBackground": soft,
        "focusRing": accent,
        "overlayHover": mix(panel, text, 0.06),
        "overlayPressed": mix(panel, text, 0.11),
        "progressTrack": base["borderMuted"],
        "progressHighlight": accent,
        "statusRunning": accent,
        "mediaFile": base["textSecondary"],
        "successSoft": mix(panel, base["statusSuccess"], 0.16),
        "warningSoft": mix(panel, base["statusWarning"], 0.16),
        "dangerSoft": mix(panel, base["statusError"], 0.16),
    }
    return {**base, **derived, **custom}
