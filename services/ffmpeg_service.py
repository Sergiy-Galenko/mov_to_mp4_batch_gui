import json
import subprocess
import os
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.constants import HW_ENCODER_MAP, OPERATION_MAP, PORTRAIT_PRESETS, POSITION_MAP, VIDEO_CODEC_MAP
from app.models import ConversionSettings, MediaChapter, MediaInfo
from utils.formatting import build_atempo_chain


def escape_drawtext(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def escape_filter_path(path: str) -> str:
    return path.replace("\\", "/").replace(":", "\\:")


def _ass_color(value: str) -> str:
    raw = str(value or "").strip()
    named = {
        "white": "&H00FFFFFF",
        "black": "&H00000000",
        "red": "&H000000FF",
        "green": "&H0000FF00",
        "blue": "&H00FF0000",
        "yellow": "&H0000FFFF",
    }
    if raw.lower() in named:
        return named[raw.lower()]
    if raw.startswith("#") and len(raw) == 7:
        try:
            r = int(raw[1:3], 16)
            g = int(raw[3:5], 16)
            b = int(raw[5:7], 16)
            return f"&H00{b:02X}{g:02X}{r:02X}"
        except ValueError:
            return named["white"]
    return raw or named["white"]


def parse_progress_line(line: str) -> Dict[str, str]:
    text = line.strip()
    if "=" not in text:
        return {}
    key, _, value = text.partition("=")
    key = key.strip()
    if not key:
        return {}
    return {key: value.strip()}


def parse_duration_ms(ffprobe_output: str) -> Optional[float]:
    try:
        data = json.loads(ffprobe_output)
        duration_str = data.get("format", {}).get("duration", "")
        if duration_str and duration_str != "N/A":
            return float(duration_str) * 1000
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return None


def _ratio_to_float(value: Any) -> Optional[float]:
    if value in (None, "", "0/0"):
        return None
    text = str(value)
    if "/" in text:
        num, den = text.split("/", 1)
        try:
            numerator = float(num)
            denominator = float(den)
        except ValueError:
            return None
        if denominator == 0:
            return None
        return numerator / denominator
    try:
        return float(text)
    except ValueError:
        return None


def _guess_dynamic_range(color_transfer: str) -> str:
    transfer = (color_transfer or "").lower()
    if transfer in {"smpte2084", "arib-std-b67"}:
        return "HDR"
    return "SDR"


def _aspect_warning(width: Optional[int], height: Optional[int]) -> Optional[str]:
    if not width or not height:
        return None
    ratio = width / height
    common = [16 / 9, 9 / 16, 4 / 3, 1.0, 21 / 9]
    if min(abs(ratio - known) for known in common) > 0.08:
        return f"Нестандартний aspect ratio: {width}:{height}"
    return None


def _container_supports_codec(ext: str, vcodec: str) -> bool:
    ext = ext.lower()
    vcodec = vcodec.lower()
    if ext in {".mkv"}:
        return True
    if ext in {".mp4", ".m4v", ".mov"}:
        return vcodec in {"h264", "hevc", "h265", "av1"}
    if ext in {".webm"}:
        return vcodec in {"vp8", "vp9", "av1"}
    if ext in {".avi"}:
        return vcodec in {"mpeg4", "h264", "xvid"}
    return True


def _null_output() -> str:
    return "NUL" if os.name == "nt" else "/dev/null"


def _bitrate_to_kbps(value: str, fallback: int = 192) -> int:
    text = str(value or "").strip().lower()
    if not text:
        return fallback
    try:
        if text.endswith("k"):
            return max(1, int(float(text[:-1])))
        if text.endswith("m"):
            return max(1, int(float(text[:-1]) * 1000))
        return max(1, int(float(text) / 1000 if float(text) > 10000 else float(text)))
    except ValueError:
        return fallback


def _normalize_video_codec(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"h264", "avc", "libx264"}:
        return "h264"
    if normalized in {"hevc", "h265", "libx265"}:
        return "h265"
    if "av1" in normalized:
        return "av1"
    if "vp9" in normalized:
        return "vp9"
    if "mpeg2" in normalized:
        return "mpeg2"
    if "prores" in normalized:
        return "prores"
    return normalized


class FfmpegService:
    DETECT_TIMEOUT_SEC = 15
    PROBE_TIMEOUT_SEC = 30

    def __init__(self, ffmpeg_path: Optional[str], ffprobe_path: Optional[str]):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self.encoder_caps: set[str] = set()

    def set_paths(self, ffmpeg_path: Optional[str], ffprobe_path: Optional[str]) -> None:
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def detect_encoders(self) -> set[str]:
        if not self.ffmpeg_path:
            return set()
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                timeout=self.DETECT_TIMEOUT_SEC,
            )
        except Exception:
            return set()
        if result.returncode != 0:
            return set()
        encoders: set[str] = set()
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("Encoders:") or line.startswith("--"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                encoders.add(parts[1])
        return encoders

    def probe_duration_ms(self, path: Path) -> Optional[float]:
        if not self.ffprobe_path:
            return None
        cmd = [
            self.ffprobe_path,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            str(path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.PROBE_TIMEOUT_SEC)
        except Exception:
            return None
        if result.returncode != 0:
            return None
        return parse_duration_ms(result.stdout)

    def probe_media_batch(self, paths: List[Path], max_workers: int = 4) -> Dict[Path, Optional[MediaInfo]]:
        if not paths:
            return {}
        worker_count = max(1, min(max_workers, len(paths)))
        results: Dict[Path, Optional[MediaInfo]] = {}
        with ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="ffprobe-batch") as pool:
            futures = {pool.submit(self.probe_media, path): path for path in paths}
            for future in as_completed(futures):
                path = futures[future]
                try:
                    results[path] = future.result()
                except Exception:
                    results[path] = None
        return results

    def probe_media(self, path: Path) -> Optional[MediaInfo]:
        if not self.ffprobe_path:
            return None
        cmd = [
            self.ffprobe_path,
            "-v",
            "error",
            "-show_entries",
            (
                "format=duration,size,format_name:"
                "stream=index,codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate,"
                "color_space,color_transfer,color_primaries,pix_fmt,display_aspect_ratio:"
                "stream_tags=rotate:stream_side_data=rotation:"
                "chapter=id,start_time,end_time:chapter_tags=title"
            ),
            "-show_chapters",
            "-of",
            "json",
            str(path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.PROBE_TIMEOUT_SEC)
        except Exception:
            return None
        if result.returncode != 0:
            return None
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            return None

        info = MediaInfo()
        fmt = data.get("format", {})
        dur = fmt.get("duration")
        if dur is not None:
            try:
                info.duration = float(dur)
            except ValueError:
                pass
        info.format_name = fmt.get("format_name")
        size = fmt.get("size")
        if size is not None:
            try:
                info.size_bytes = int(size)
            except ValueError:
                pass

        for stream in data.get("streams", []):
            codec_type = stream.get("codec_type")
            if codec_type == "video":
                if info.vcodec is None:
                    info.vcodec = stream.get("codec_name")
                    info.width = stream.get("width")
                    info.height = stream.get("height")
                    info.fps = _ratio_to_float(stream.get("avg_frame_rate")) or _ratio_to_float(stream.get("r_frame_rate"))
                    avg_fps = _ratio_to_float(stream.get("avg_frame_rate"))
                    real_fps = _ratio_to_float(stream.get("r_frame_rate"))
                    if avg_fps and real_fps:
                        info.frame_rate_mode = "VFR" if abs(avg_fps - real_fps) > 0.01 else "CFR"
                    info.color_space = stream.get("color_space")
                    info.color_transfer = stream.get("color_transfer")
                    info.color_primaries = stream.get("color_primaries")
                    info.pix_fmt = stream.get("pix_fmt")
                    info.display_aspect_ratio = stream.get("display_aspect_ratio")
                    info.dynamic_range = _guess_dynamic_range(info.color_transfer or "")

                    rotate = stream.get("tags", {}).get("rotate")
                    if rotate is None:
                        for side_data in stream.get("side_data_list", []):
                            if "rotation" in side_data:
                                rotate = side_data.get("rotation")
                                break
                    if rotate is not None:
                        try:
                            info.rotation = int(float(rotate))
                        except ValueError:
                            info.rotation = None
                continue

            if codec_type == "audio":
                info.audio_streams += 1
                if info.acodec is None:
                    info.acodec = stream.get("codec_name")
                continue

            if codec_type == "subtitle":
                info.subtitle_streams += 1

        for index, chapter in enumerate(data.get("chapters", []), start=1):
            start_value = _ratio_to_float(chapter.get("start_time")) or 0.0
            end_value = _ratio_to_float(chapter.get("end_time")) or 0.0
            if end_value <= start_value:
                continue
            title = str(chapter.get("tags", {}).get("title") or "").strip()
            info.chapters.append(MediaChapter(index=index, start=start_value, end=end_value, title=title))

        if info.width and info.height:
            if info.width % 2 or info.height % 2:
                info.warnings.append("Непарна роздільність може бути проблемною для деяких енкодерів.")
            aspect_warning = _aspect_warning(info.width, info.height)
            if aspect_warning:
                info.warnings.append(aspect_warning)
        if info.rotation not in (None, 0):
            info.warnings.append(f"Відео має rotation={info.rotation}°.")
        if info.dynamic_range == "HDR":
            info.warnings.append("HDR-джерело: перевір тонмапінг для SDR-платформ.")

        if info.size_bytes is None:
            try:
                info.size_bytes = path.stat().st_size
            except Exception:
                pass
        return info

    def output_extension_for(self, media_type_name: str, settings: ConversionSettings) -> str:
        operation = settings.operation
        if media_type_name == "text":
            return settings.out_text_format
        if operation == "audio_only" or media_type_name == "audio":
            return settings.out_audio_format
        if operation in {"subtitle_extract", "auto_subtitle"} or media_type_name == "subtitle":
            return settings.out_subtitle_format
        if operation in {"thumbnail", "contact_sheet"}:
            return settings.out_image_format
        return settings.out_video_format if media_type_name == "video" else settings.out_image_format

    def resolve_codec(self, out_ext: str, codec_choice: str, log_cb=None) -> str:
        choice = VIDEO_CODEC_MAP.get(codec_choice, "auto")
        out_ext = out_ext.lower()
        if out_ext == ".gif":
            return "gif"
        if choice == "auto":
            if out_ext == ".webm":
                return "vp9"
            if out_ext == ".mpg":
                return "mpeg2"
            return "h264"
        if out_ext == ".webm" and choice not in {"vp9", "av1"}:
            if log_cb:
                log_cb("WARN", "WebM підтримує лише VP9/AV1. Перемикаю на VP9.")
            return "vp9"
        if out_ext in {".mp4", ".mov", ".m4v", ".avi"} and choice == "vp9":
            if log_cb:
                log_cb("WARN", "VP9 не сумісний з MP4/MOV/AVI. Перемикаю на H.264.")
            return "h264"
        if out_ext == ".mpg" and choice != "mpeg2":
            if log_cb:
                log_cb("WARN", "MPG профіль використовує MPEG-2.")
            return "mpeg2"
        return choice

    def select_encoder(self, codec: str, hw_pref: str, log_cb=None) -> Tuple[str, bool]:
        av1_cpu = "libsvtav1" if "libsvtav1" in self.encoder_caps else "libaom-av1"
        cpu_map = {
            "h264": "libx264",
            "h265": "libx265",
            "av1": av1_cpu,
            "vp9": "libvpx-vp9",
            "prores": "prores_ks",
            "mpeg2": "mpeg2video",
        }
        if codec not in cpu_map:
            return "libx264", False

        hw_map = {
            "nvidia": {"h264": "h264_nvenc", "h265": "hevc_nvenc", "av1": "av1_nvenc"},
            "intel": {"h264": "h264_qsv", "h265": "hevc_qsv", "av1": "av1_qsv"},
            "amd": {"h264": "h264_amf", "h265": "hevc_amf", "av1": "av1_amf"},
        }

        if hw_pref == "cpu" or codec in {"prores", "mpeg2"}:
            encoder = cpu_map[codec]
            if self.encoder_caps and encoder not in self.encoder_caps:
                if log_cb:
                    log_cb("WARN", f"Кодек {encoder} недоступний. Перемикаю на libx264.")
                return "libx264", False
            return encoder, False

        if hw_pref == "auto":
            for vendor in ["nvidia", "intel", "amd"]:
                encoder = hw_map.get(vendor, {}).get(codec)
                if encoder and encoder in self.encoder_caps:
                    return encoder, True
            encoder = cpu_map[codec]
            if self.encoder_caps and encoder not in self.encoder_caps:
                if log_cb:
                    log_cb("WARN", f"Кодек {encoder} недоступний. Перемикаю на libx264.")
                return "libx264", False
            return encoder, False

        encoder = hw_map.get(hw_pref, {}).get(codec)
        if encoder and encoder in self.encoder_caps:
            return encoder, True

        if log_cb:
            log_cb("WARN", "Обраний GPU-енкодер недоступний. Використовую CPU.")
        encoder = cpu_map[codec]
        if self.encoder_caps and encoder not in self.encoder_caps:
            if log_cb:
                log_cb("WARN", f"Кодек {encoder} недоступний. Перемикаю на libx264.")
            return "libx264", False
        return encoder, False

    def encoder_quality_args(self, encoder: str, crf: int) -> List[str]:
        if encoder in {"libx264", "libx265", "libsvtav1", "libaom-av1"}:
            return ["-crf", str(crf)]
        if encoder == "libvpx-vp9":
            return ["-crf", str(crf), "-b:v", "0"]
        if encoder == "prores_ks":
            return ["-profile:v", "3"]
        if encoder == "mpeg2video":
            qscale = max(2, min(31, int(round(2 + (max(0, min(51, int(crf))) / 51.0) * 29))))
            return ["-q:v", str(qscale)]
        if encoder.endswith("_nvenc"):
            return ["-rc:v", "vbr", "-cq", str(crf), "-b:v", "0"]
        if encoder.endswith("_qsv"):
            return ["-global_quality", str(crf)]
        if encoder.endswith("_amf"):
            return ["-rc", "cqp", "-qp_i", str(crf), "-qp_p", str(crf), "-qp_b", str(crf)]
        return []

    def video_audio_codec_args(self, settings: ConversionSettings, out_ext: str) -> List[str]:
        if out_ext == ".webm":
            return ["-c:a", "libopus", "-b:a", "128k"]
        requested = str(settings.audio_codec or "auto").strip().lower()
        if requested == "copy":
            return ["-c:a", "copy"]
        codec_map = {
            "aac": "aac",
            "ac3": "ac3",
            "opus": "libopus",
            "mp3": "libmp3lame",
        }
        codec = codec_map.get(requested, "aac")
        bitrate = settings.audio_bitrate or ("384k" if codec == "ac3" else "192k")
        return ["-c:a", codec, "-b:a", bitrate]

    def video_profile_args(self, encoder: str, settings: ConversionSettings) -> List[str]:
        profile = str(settings.video_profile or "").strip().lower()
        if profile not in {"baseline", "main", "high"}:
            return []
        if encoder in {"libx264", "h264_nvenc", "h264_qsv", "h264_amf"}:
            return ["-profile:v", profile]
        return []

    def target_video_bitrate_kbps(self, settings: ConversionSettings, info: Optional[MediaInfo]) -> Optional[int]:
        if not settings.target_size_mb or not info or not info.duration or info.duration <= 0:
            return None
        total_kbits = float(settings.target_size_mb) * 8192.0
        audio_kbps = _bitrate_to_kbps(settings.audio_bitrate, fallback=160)
        mux_overhead = 0.94
        video_kbps = int((total_kbits * mux_overhead / info.duration) - audio_kbps)
        return max(video_kbps, 120)

    def target_audio_bitrate_kbps(self, settings: ConversionSettings, duration: Optional[float]) -> Optional[int]:
        if not settings.target_size_mb or not duration or duration <= 0:
            return None
        total_kbits = float(settings.target_size_mb) * 8192.0
        return max(32, int(total_kbits * 0.96 / duration))

    def source_matches_codec_choice(self, info: Optional[MediaInfo], codec_choice: str, out_ext: str) -> bool:
        if not info or not info.vcodec:
            return False
        source = _normalize_video_codec(info.vcodec)
        wanted = _normalize_video_codec(self.resolve_codec(out_ext, codec_choice))
        return bool(source and wanted and source == wanted)

    def build_trim_args(self, settings: ConversionSettings, log_cb=None) -> List[str]:
        args: List[str] = []
        start = settings.trim_start
        end = settings.trim_end
        if start is not None:
            args += ["-ss", f"{start:.3f}"]
        if end is not None:
            if start is not None and end <= start:
                if log_cb:
                    log_cb("WARN", "Trim end <= start. Ігнорую end.")
            else:
                args += ["-to", f"{end:.3f}"]
        return args

    def _get_resize_filter(self, settings: ConversionSettings) -> Optional[str]:
        w = settings.resize_w
        h = settings.resize_h
        if w is None and h is None:
            return None
        if w is None:
            w = -1
        if h is None:
            h = -1
        return f"scale={w}:{h}"

    def _get_crop_filter(self, settings: ConversionSettings) -> Optional[str]:
        w = settings.crop_w
        h = settings.crop_h
        if w is None or h is None:
            return None
        x = settings.crop_x or 0
        y = settings.crop_y or 0
        return f"crop={w}:{h}:{x}:{y}"

    def _get_speed_value(self, settings: ConversionSettings) -> Optional[float]:
        speed = settings.speed
        if speed is None or speed <= 0:
            return None
        return speed

    def build_audio_speed_filter(self, settings: ConversionSettings) -> Optional[str]:
        speed = self._get_speed_value(settings)
        if speed is None or abs(speed - 1.0) < 0.001:
            return None
        chain = build_atempo_chain(speed)
        if not chain:
            return None
        return ",".join([f"atempo={factor:.3f}" for factor in chain])

    def build_audio_filter(self, settings: ConversionSettings) -> Optional[str]:
        filters: List[str] = []

        speed_filter = self.build_audio_speed_filter(settings)
        if speed_filter:
            filters.append(speed_filter)

        if settings.trim_silence:
            silence_duration = max(0.1, float(settings.silence_duration))
            silence_threshold = int(settings.silence_threshold_db)
            filters.append(
                "silenceremove="
                f"start_periods=1:start_duration={silence_duration:.2f}:start_threshold={silence_threshold}dB:"
                f"stop_periods=-1:stop_duration={silence_duration:.2f}:stop_threshold={silence_threshold}dB"
            )

        if settings.normalize_audio == "ebu_r128":
            filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")

        if settings.audio_peak_limit_db is not None:
            peak_linear = pow(10.0, float(settings.audio_peak_limit_db) / 20.0)
            peak_linear = max(0.01, min(1.0, peak_linear))
            filters.append(f"alimiter=limit={peak_linear:.3f}")

        if not filters:
            return None
        return ",".join(filters)

    def has_audio_processing(self, settings: ConversionSettings) -> bool:
        return bool(self.build_audio_filter(settings))

    def build_subtitle_burn_filter(self, inp: Path, settings: ConversionSettings, log_cb=None) -> Optional[str]:
        should_burn = settings.operation == "subtitle_burn" or settings.subtitle_mode in {"burn", "burn_in"}
        if not should_burn:
            return None
        source = settings.subtitle_path.strip()
        subtitle_source = Path(source).expanduser() if source else inp
        if source and not subtitle_source.exists():
            if log_cb:
                log_cb("WARN", f"Subtitle файл не знайдено: {source}")
            return None
        stream_idx = max(0, int(settings.subtitle_stream))
        subtitle_filter = f"subtitles='{escape_filter_path(str(subtitle_source.resolve()))}':si={stream_idx}"
        if settings.subtitle_style_enabled:
            style_parts = [
                f"FontSize={max(6, int(settings.subtitle_font_size))}",
                f"PrimaryColour={_ass_color(settings.subtitle_primary_color)}",
                f"Outline={max(0, int(settings.subtitle_outline))}",
                f"Shadow={max(0, int(settings.subtitle_shadow))}",
                f"Alignment={max(1, min(9, int(settings.subtitle_alignment)))}",
            ]
            if settings.subtitle_font_name.strip():
                style_parts.append(f"FontName={settings.subtitle_font_name.strip()}")
            subtitle_filter += f":force_style='{','.join(style_parts)}'"
        return subtitle_filter

    def build_privacy_blur_filters(self, settings: ConversionSettings, log_cb=None) -> List[str]:
        filters: List[str] = []
        raw = settings.privacy_blur_regions.strip()
        if not raw:
            return filters
        for region in raw.split(";"):
            parts = [part.strip() for part in region.replace(",", ":").split(":") if part.strip()]
            if len(parts) != 4:
                if log_cb:
                    log_cb("WARN", f"Blur region ignored: {region}")
                continue
            try:
                x, y, w, h = [max(0, int(float(part))) for part in parts]
            except ValueError:
                if log_cb:
                    log_cb("WARN", f"Blur region ignored: {region}")
                continue
            if w <= 0 or h <= 0:
                continue
            filters.append(f"delogo=x={x}:y={y}:w={w}:h={h}:show=0")
        return filters

    def build_editor_filters(self, settings: ConversionSettings, log_cb=None) -> List[str]:
        filters: List[str] = []
        if settings.editor_deinterlace:
            filters.append("yadif")
        if settings.editor_stabilize:
            filters.append("deshake")
        if settings.editor_denoise == "hqdn3d":
            filters.append("hqdn3d")
        elif settings.editor_denoise == "nlmeans":
            filters.append("nlmeans")
        eq_parts: List[str] = []
        if abs(float(settings.editor_brightness)) > 0.001:
            eq_parts.append(f"brightness={float(settings.editor_brightness):.3f}")
        if abs(float(settings.editor_contrast) - 1.0) > 0.001:
            eq_parts.append(f"contrast={float(settings.editor_contrast):.3f}")
        if abs(float(settings.editor_saturation) - 1.0) > 0.001:
            eq_parts.append(f"saturation={float(settings.editor_saturation):.3f}")
        if abs(float(settings.editor_gamma) - 1.0) > 0.001:
            eq_parts.append(f"gamma={float(settings.editor_gamma):.3f}")
        if eq_parts:
            filters.append("eq=" + ":".join(eq_parts))
        lut_path = settings.editor_lut_path.strip()
        if lut_path:
            path = Path(lut_path).expanduser()
            if path.exists():
                filters.append(f"lut3d=file='{escape_filter_path(str(path.resolve()))}'")
            elif log_cb:
                log_cb("WARN", f"LUT файл не знайдено: {lut_path}")
        return filters

    def build_text_filter(self, settings: ConversionSettings) -> Optional[str]:
        text = settings.text_wm.strip()
        if not text:
            return None
        size = settings.text_size
        color = settings.text_color.strip() or "white"
        fontfile = settings.text_font.strip()
        pos = settings.text_pos
        text_pos_map = {
            "Верх-ліворуч": "10:10",
            "Верх-праворуч": "W-tw-10:10",
            "Низ-ліворуч": "10:H-th-10",
            "Низ-праворуч": "W-tw-10:H-th-10",
            "Центр": "(W-tw)/2:(H-th)/2",
        }
        pos_expr = text_pos_map.get(pos, "10:10")
        x, y = pos_expr.split(":", 1)
        draw = f"drawtext=text='{escape_drawtext(text)}':x={x}:y={y}:fontsize={size}:fontcolor={color}"
        if fontfile:
            draw += f":fontfile='{escape_filter_path(fontfile)}'"
        if settings.text_box:
            opacity = max(0, min(100, settings.text_box_opacity)) / 100.0
            box_color = settings.text_box_color.strip() or "black"
            draw += f":box=1:boxcolor={box_color}@{opacity:.2f}"
        return draw

    def build_video_filter_spec(
        self,
        inp: Path,
        settings: ConversionSettings,
        out_ext: str,
        log_cb=None,
    ) -> Tuple[Optional[str], Optional[str], Optional[str], List[str], bool]:
        filters: List[str] = []

        resize_filter = self._get_resize_filter(settings)
        if resize_filter:
            filters.append(resize_filter)

        crop_filter = self._get_crop_filter(settings)
        if crop_filter:
            filters.append(crop_filter)

        filters.extend(self.build_privacy_blur_filters(settings, log_cb=log_cb))
        filters.extend(self.build_editor_filters(settings, log_cb=log_cb))

        rotate_expr = None
        if settings.rotate:
            from app.constants import ROTATE_MAP

            rotate_expr = ROTATE_MAP.get(settings.rotate)
        if rotate_expr:
            filters.append(rotate_expr)

        speed = self._get_speed_value(settings)
        if speed and abs(speed - 1.0) > 0.001:
            filters.append(f"setpts=PTS/{speed}")

        subtitle_filter = self.build_subtitle_burn_filter(inp, settings, log_cb=log_cb)
        if subtitle_filter:
            filters.append(subtitle_filter)

        text_filter = self.build_text_filter(settings)
        if text_filter:
            filters.append(text_filter)

        portrait = PORTRAIT_PRESETS.get(settings.portrait)
        use_blur = False
        blur_graph = ""
        if portrait:
            mode, w, h = portrait
            if mode == "crop":
                filters.insert(0, f"scale='if(gt(a,9/16),-2,{w})':'if(gt(a,9/16),{h},-2)',crop={w}:{h},setsar=1")
            else:
                use_blur = True
                blur_graph = (
                    f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,boxblur=20:1,crop={w}:{h}[bg];"
                    f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
                    f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1"
                )

        if out_ext == ".gif":
            filters.append("fps=12")
            if resize_filter is None:
                filters.append("scale=640:-1:flags=lanczos")

        watermark_inputs: List[str] = []
        watermark_path = settings.watermark_path.strip()
        if watermark_path:
            wm_path = Path(watermark_path).expanduser()
            if wm_path.exists():
                watermark_inputs.append(str(wm_path))
            elif log_cb:
                log_cb("WARN", f"Водяний знак не знайдено: {watermark_path}")

        if not use_blur and not watermark_inputs:
            if filters:
                return "-vf", ",".join(filters), None, [], True
            return None, None, None, [], False

        base_label = "vbase"
        graph_parts: List[str] = []
        if use_blur:
            graph = blur_graph
            if filters:
                graph += f",{','.join(filters)}"
            graph += f"[{base_label}]"
            graph_parts.append(graph)
        else:
            chain = ",".join(filters) if filters else "null"
            graph_parts.append(f"[0:v]{chain}[{base_label}]")

        out_label = base_label
        if watermark_inputs:
            wm_chain = "[1:v]format=rgba"
            wm_scale = max(1, int(settings.watermark_scale)) / 100.0
            wm_opacity = max(0, min(100, int(settings.watermark_opacity))) / 100.0
            wm_chain += f",scale=iw*{wm_scale}:ih*{wm_scale}"
            wm_chain += f",colorchannelmixer=aa={wm_opacity}"
            wm_chain += "[wm]"
            graph_parts.append(wm_chain)
            pos_expr = POSITION_MAP.get(settings.watermark_pos, "10:10")
            graph_parts.append(f"[{base_label}][wm]overlay={pos_expr}[vout]")
            out_label = "vout"

        return "-filter_complex", ";".join(graph_parts), f"[{out_label}]", watermark_inputs, True

    def build_image_filter_spec(
        self,
        settings: ConversionSettings,
        log_cb=None,
    ) -> Tuple[Optional[str], Optional[str], Optional[str], List[str]]:
        filters: List[str] = []

        resize_filter = self._get_resize_filter(settings)
        if resize_filter:
            filters.append(resize_filter)

        crop_filter = self._get_crop_filter(settings)
        if crop_filter:
            filters.append(crop_filter)

        rotate_expr = None
        if settings.rotate:
            from app.constants import ROTATE_MAP

            rotate_expr = ROTATE_MAP.get(settings.rotate)
        if rotate_expr:
            filters.append(rotate_expr)

        text_filter = self.build_text_filter(settings)
        if text_filter:
            filters.append(text_filter)

        watermark_inputs: List[str] = []
        watermark_path = settings.watermark_path.strip()
        if watermark_path:
            wm_path = Path(watermark_path).expanduser()
            if wm_path.exists():
                watermark_inputs.append(str(wm_path))
            elif log_cb:
                log_cb("WARN", f"Водяний знак не знайдено: {watermark_path}")

        if not watermark_inputs:
            if filters:
                return "-vf", ",".join(filters), None, []
            return None, None, None, []

        base_label = "vbase"
        graph_parts: List[str] = []
        chain = ",".join(filters) if filters else "null"
        graph_parts.append(f"[0:v]{chain}[{base_label}]")

        wm_chain = "[1:v]format=rgba"
        wm_scale = max(1, int(settings.watermark_scale)) / 100.0
        wm_opacity = max(0, min(100, int(settings.watermark_opacity))) / 100.0
        wm_chain += f",scale=iw*{wm_scale}:ih*{wm_scale}"
        wm_chain += f",colorchannelmixer=aa={wm_opacity}"
        wm_chain += "[wm]"
        graph_parts.append(wm_chain)
        pos_expr = POSITION_MAP.get(settings.watermark_pos, "10:10")
        graph_parts.append(f"[{base_label}][wm]overlay={pos_expr}[vout]")

        return "-filter_complex", ";".join(graph_parts), "[vout]", watermark_inputs

    def metadata_args(self, settings: ConversionSettings) -> List[str]:
        args: List[str] = []
        if settings.strip_metadata:
            args += ["-map_metadata", "-1"]
        elif settings.copy_metadata:
            args += ["-map_metadata", "0"]
        title = settings.meta_title.strip()
        if title:
            args += ["-metadata", f"title={title}"]
        comment = settings.meta_comment.strip()
        if comment:
            args += ["-metadata", f"comment={comment}"]
        author = settings.meta_author.strip()
        if author:
            args += ["-metadata", f"artist={author}"]
        copyright_text = settings.meta_copyright.strip()
        if copyright_text:
            args += ["-metadata", f"copyright={copyright_text}"]
        album = settings.meta_album.strip()
        if album:
            args += ["-metadata", f"album={album}"]
        genre = settings.meta_genre.strip()
        if genre:
            args += ["-metadata", f"genre={genre}"]
        year = settings.meta_year.strip()
        if year:
            args += ["-metadata", f"date={year}"]
        track = settings.meta_track.strip()
        if track:
            args += ["-metadata", f"track={track}"]
        return args

    def fast_copy_allowed(
        self,
        inp: Path,
        out_ext: str,
        info: Optional[MediaInfo],
        filters_used: bool,
        audio_filter_used: bool,
        allow_remux: bool = False,
    ) -> Tuple[bool, str]:
        if out_ext.lower() == ".gif":
            return False, "GIF потребує перекодування"
        if filters_used or audio_filter_used:
            return False, "Є фільтри/зміна швидкості"
        if info and info.vcodec and not _container_supports_codec(out_ext, info.vcodec):
            return False, "Кодек несумісний з контейнером"
        if inp.suffix.lower() != out_ext.lower() and not allow_remux:
            return False, "Контейнер відрізняється"
        return True, ""

    def merge_copy_allowed(
        self,
        inputs: List[Path],
        out_ext: str,
        infos: Dict[Path, MediaInfo],
        filters_used: bool,
        audio_filter_used: bool,
        trim_args: List[str],
    ) -> Tuple[bool, str]:
        if filters_used or audio_filter_used or trim_args:
            return False, "Є фільтри або trim"
        if out_ext.lower() != inputs[0].suffix.lower():
            return False, "Контейнер відрізняється"
        vcodecs = set()
        acodecs = set()
        for path in inputs:
            info = infos.get(path)
            if not info or not info.vcodec:
                return False, "Немає даних ffprobe"
            vcodecs.add(info.vcodec)
            if info.acodec:
                acodecs.add(info.acodec)
        if len(vcodecs) > 1 or len(acodecs) > 1:
            return False, "Різні кодеки"
        return True, ""

    def _resolve_replace_audio_path(self, settings: ConversionSettings, log_cb=None) -> Optional[Path]:
        source = settings.replace_audio_path.strip()
        if not source:
            return None
        audio_path = Path(source).expanduser()
        if not audio_path.exists():
            if log_cb:
                log_cb("WARN", f"Файл заміни аудіо не знайдено: {source}")
            return None
        return audio_path

    def _resolve_cover_art_path(self, settings: ConversionSettings, log_cb=None) -> Optional[Path]:
        source = settings.cover_art_path.strip()
        if not source:
            return None
        cover_path = Path(source).expanduser()
        if not cover_path.exists():
            if log_cb:
                log_cb("WARN", f"Cover art не знайдено: {source}")
            return None
        return cover_path

    def _write_concat_list(self, inputs: List[Path]) -> str:
        tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".txt", encoding="utf-8")
        with tmp as fh:
            for path in inputs:
                safe = str(path.resolve()).replace("'", "'\\''")
                fh.write(f"file '{safe}'\n")
        return tmp.name

    def build_two_pass_commands(self, final_cmd: List[str], passlogfile: Path) -> Tuple[List[str], List[str]]:
        if not final_cmd:
            return [], []
        passlog = str(passlogfile)
        pass1 = list(final_cmd[:-1])
        pass1 += ["-pass", "1", "-passlogfile", passlog, "-an", "-sn", "-f", "null", _null_output()]
        pass2 = list(final_cmd[:-1])
        pass2 += ["-pass", "2", "-passlogfile", passlog, final_cmd[-1]]
        return pass1, pass2

    def build_integrity_check_command(self, output_path: Path) -> List[str]:
        return [self.ffmpeg_path, "-v", "error", "-i", str(output_path), "-map", "0", "-f", "null", _null_output()]

    def check_media_integrity(self, output_path: Path, timeout: int = 300) -> Tuple[bool, str]:
        if not self.ffmpeg_path:
            return False, "FFmpeg path is not configured."
        try:
            result = subprocess.run(
                self.build_integrity_check_command(output_path),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return False, "Integrity check timed out."
        except Exception as exc:
            return False, str(exc)
        details = (result.stderr or result.stdout or "").strip()
        return result.returncode == 0, details

    def build_quality_metric_command(self, source_path: Path, output_path: Path, metric: str) -> List[str]:
        normalized = str(metric or "").strip().lower()
        if normalized == "vmaf":
            lavfi = (
                "[0:v]scale=640:-2,setpts=PTS-STARTPTS[dist];"
                "[1:v]scale=640:-2,setpts=PTS-STARTPTS[ref];"
                "[dist][ref]libvmaf"
            )
        else:
            lavfi = (
                "[0:v]scale=640:-2,setpts=PTS-STARTPTS[dist];"
                "[1:v]scale=640:-2,setpts=PTS-STARTPTS[ref];"
                "[dist][ref]ssim"
            )
        return [self.ffmpeg_path, "-v", "info", "-i", str(output_path), "-i", str(source_path), "-lavfi", lavfi, "-f", "null", _null_output()]

    def measure_quality(self, source_path: Path, output_path: Path, metric: str, timeout: int = 300) -> Tuple[bool, Optional[float], str]:
        normalized = str(metric or "none").strip().lower()
        if normalized not in {"ssim", "vmaf"}:
            return True, None, ""
        if not self.ffmpeg_path:
            return False, None, "FFmpeg path is not configured."
        try:
            result = subprocess.run(
                self.build_quality_metric_command(source_path, output_path, normalized),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return False, None, f"{normalized.upper()} check timed out."
        except Exception as exc:
            return False, None, str(exc)
        details = "\n".join(part for part in [result.stdout, result.stderr] if part).strip()
        score: Optional[float] = None
        if normalized == "ssim":
            match = re.search(r"All:\s*([0-9.]+)", details)
            if match:
                score = float(match.group(1))
        else:
            match = re.search(r"VMAF score:\s*([0-9.]+)", details)
            if match:
                score = float(match.group(1))
        return result.returncode == 0, score, details[-600:]

    def build_video_command(
        self,
        inp: Path,
        outp: Path,
        settings: ConversionSettings,
        info: Optional[MediaInfo],
        allow_fast_copy: bool,
        log_cb=None,
    ) -> List[str]:
        overwrite = "-y" if settings.overwrite else "-n"
        out_ext = outp.suffix.lower()
        trim_args = self.build_trim_args(settings, log_cb=log_cb)
        filter_arg, filter_val, map_label, extra_inputs, filters_used = self.build_video_filter_spec(
            inp, settings, out_ext, log_cb=log_cb
        )
        audio_filter = self.build_audio_filter(settings)
        replace_audio = self._resolve_replace_audio_path(settings, log_cb=log_cb)

        if allow_fast_copy and replace_audio is None:
            track_index = max(0, int(settings.audio_track_index))
            cmd = [self.ffmpeg_path, overwrite, "-i", str(inp)]
            cmd += trim_args
            cmd += ["-map", "0:v:0?", "-map", f"0:a:{track_index}?", "-map", "0:s?"]
            cmd += ["-c", "copy"]
            cmd += self.metadata_args(settings)
            if out_ext in {".mp4", ".mov", ".m4v"}:
                cmd += ["-movflags", "+faststart"]
            cmd.append(str(outp))
            return cmd

        cmd = [self.ffmpeg_path, overwrite, "-i", str(inp)]
        if extra_inputs:
            cmd += ["-i", extra_inputs[0]]
        audio_input_index = 1 + len(extra_inputs)
        if replace_audio is not None:
            cmd += ["-i", str(replace_audio)]
        cmd += trim_args

        if filter_arg:
            cmd += [filter_arg, filter_val]
            if filter_arg == "-filter_complex" and map_label:
                cmd += ["-map", map_label]
            else:
                cmd += ["-map", "0:v:0?"]
        else:
            cmd += ["-map", "0:v:0?"]

        if out_ext != ".gif":
            if replace_audio is not None:
                cmd += ["-map", f"{audio_input_index}:a:0?"]
            else:
                track_index = max(0, int(settings.audio_track_index))
                cmd += ["-map", f"0:a:{track_index}?"]
            if audio_filter:
                cmd += ["-filter:a", audio_filter]
        else:
            cmd += ["-an"]

        if out_ext == ".gif":
            cmd += self.metadata_args(settings)
            cmd.append(str(outp))
            return cmd

        codec = self.resolve_codec(out_ext, settings.video_codec, log_cb=log_cb)
        encoder, is_hw = self.select_encoder(codec, HW_ENCODER_MAP.get(settings.hw_encoder, "auto"), log_cb=log_cb)
        cmd += ["-c:v", encoder]
        if not is_hw and encoder in {"libx264", "libx265"}:
            cmd += ["-preset", (settings.preset or "medium").strip()]
        target_video_kbps = self.target_video_bitrate_kbps(settings, info)
        if target_video_kbps:
            cmd += ["-b:v", f"{target_video_kbps}k", "-maxrate", f"{int(target_video_kbps * 1.35)}k", "-bufsize", f"{int(target_video_kbps * 2)}k"]
        else:
            cmd += self.encoder_quality_args(encoder, settings.crf)
        if encoder in {
            "libx264",
            "libx265",
            "h264_nvenc",
            "hevc_nvenc",
            "h264_qsv",
            "hevc_qsv",
            "h264_amf",
            "hevc_amf",
        }:
            cmd += ["-pix_fmt", "yuv420p"]
        elif encoder == "prores_ks":
            cmd += ["-pix_fmt", "yuv422p10le"]

        cmd += self.video_profile_args(encoder, settings)
        cmd += self.video_audio_codec_args(settings, out_ext)

        if out_ext in {".mp4", ".mov", ".m4v"}:
            cmd += ["-movflags", "+faststart"]
        if replace_audio is not None:
            cmd += ["-shortest"]

        cmd += self.metadata_args(settings)
        cmd.append(str(outp))
        return cmd

    def build_audio_command(
        self,
        inp: Path,
        outp: Path,
        settings: ConversionSettings,
        duration: Optional[float] = None,
        log_cb=None,
    ) -> List[str]:
        overwrite = "-y" if settings.overwrite else "-n"
        out_ext = outp.suffix.lower()
        trim_args = self.build_trim_args(settings, log_cb=log_cb)
        audio_filter = self.build_audio_filter(settings)
        codec_map = {
            ".mp3": "libmp3lame",
            ".m4a": "aac",
            ".aac": "aac",
            ".wav": "pcm_s16le",
            ".flac": "flac",
            ".opus": "libopus",
        }
        codec = codec_map.get(out_ext, "aac")
        cmd = [self.ffmpeg_path, overwrite, "-i", str(inp)]
        cover_art = self._resolve_cover_art_path(settings, log_cb=log_cb)
        if cover_art and out_ext in {".mp3", ".m4a", ".aac"}:
            cmd += ["-i", str(cover_art)]
        cmd += trim_args
        track_index = max(0, int(settings.audio_track_index))
        cmd += ["-vn", "-sn", "-map", f"0:a:{track_index}?"]
        if cover_art and out_ext in {".mp3", ".m4a", ".aac"}:
            cmd += ["-map", "1:v:0"]
        if audio_filter:
            cmd += ["-filter:a", audio_filter]
        cmd += ["-c:a", codec]
        if codec in {"libmp3lame", "aac", "libopus"}:
            target_audio_kbps = self.target_audio_bitrate_kbps(settings, duration)
            cmd += ["-b:a", f"{target_audio_kbps}k" if target_audio_kbps else settings.audio_bitrate or "192k"]
        if cover_art and out_ext in {".mp3", ".m4a", ".aac"}:
            cmd += ["-c:v", "mjpeg", "-disposition:v:0", "attached_pic"]
            if out_ext == ".mp3":
                cmd += ["-id3v2_version", "3"]
        cmd += self.metadata_args(settings)
        cmd.append(str(outp))
        return cmd

    def build_subtitle_extract_command(
        self,
        inp: Path,
        outp: Path,
        settings: ConversionSettings,
    ) -> List[str]:
        overwrite = "-y" if settings.overwrite else "-n"
        stream_idx = max(0, int(settings.subtitle_stream))
        codec_map = {
            ".srt": "srt",
            ".ass": "ass",
            ".vtt": "webvtt",
        }
        codec = codec_map.get(outp.suffix.lower(), "srt")
        cmd = [self.ffmpeg_path, overwrite, "-i", str(inp)]
        cmd += ["-map", f"0:s:{stream_idx}?", "-vn", "-an", "-c:s", codec]
        cmd.append(str(outp))
        return cmd

    def build_subtitle_file_command(
        self,
        inp: Path,
        outp: Path,
        settings: ConversionSettings,
    ) -> List[str]:
        overwrite = "-y" if settings.overwrite else "-n"
        codec_map = {
            ".srt": "srt",
            ".ass": "ass",
            ".vtt": "webvtt",
        }
        codec = codec_map.get(outp.suffix.lower(), "srt")
        cmd = [self.ffmpeg_path, overwrite]
        if settings.subtitle_sync_ms:
            cmd += ["-itsoffset", f"{float(settings.subtitle_sync_ms) / 1000.0:.3f}"]
        cmd += ["-i", str(inp), "-c:s", codec]
        cmd.append(str(outp))
        return cmd

    def build_image_command(
        self,
        inp: Path,
        outp: Path,
        settings: ConversionSettings,
        log_cb=None,
    ) -> List[str]:
        overwrite = "-y" if settings.overwrite else "-n"
        ext = outp.suffix.lower()

        filter_arg, filter_val, map_label, extra_inputs = self.build_image_filter_spec(settings, log_cb=log_cb)
        cmd = [self.ffmpeg_path, overwrite, "-i", str(inp)]
        if extra_inputs:
            cmd += ["-i", extra_inputs[0]]
        if filter_arg:
            cmd += [filter_arg, filter_val]
            if filter_arg == "-filter_complex" and map_label:
                cmd += ["-map", map_label]

        cmd += self.metadata_args(settings)

        quality = int(settings.img_quality)
        if ext in {".jpg", ".jpeg"}:
            qv = max(2, min(31, int(round(31 - (quality / 100) * 29))))
            cmd += ["-q:v", str(qv)]
        elif ext == ".webp":
            cmd += ["-q:v", str(max(0, min(100, quality)))]

        cmd.append(str(outp))
        return cmd

    def build_thumbnail_command(
        self,
        inp: Path,
        outp: Path,
        settings: ConversionSettings,
        log_cb=None,
    ) -> List[str]:
        overwrite = "-y" if settings.overwrite else "-n"
        time_value = settings.thumbnail_time
        if time_value is None:
            time_value = settings.trim_start if settings.trim_start is not None else 5.0
        filter_arg, filter_val, map_label, extra_inputs = self.build_image_filter_spec(settings, log_cb=log_cb)
        cmd = [self.ffmpeg_path, overwrite, "-ss", f"{time_value:.3f}", "-i", str(inp)]
        if extra_inputs:
            cmd += ["-i", extra_inputs[0]]
        if filter_arg:
            cmd += [filter_arg, filter_val]
            if filter_arg == "-filter_complex" and map_label:
                cmd += ["-map", map_label]
        cmd += ["-frames:v", "1"]
        cmd += self.metadata_args(settings)
        cmd.append(str(outp))
        return cmd

    def build_contact_sheet_command(
        self,
        inp: Path,
        outp: Path,
        settings: ConversionSettings,
    ) -> List[str]:
        overwrite = "-y" if settings.overwrite else "-n"
        cols = max(1, settings.contact_sheet_cols)
        rows = max(1, settings.contact_sheet_rows)
        interval = max(1, settings.contact_sheet_interval)
        width = max(80, settings.contact_sheet_width)
        vf = f"fps=1/{interval},scale={width}:-1,tile={cols}x{rows}"
        cmd = [self.ffmpeg_path, overwrite, "-i", str(inp), "-vf", vf, "-frames:v", "1"]
        cmd += self.metadata_args(settings)
        cmd.append(str(outp))
        return cmd

    def build_merge_command(
        self,
        inputs: List[Path],
        outp: Path,
        settings: ConversionSettings,
        infos: Dict[Path, MediaInfo],
        allow_fast_copy: bool,
        log_cb=None,
    ) -> Tuple[List[str], str]:
        overwrite = "-y" if settings.overwrite else "-n"
        list_path = self._write_concat_list(inputs)
        out_ext = outp.suffix.lower()
        trim_args = self.build_trim_args(settings, log_cb=log_cb)
        filter_arg, filter_val, map_label, extra_inputs, _ = self.build_video_filter_spec(
            inputs[0], settings, out_ext, log_cb=log_cb
        )
        audio_filter = self.build_audio_filter(settings)

        cmd = [self.ffmpeg_path, overwrite, "-f", "concat", "-safe", "0", "-i", list_path]
        if extra_inputs:
            cmd += ["-i", extra_inputs[0]]
        cmd += trim_args

        if allow_fast_copy:
            track_index = max(0, int(settings.audio_track_index))
            cmd += ["-map", "0:v:0?", "-map", f"0:a:{track_index}?", "-map", "0:s?"]
            cmd += ["-c", "copy"]
            cmd += self.metadata_args(settings)
            if out_ext in {".mp4", ".mov", ".m4v"}:
                cmd += ["-movflags", "+faststart"]
            cmd.append(str(outp))
            return cmd, list_path

        if filter_arg:
            cmd += [filter_arg, filter_val]
            if filter_arg == "-filter_complex" and map_label:
                cmd += ["-map", map_label]
            else:
                cmd += ["-map", "0:v:0?"]
        else:
            cmd += ["-map", "0:v:0?"]

        if out_ext != ".gif":
            track_index = max(0, int(settings.audio_track_index))
            cmd += ["-map", f"0:a:{track_index}?"]
            if audio_filter:
                cmd += ["-filter:a", audio_filter]
        else:
            cmd += ["-an"]

        if out_ext == ".gif":
            cmd += self.metadata_args(settings)
            cmd.append(str(outp))
            return cmd, list_path

        codec = self.resolve_codec(out_ext, settings.video_codec, log_cb=log_cb)
        encoder, is_hw = self.select_encoder(codec, HW_ENCODER_MAP.get(settings.hw_encoder, "auto"), log_cb=log_cb)
        cmd += ["-c:v", encoder]
        if not is_hw and encoder in {"libx264", "libx265"}:
            cmd += ["-preset", (settings.preset or "medium").strip()]
        cmd += self.encoder_quality_args(encoder, settings.crf)
        if encoder in {
            "libx264",
            "libx265",
            "h264_nvenc",
            "hevc_nvenc",
            "h264_qsv",
            "hevc_qsv",
            "h264_amf",
            "hevc_amf",
        }:
            cmd += ["-pix_fmt", "yuv420p"]
        elif encoder == "prores_ks":
            cmd += ["-pix_fmt", "yuv422p10le"]

        cmd += self.video_profile_args(encoder, settings)
        cmd += self.video_audio_codec_args(settings, out_ext)

        if out_ext in {".mp4", ".mov", ".m4v"}:
            cmd += ["-movflags", "+faststart"]

        cmd += self.metadata_args(settings)
        cmd.append(str(outp))
        return cmd, list_path
