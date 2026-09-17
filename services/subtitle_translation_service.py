"""Subtitle Translation Service with Timestamp Preservation.

Provides:
- Translation of subtitle segments across multiple target languages.
- Strict preservation of start/end timestamps, speaker tags, and line order.
- Free web translation API client with offline dictionary fallback for air-gapped environments.
- Exporting individual language subtitle files (*.uk.srt, *.en.srt, *.pl.srt, etc.).
- Multi-track subtitle packaging for MP4 / MKV containers via FFmpeg.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES: dict[str, str] = {
    "uk": "Українська",
    "en": "English",
    "pl": "Polski",
    "de": "Deutsch",
    "es": "Español",
    "fr": "Français",
    "it": "Italiano",
    "ja": "日本語",
    "zh": "中文",
}


@dataclass
class TranslatedSubtitleSegment:
    start: float
    end: float
    original_text: str
    translated_text: str
    language: str
    speaker: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TranslatedSubtitleSegment:
        valid = cls.__dataclass_fields__.keys()
        return cls(**{k: v for k, v in data.items() if k in valid})


@dataclass
class MultiLanguageSubtitles:
    source_language: str
    translations: dict[str, list[TranslatedSubtitleSegment]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_language": self.source_language,
            "translations": {
                lang: [s.to_dict() for s in segs]
                for lang, segs in self.translations.items()
            },
        }


class SubtitleTranslationService:
    """Service providing multi-language subtitle translation while preserving timecodes."""

    def __init__(self, ffmpeg_path: str = "ffmpeg") -> None:
        self.ffmpeg_path = ffmpeg_path or "ffmpeg"

    def translate_text(self, text: str, source_lang: str = "auto", target_lang: str = "en") -> str:
        """Translate a single line or text chunk using web API with graceful offline fallback."""
        cleaned = text.strip()
        if not cleaned:
            return ""

        # Extract leading speaker tag if present (e.g., "[Мовець 1]")
        speaker_prefix = ""
        m = re.match(r"^(\[[^\]]+\]|\<v [^\>]+\>)\s*(.*)$", cleaned)
        if m:
            speaker_prefix = m.group(1) + " "
            cleaned = m.group(2).strip()

        if not cleaned:
            return speaker_prefix.strip()

        # 1. Attempt free translation endpoint
        try:
            params = {
                "client": "gtx",
                "sl": source_lang if source_lang != "auto" else "auto",
                "tl": target_lang,
                "dt": "t",
                "q": cleaned,
            }
            url = f"https://translate.googleapis.com/translate_a/single?{urllib.parse.urlencode(params)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    raw_data = response.read().decode("utf-8")
                    parsed = json.loads(raw_data)
                    if parsed and isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], list):
                        translated_pieces = [piece[0] for piece in parsed[0] if piece and isinstance(piece, list) and len(piece) > 0 and piece[0]]
                        translated = "".join(translated_pieces).strip()
                        if translated:
                            return f"{speaker_prefix}{translated}".strip()
        except Exception as exc:
            logger.debug("Web translation failed: %s; using local dictionary fallback", exc)

        # 2. Offline fallback: common phrase and term dictionary
        offline_dict: dict[tuple[str, str], dict[str, str]] = {
            ("uk", "en"): {
                "привіт": "Hello",
                "дякую": "Thank you",
                "будь ласка": "Please",
                "так": "Yes",
                "ні": "No",
                "відео": "Video",
                "редактор": "Editor",
                "монтаж": "Montage",
            },
            ("en", "uk"): {
                "hello": "Привіт",
                "thank you": "Дякую",
                "please": "Будь ласка",
                "yes": "Так",
                "no": "Ні",
                "video": "Відео",
            },
        }

        dict_key = (source_lang.lower(), target_lang.lower())
        lookup = offline_dict.get(dict_key, {})
        lower = cleaned.lower()
        if lower in lookup:
            return f"{speaker_prefix}{lookup[lower]}".strip()

        # If completely offline and untranslatable, keep original text
        return f"{speaker_prefix}{cleaned}".strip()

    def translate_segments(
        self,
        segments: list[dict[str, Any]],
        target_languages: list[str],
        source_language: str = "auto",
    ) -> MultiLanguageSubtitles:
        """Translate a batch of subtitle segments into multiple target languages."""
        results: dict[str, list[TranslatedSubtitleSegment]] = {}

        for target_lang in target_languages:
            lang_code = target_lang.lower().strip()
            if lang_code not in SUPPORTED_LANGUAGES and len(lang_code) != 2:
                continue

            trans_list: list[TranslatedSubtitleSegment] = []
            for seg in segments:
                st = float(seg.get("start", 0.0) or 0.0)
                et = float(seg.get("end", st + 1.0) or (st + 1.0))
                orig_txt = str(seg.get("text", "")).strip()
                spk = str(seg.get("speaker", "") or seg.get("speaker_name", "")).strip()

                if source_language == lang_code:
                    translated = orig_txt
                else:
                    translated = self.translate_text(orig_txt, source_lang=source_language, target_lang=lang_code)

                trans_list.append(
                    TranslatedSubtitleSegment(
                        start=st,
                        end=et,
                        original_text=orig_txt,
                        translated_text=translated,
                        language=lang_code,
                        speaker=spk,
                    )
                )
            results[lang_code] = trans_list

        return MultiLanguageSubtitles(
            source_language=source_language,
            translations=results,
        )

    def export_language_srt(
        self,
        segments: list[TranslatedSubtitleSegment],
        output_path: Path | str,
        include_speaker: bool = False,
    ) -> Path:
        """Export translated segments to an SRT file."""
        lines: list[str] = []
        for idx, seg in enumerate(segments, start=1):
            s_h, s_rem = divmod(seg.start, 3600)
            s_m, s_s = divmod(s_rem, 60)
            e_h, e_rem = divmod(seg.end, 3600)
            e_m, e_s = divmod(e_rem, 60)
            t_start = f"{int(s_h):02d}:{int(s_m):02d}:{int(s_s):02d},{int((s_s % 1) * 1000):03d}"
            t_end = f"{int(e_h):02d}:{int(e_m):02d}:{int(e_s):02d},{int((e_s % 1) * 1000):03d}"

            lines.append(str(idx))
            lines.append(f"{t_start} --> {t_end}")
            txt = f"[{seg.speaker}] {seg.translated_text}" if (include_speaker and seg.speaker) else seg.translated_text
            lines.append(txt)
            lines.append("")

        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(lines), encoding="utf-8")
        return out

    def build_multitrack_embed_command(
        self,
        video_path: Path | str,
        subtitle_files: dict[str, Path | str],
        output_path: Path | str,
    ) -> list[str]:
        """Build FFmpeg command to multiplex multiple translated subtitle files as distinct subtitle streams."""
        cmd = [self.ffmpeg_path, "-y", "-i", str(Path(video_path).resolve())]

        sub_inputs = list(subtitle_files.items())
        for _, sub_path in sub_inputs:
            cmd.extend(["-i", str(Path(sub_path).resolve())])

        cmd.extend(["-map", "0:v", "-map", "0:a?"])

        for i in range(len(sub_inputs)):
            cmd.extend(["-map", f"{i + 1}:s"])

        cmd.extend(["-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text" if str(output_path).endswith(".mp4") else "srt"])

        for i, (lang_code, _) in enumerate(sub_inputs):
            # ISO 639-2 language tag mapping
            iso_map = {"uk": "ukr", "en": "eng", "pl": "pol", "de": "deu", "es": "spa", "fr": "fra"}
            tag = iso_map.get(lang_code, lang_code)
            lang_title = SUPPORTED_LANGUAGES.get(lang_code, lang_code.upper())
            cmd.extend([
                f"-metadata:s:s:{i}", f"language={tag}",
                f"-metadata:s:s:{i}", f"title={lang_title}",
            ])

        cmd.append(str(Path(output_path).resolve()))
        return cmd

