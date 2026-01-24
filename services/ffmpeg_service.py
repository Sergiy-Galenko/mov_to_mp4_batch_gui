import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config.constants import (
    PORTRAIT_PRESETS,
    POSITION_MAP,
    VIDEO_CODEC_MAP,
    HW_ENCODER_MAP,
)
from core.models import ConversionSettings, MediaInfo
from utils.formatting import build_atempo_chain


def escape_drawtext(text: str) -> str:
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def escape_filter_path(path: str) -> str:
    return path.replace("\\", "/").replace(":", "\\:")


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
            r = subprocess.run([self.ffmpeg_path, "-hide_banner", "-encoders"], capture_output=True, text=True)
        except Exception:
            return set()
        if r.returncode != 0:
            return set()
        encoders: set[str] = set()
        for line in r.stdout.splitlines():
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
            "-v", "error",
            "-show_entries", "format=duration,size,format_name:stream=codec_type,codec_name,width,height",
            "-of", "json",
            str(path),
        ]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
        except Exception:
            return None
        if r.returncode != 0:
            return None
        try:
            data = json.loads(r.stdout)
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
            if stream.get("codec_type") == "video" and info.vcodec is None:
                info.vcodec = stream.get("codec_name")
                info.width = stream.get("width")
                info.height = stream.get("height")
            if stream.get("codec_type") == "audio" and info.acodec is None:
                info.acodec = stream.get("codec_name")

        if info.size_bytes is None:
            try:
                info.size_bytes = path.stat().st_size
            except Exception:
                pass
        return info

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
                enc = hw_map.get(vendor, {}).get(codec)
                if enc and enc in self.encoder_caps:
                    return enc, True
            encoder = cpu_map[codec]
            if self.encoder_caps and encoder not in self.encoder_caps:
                if log_cb:
                    log_cb("WARN", f"Кодек {encoder} недоступний. Перемикаю на libx264.")
                return "libx264", False
            return encoder, False

        enc = hw_map.get(hw_pref, {}).get(codec)
        if enc and enc in self.encoder_caps:
            return enc, True

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

        rotate_filter = settings.rotate
        rotate_expr = None
        if rotate_filter:
            from config.constants import ROTATE_MAP
            rotate_expr = ROTATE_MAP.get(rotate_filter)
        if rotate_expr:
            filters.append(rotate_expr)

        speed = self._get_speed_value(settings)
        if speed and abs(speed - 1.0) > 0.001:
            filters.append(f"setpts=PTS/{speed}")

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
            else:
                if log_cb:
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
            else:
                if log_cb:
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
        if info and info.vcodec:
            if not _container_supports_codec(out_ext, info.vcodec):
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
            settings, out_ext, log_cb=log_cb
        )
        audio_filter = self.build_audio_speed_filter(settings)

        if allow_fast_copy:
            cmd = [self.ffmpeg_path, overwrite, "-i", str(inp)]
            cmd += trim_args
            cmd += ["-map", "0", "-c", "copy"]
            cmd += self.metadata_args(settings)
            if out_ext in {".mp4", ".mov", ".m4v"}:
                cmd += ["-movflags", "+faststart"]
            cmd.append(str(outp))
            return cmd

        cmd = [self.ffmpeg_path, overwrite, "-i", str(inp)]
        if extra_inputs:
            cmd += ["-i", extra_inputs[0]]
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
            cmd += ["-map", "0:a:0?"]
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
            preset = (settings.preset or "medium").strip()
            cmd += ["-preset", preset]
        cmd += self.encoder_quality_args(encoder, settings.crf)
        if encoder in {
            "libx264", "libx265",
            "h264_nvenc", "hevc_nvenc",
            "h264_qsv", "hevc_qsv",
            "h264_amf", "hevc_amf",
        }:
            cmd += ["-pix_fmt", "yuv420p"]

        if out_ext == ".webm":
            cmd += ["-c:a", "libopus", "-b:a", "128k"]
        else:
            cmd += ["-c:a", "aac", "-b:a", "192k"]

        if out_ext in {".mp4", ".mov", ".m4v"}:
            cmd += ["-movflags", "+faststart"]

        cmd += self.metadata_args(settings)
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

        q = int(settings.img_quality)
        if ext in {".jpg", ".jpeg"}:
            qv = max(2, min(31, int(round(31 - (q / 100) * 29))))
            cmd += ["-q:v", str(qv)]
        elif ext == ".webp":
            cmd += ["-q:v", str(max(0, min(100, q)))]

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
            settings, out_ext, log_cb=log_cb
        )
        audio_filter = self.build_audio_speed_filter(settings)

        cmd = [self.ffmpeg_path, overwrite, "-f", "concat", "-safe", "0", "-i", list_path]
        if extra_inputs:
            cmd += ["-i", extra_inputs[0]]
        cmd += trim_args

        if allow_fast_copy:
            cmd += ["-map", "0", "-c", "copy"]
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
            cmd += ["-map", "0:a:0?"]
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
            preset = (settings.preset or "medium").strip()
            cmd += ["-preset", preset]
        cmd += self.encoder_quality_args(encoder, settings.crf)
        if encoder in {
            "libx264", "libx265",
            "h264_nvenc", "hevc_nvenc",
            "h264_qsv", "hevc_qsv",
            "h264_amf", "hevc_amf",
        }:
            cmd += ["-pix_fmt", "yuv420p"]

        if out_ext == ".webm":
            cmd += ["-c:a", "libopus", "-b:a", "128k"]
        else:
            cmd += ["-c:a", "aac", "-b:a", "192k"]

        if out_ext in {".mp4", ".mov", ".m4v"}:
            cmd += ["-movflags", "+faststart"]

        cmd += self.metadata_args(settings)
        cmd.append(str(outp))
        return cmd, list_path
