"""Subtitle Styling and Word-Level Animated Highlights Service (Karaoke / Shorts / Reels).

Generates Advanced SubStation Alpha (.ass) subtitle files with word-level highlight
animations and provides stylish design templates for modern social video formats.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class WordTiming:
    word: str
    start: float
    end: float

    def duration_cs(self) -> int:
        """Duration in centiseconds (1/100 sec) for ASS karaoke tags."""
        return max(1, round((self.end - self.start) * 100))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StyledSubtitleLine:
    start: float
    end: float
    text: str
    speaker: str = ""
    words: list[WordTiming] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "start": self.start,
            "end": self.end,
            "text": self.text,
            "speaker": self.speaker,
            "words": [w.to_dict() for w in self.words],
        }


STYLE_PRESETS: dict[str, dict[str, Any]] = {
    "tiktok_pop": {
        "name": "TikTok Pop",
        "font_name": "Arial Black",
        "font_size": 42,
        # ASS color is &HAABBGGRR
        "primary_color": "&H00FFFFFF",  # White
        "secondary_color": "&H0000D7FF",  # Gold / Yellow
        "highlight_color": "&H0000E6FF",  # Bright Yellow
        "outline_color": "&H00000000",  # Black
        "back_color": "&H80000000",  # 50% Black Shadow
        "bold": 1,
        "italic": 0,
        "outline": 4,
        "shadow": 3,
        "alignment": 2,  # Bottom Center (2) or Middle Center (5)
        "margin_v": 110,
        "uppercase": True,
    },
    "reels_modern": {
        "name": "Reels Modern",
        "font_name": "Helvetica Neue",
        "font_size": 36,
        "primary_color": "&H00FFFFFF",  # Pure White
        "secondary_color": "&H00F0FF00",  # Cyan highlight
        "highlight_color": "&H00FFF000",  # Vivid Cyan
        "outline_color": "&H001A1A1A",  # Dark Charcoal
        "back_color": "&H99000000",  # Soft Translucent Box
        "bold": 1,
        "italic": 0,
        "outline": 2,
        "shadow": 0,
        "alignment": 2,
        "margin_v": 90,
        "uppercase": False,
    },
    "karaoke_classic": {
        "name": "Karaoke Classic",
        "font_name": "Arial",
        "font_size": 38,
        "primary_color": "&H00E0E0E0",  # Silver inactive
        "secondary_color": "&H0000BFFF",  # Deep Gold active
        "highlight_color": "&H0000BFFF",
        "outline_color": "&H00000000",
        "back_color": "&H00000000",
        "bold": 1,
        "italic": 0,
        "outline": 3,
        "shadow": 2,
        "alignment": 2,
        "margin_v": 80,
        "uppercase": False,
    },
    "neon_glow": {
        "name": "Neon Glow",
        "font_name": "Impact",
        "font_size": 44,
        "primary_color": "&H00FFFFFF",
        "secondary_color": "&H0014FF39",  # Neon Green
        "highlight_color": "&H0014FF39",  # Neon Green
        "outline_color": "&H00660066",  # Dark Purple
        "back_color": "&H00330033",
        "bold": 1,
        "italic": 0,
        "outline": 4,
        "shadow": 4,
        "alignment": 2,
        "margin_v": 100,
        "uppercase": True,
    },
}


class SubtitleStyleService:
    """Provides word-level timing interpolation, ASS script generation, and burn-in filters."""

    @staticmethod
    def interpolate_word_timings(text: str, start: float, end: float) -> list[WordTiming]:
        """Interpolate timing for each word within a segment duration."""
        words = [w.strip() for w in re.split(r"\s+", text.strip()) if w.strip()]
        if not words:
            return []

        total_dur = max(0.2, end - start)
        # Weight by length of word with slight bonus for punctuation
        weights = [len(w) + (2 if w[-1] in ".,!?;:" else 0) for w in words]
        total_weight = sum(weights) or len(words)

        timings: list[WordTiming] = []
        current_time = start
        for w, weight in zip(words, weights, strict=False):
            w_dur = round((weight / total_weight) * total_dur, 3)
            w_start = round(current_time, 3)
            w_end = round(min(end, current_time + w_dur), 3)
            timings.append(WordTiming(word=w, start=w_start, end=w_end))
            current_time += w_dur

        return timings

    @staticmethod
    def format_ass_time(sec: float) -> str:
        """Format seconds into ASS timestamp format: H:MM:SS.cs"""
        h, rem = divmod(max(0.0, sec), 3600)
        m, s = divmod(rem, 60)
        cs = round((s % 1.0) * 100)
        if cs >= 100:
            s += 1
            cs = 0
        return f"{int(h)}:{int(m):02d}:{int(s):02d}.{cs:02d}"

    def build_ass_script(
        self,
        lines: list[StyledSubtitleLine],
        template_name: str = "tiktok_pop",
        res_x: int = 1080,
        res_y: int = 1920,
    ) -> str:
        """Generate a complete, standard-compliant ASS subtitle script."""
        tmpl = STYLE_PRESETS.get(template_name, STYLE_PRESETS["tiktok_pop"])

        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {res_x}
PlayResY: {res_y}
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{tmpl["font_name"]},{tmpl["font_size"]},{tmpl["primary_color"]},{tmpl["secondary_color"]},{tmpl["outline_color"]},{tmpl["back_color"]},{tmpl["bold"]},{tmpl["italic"]},0,0,100,100,0,0,1,{tmpl["outline"]},{tmpl["shadow"]},{tmpl["alignment"]},30,30,{tmpl["margin_v"]},1
Style: Highlight,{tmpl["font_name"]},{tmpl["font_size"]},{tmpl["highlight_color"]},{tmpl["secondary_color"]},{tmpl["outline_color"]},{tmpl["back_color"]},{tmpl["bold"]},{tmpl["italic"]},0,0,108,108,0,0,1,{tmpl["outline"] + 1},{tmpl["shadow"]}, {tmpl["alignment"]},30,30,{tmpl["margin_v"]},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        dialogue_rows: list[str] = []
        is_karaoke = template_name == "karaoke_classic"
        highlight_color = tmpl.get("highlight_color", "&H0000E6FF")
        primary_color = tmpl.get("primary_color", "&H00FFFFFF")

        for line in lines:
            if not line.words:
                line.words = self.interpolate_word_timings(line.text, line.start, line.end)

            line_speaker = line.speaker.strip()
            speaker_prefix = f"[{line_speaker}] " if line_speaker else ""

            if is_karaoke:
                # Classic Karaoke using {\k<centiseconds>}
                k_parts: list[str] = []
                for w in line.words:
                    word_str = w.word.upper() if tmpl["uppercase"] else w.word
                    k_parts.append(f"{{\\k{w.duration_cs()}}}{word_str}")
                text_content = speaker_prefix + " ".join(k_parts)
                dialogue_rows.append(
                    f"Dialogue: 0,{self.format_ass_time(line.start)},{self.format_ass_time(line.end)},Default,{line_speaker},0,0,0,,{text_content}"
                )
            else:
                # Word-level Pop Highlight: generate an event for each active word
                for active_idx, active_word in enumerate(line.words):
                    parts: list[str] = []
                    for i, w in enumerate(line.words):
                        word_str = w.word.upper() if tmpl["uppercase"] else w.word
                        if i == active_idx:
                            # Highlight active word with color override and subtle scale pop
                            parts.append(f"{{\\c{highlight_color}\\fscx108\\fscy108}}{word_str}{{\\c{primary_color}\\fscx100\\fscy100}}")
                        else:
                            parts.append(word_str)
                    text_content = speaker_prefix + " ".join(parts)
                    dialogue_rows.append(
                        f"Dialogue: 0,{self.format_ass_time(active_word.start)},{self.format_ass_time(active_word.end)},Default,{line_speaker},0,0,0,,{text_content}"
                    )

        return header + "\n".join(dialogue_rows) + "\n"

    def export_ass_file(
        self,
        lines: list[StyledSubtitleLine],
        output_path: Path | str,
        template_name: str = "tiktok_pop",
        res_x: int = 1080,
        res_y: int = 1920,
    ) -> Path:
        """Write ASS script to disk."""
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        script = self.build_ass_script(lines, template_name, res_x, res_y)
        out.write_text(script, encoding="utf-8")
        return out

    def build_burnin_filter(self, ass_path: Path | str) -> str:
        """Create escaped FFmpeg video filter for burning the ASS subtitle."""
        p = str(Path(ass_path).resolve())
        # Escape colons and backslashes for FFmpeg filter syntax
        escaped = p.replace("\\", "/").replace(":", "\\:")
        return f"ass='{escaped}'"
