import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config.constants import HW_ENCODER_MAP, OPERATION_MAP, PORTRAIT_PRESETS, POSITION_MAP, VIDEO_CODEC_MAP
from core.models import ConversionSettings, MediaChapter, MediaInfo
from utils.formatting import build_atempo_chain


def escape_drawtext(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def escape_filter_path(path: str) -> str:
    return path.replace("\\", "/").replace(":", "\\:")


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


class FfmpegService:
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
            result = subprocess.run(cmd, capture_output=True, text=True)
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
        if operation == "audio_only":
            return settings.out_audio_format
        if operation in {"subtitle_extract", "auto_subtitle"}:
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
            return "h264"
        if out_ext == ".webm" and choice not in {"vp9", "av1"}:
            if log_cb:
                log_cb("WARN", "WebM підтримує лише VP9/AV1. Перемикаю на VP9.")
            return "vp9"
        if out_ext in {".mp4", ".mov", ".m4v", ".avi"} and choice == "vp9":
            if log_cb:
                log_cb("WARN", "VP9 не сумісний з MP4/MOV/AVI. Перемикаю на H.264.")
            return "h264"
        return choice

    def select_encoder(self, codec: str, hw_pref: str, log_cb=None) -> Tuple[str, bool]:
        av1_cpu = "libsvtav1" if "libsvtav1" in self.encoder_caps else "libaom-av1"
        cpu_map = {
            "h264": "libx264",
            "h265": "libx265",
            "av1": av1_cpu,
            "vp9": "libvpx-vp9",
        }
        if codec not in cpu_map:
            return "libx264", False

        hw_map = {
            "nvidia": {"h264": "h264_nvenc", "h265": "hevc_nvenc", "av1": "av1_nvenc"},
            "intel": {"h264": "h264_qsv", "h265": "hevc_qsv", "av1": "av1_qsv"},
            "amd": {"h264": "h264_amf", "h265": "hevc_amf", "av1": "av1_amf"},
        }

        if hw_pref == "cpu":
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
        if encoder.endswith("_nvenc"):
            return ["-rc:v", "vbr", "-cq", str(crf), "-b:v", "0"]
        if encoder.endswith("_qsv"):
            return ["-global_quality", str(crf)]
        if encoder.endswith("_amf"):
            return ["-rc", "cqp", "-qp_i", str(crf), "-qp_p", str(crf), "-qp_b", str(crf)]
        return []

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
        should_burn = settings.operation == "subtitle_burn" or settings.subtitle_mode == "burn_in"
        if not should_burn:
            return None
        source = settings.subtitle_path.strip()
        subtitle_source = Path(source).expanduser() if source else inp
        if source and not subtitle_source.exists():
            if log_cb:
                log_cb("WARN", f"Subtitle файл не знайдено: {source}")
            return None
        stream_idx = max(0, int(settings.subtitle_stream))
        return f"subtitles='{escape_filter_path(str(subtitle_source.resolve()))}':si={stream_idx}"

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

        rotate_expr = None
        if settings.rotate:
            from config.constants import ROTATE_MAP

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
            from config.constants import ROTATE_MAP

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
    ) -> Tuple[bool, str]:
        if out_ext.lower() == ".gif":
            return False, "GIF потребує перекодування"
        if filters_used or audio_filter_used:
            return False, "Є фільтри/зміна швидкості"
        if inp.suffix.lower() != out_ext.lower():
            return False, "Контейнер відрізняється"
        if info and info.vcodec and not _container_supports_codec(out_ext, info.vcodec):
            return False, "Кодек несумісний з контейнером"
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

        if out_ext == ".webm":
            cmd += ["-c:a", "libopus", "-b:a", "128k"]
        else:
            cmd += ["-c:a", "aac", "-b:a", settings.audio_bitrate or "192k"]

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
            cmd += ["-b:a", settings.audio_bitrate or "192k"]
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

        if out_ext == ".webm":
            cmd += ["-c:a", "libopus", "-b:a", "128k"]
        else:
            cmd += ["-c:a", "aac", "-b:a", settings.audio_bitrate or "192k"]

        if out_ext in {".mp4", ".mov", ".m4v"}:
            cmd += ["-movflags", "+faststart"]

        cmd += self.metadata_args(settings)
        cmd.append(str(outp))
        return cmd, list_path
