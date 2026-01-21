import os
import sys
import threading
import queue
import subprocess
import shutil
from pathlib import Path
from typing import Optional, List, Tuple
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


APP_TITLE = "Media Converter (Фото + Відео) — FFmpeg"
VIDEO_EXTS = {".mov", ".mp4", ".mkv", ".webm", ".avi", ".m4v", ".flv", ".wmv", ".mts", ".m2ts"}
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".heic", ".heif"}

OUT_VIDEO_FORMATS = ["mp4", "mkv", "webm", "mov", "avi", "gif"]
OUT_IMAGE_FORMATS = ["jpg", "png", "webp", "bmp", "tiff"]

# Portrait presets
PORTRAIT_PRESETS = {
    "Вимкнено": None,
    "9:16 (1080x1920) — crop": ("crop", 1080, 1920),
    "9:16 (1080x1920) — blur": ("blur", 1080, 1920),
    "9:16 (720x1280) — crop": ("crop", 720, 1280),
    "9:16 (720x1280) — blur": ("blur", 720, 1280),
}


def find_ffmpeg() -> Optional[str]:
    local = Path(__file__).resolve().parent
    candidates = [
        local / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg"),
        local / "bin" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg"),
    ]
    for c in candidates:
        if c.exists() and c.is_file():
            return str(c)
    return shutil.which("ffmpeg")


def is_video(p: Path) -> bool:
    return p.suffix.lower() in VIDEO_EXTS


def is_image(p: Path) -> bool:
    return p.suffix.lower() in IMAGE_EXTS


def media_type(p: Path) -> Optional[str]:
    if is_video(p):
        return "video"
    if is_image(p):
        return "image"
    return None


def safe_output_name(out_dir: Path, in_path: Path, out_ext: str) -> Path:
    out_ext = out_ext.lstrip(".")
    base = in_path.stem
    out_path = out_dir / f"{base}.{out_ext}"
    if not out_path.exists():
        return out_path
    i = 1
    while True:
        cand = out_dir / f"{base} ({i}).{out_ext}"
        if not cand.exists():
            return cand
        i += 1


class ConverterUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1020x720")
        self.minsize(940, 650)

        self.ffmpeg_path: Optional[str] = find_ffmpeg()
        self.tasks: List[Tuple[Path, str]] = []
        self.stop_requested = False
        self.worker_thread: Optional[threading.Thread] = None
        self.ui_queue: "queue.Queue[Tuple[str, str]]" = queue.Queue()

        self._build_ui()
        self._poll_queue()

        self._log("INFO", "Підтримка: відео + фото. Тип визначається автоматично по розширенню.")
        if self.ffmpeg_path:
            self._log("OK", f"FFmpeg знайдено: {self.ffmpeg_path}")
            self.ffmpeg_var.set(self.ffmpeg_path)
        else:
            self._log("ERROR", "FFmpeg не знайдено. Натисни 'Вказати ffmpeg.exe' або додай ffmpeg у PATH.")

    # ---------------- UI ----------------
    def _build_ui(self):
        top = ttk.Frame(self, padding=12)
        top.pack(fill="x")

        ttk.Label(top, text="FFmpeg:").grid(row=0, column=0, sticky="w")
        self.ffmpeg_var = tk.StringVar(value="")
        ttk.Entry(top, textvariable=self.ffmpeg_var).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(top, text="Вказати ffmpeg.exe", command=self.pick_ffmpeg).grid(row=0, column=2, padx=4)
        ttk.Button(top, text="Перевірити", command=self.check_ffmpeg).grid(row=0, column=3, padx=4)

        ttk.Label(top, text="Джерело:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.src_var = tk.StringVar(value="")
        ttk.Entry(top, textvariable=self.src_var).grid(row=1, column=1, sticky="ew", padx=8, pady=(10, 0))
        ttk.Button(top, text="Вибрати папку", command=self.pick_folder).grid(row=1, column=2, padx=4, pady=(10, 0))
        ttk.Button(top, text="Вибрати файли", command=self.pick_files).grid(row=1, column=3, padx=4, pady=(10, 0))

        ttk.Label(top, text="Папка виводу:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.out_var = tk.StringVar(value=str(Path.home() / "Videos" / "converted"))
        ttk.Entry(top, textvariable=self.out_var).grid(row=2, column=1, sticky="ew", padx=8, pady=(10, 0))
        ttk.Button(top, text="Вибрати", command=self.pick_output).grid(row=2, column=2, padx=4, pady=(10, 0))
        ttk.Button(top, text="Відкрити папку", command=self.open_output_folder).grid(row=2, column=3, padx=4, pady=(10, 0))

        top.columnconfigure(1, weight=1)

        opts = ttk.LabelFrame(self, text="Налаштування конвертації", padding=12)
        opts.pack(fill="x", padx=12, pady=(0, 10))

        ttk.Label(opts, text="Відео → формат:").grid(row=0, column=0, sticky="w")
        self.out_video_fmt_var = tk.StringVar(value="mp4")
        ttk.Combobox(opts, textvariable=self.out_video_fmt_var, values=OUT_VIDEO_FORMATS, state="readonly", width=10)\
            .grid(row=0, column=1, sticky="w", padx=(8, 18))

        ttk.Label(opts, text="CRF:").grid(row=0, column=2, sticky="w")
        self.crf_var = tk.IntVar(value=23)
        ttk.Spinbox(opts, from_=14, to=35, textvariable=self.crf_var, width=6)\
            .grid(row=0, column=3, sticky="w", padx=(8, 18))

        ttk.Label(opts, text="Preset:").grid(row=0, column=4, sticky="w")
        self.preset_var = tk.StringVar(value="medium")
        ttk.Combobox(
            opts,
            textvariable=self.preset_var,
            values=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            state="readonly",
            width=10,
        ).grid(row=0, column=5, sticky="w", padx=(8, 0))

        # NEW: Portrait mode
        ttk.Label(opts, text="Зробити вертикальним:").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.portrait_var = tk.StringVar(value="Вимкнено")
        ttk.Combobox(
            opts,
            textvariable=self.portrait_var,
            values=list(PORTRAIT_PRESETS.keys()),
            state="readonly",
            width=26,
        ).grid(row=1, column=1, sticky="w", padx=(8, 18), pady=(10, 0))
        ttk.Label(opts, text="(тільки для відео)").grid(row=1, column=2, sticky="w", pady=(10, 0))

        ttk.Label(opts, text="Фото → формат:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.out_image_fmt_var = tk.StringVar(value="jpg")
        ttk.Combobox(opts, textvariable=self.out_image_fmt_var, values=OUT_IMAGE_FORMATS, state="readonly", width=10)\
            .grid(row=2, column=1, sticky="w", padx=(8, 18), pady=(10, 0))

        ttk.Label(opts, text="Якість фото (1–100):").grid(row=2, column=2, sticky="w", pady=(10, 0))
        self.img_quality_var = tk.IntVar(value=90)
        ttk.Spinbox(opts, from_=1, to=100, textvariable=self.img_quality_var, width=6)\
            .grid(row=2, column=3, sticky="w", padx=(8, 18), pady=(10, 0))

        self.overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="Перезаписувати існуючі файли", variable=self.overwrite_var)\
            .grid(row=3, column=0, columnspan=3, sticky="w", pady=(10, 0))

        self.fast_copy_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="Швидко для відео (copy без перекодування, якщо можливо)", variable=self.fast_copy_var)\
            .grid(row=3, column=3, columnspan=3, sticky="w", pady=(10, 0))

        mid = ttk.Frame(self, padding=(12, 0, 12, 12))
        mid.pack(fill="both", expand=True)

        left = ttk.LabelFrame(mid, text="Черга файлів", padding=8)
        left.pack(side="left", fill="both", expand=True)

        self.listbox = tk.Listbox(left, height=14, selectmode=tk.EXTENDED)
        self.listbox.pack(fill="both", expand=True, padx=4, pady=4)

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(6, 0))
        ttk.Button(btns, text="Очистити", command=self.clear_list).pack(side="left")
        ttk.Button(btns, text="Видалити вибране", command=self.remove_selected).pack(side="left", padx=8)
        ttk.Button(btns, text="Додати ще файли", command=self.pick_files).pack(side="left")

        right = ttk.LabelFrame(mid, text="Статус", padding=10)
        right.pack(side="right", fill="both", expand=True, padx=(12, 0))

        self.status_var = tk.StringVar(value="Готово")
        ttk.Label(right, textvariable=self.status_var, wraplength=380).pack(anchor="w")

        self.progress = ttk.Progressbar(right, mode="determinate")
        self.progress.pack(fill="x", pady=(12, 6))

        self.progress_var = tk.StringVar(value="0 / 0")
        ttk.Label(right, textvariable=self.progress_var).pack(anchor="w")

        controls = ttk.Frame(right)
        controls.pack(fill="x", pady=(12, 0))
        self.btn_start = ttk.Button(controls, text="▶ Старт", command=self.start)
        self.btn_start.pack(side="left")
        self.btn_stop = ttk.Button(controls, text="■ Стоп", command=self.stop, state="disabled")
        self.btn_stop.pack(side="left", padx=8)

        log_frame = ttk.LabelFrame(self, text="Лог", padding=10)
        log_frame.pack(fill="both", expand=False, padx=12, pady=(0, 12))

        self.log_text = tk.Text(log_frame, height=9, wrap="word")
        self.log_text.pack(fill="both", expand=True)
        self.log_text.tag_configure("INFO", foreground="#1f6feb")
        self.log_text.tag_configure("OK", foreground="#2da44e")
        self.log_text.tag_configure("WARN", foreground="#bf8700")
        self.log_text.tag_configure("ERROR", foreground="#cf222e")

    # ---------------- Logging ----------------
    def _log(self, level: str, msg: str):
        self.log_text.insert("end", f"[{level}] {msg}\n", level)
        self.log_text.see("end")

    def _queue_log(self, level: str, msg: str):
        self.ui_queue.put((level, msg))

    def _poll_queue(self):
        try:
            while True:
                level, msg = self.ui_queue.get_nowait()
                self._log(level, msg)
        except queue.Empty:
            pass
        self.after(120, self._poll_queue)

    # ---------------- Listbox numbering ----------------
    def refresh_listbox(self):
        self.listbox.delete(0, "end")
        for i, (p, t) in enumerate(self.tasks, start=1):
            tag = "🎬" if t == "video" else "🖼️"
            self.listbox.insert("end", f"{i}. {tag} {p.name}")

    # ---------------- FFmpeg ----------------
    def pick_ffmpeg(self):
        path = filedialog.askopenfilename(
            title="Вибери ffmpeg.exe",
            filetypes=[("ffmpeg", "ffmpeg.exe"), ("All files", "*.*")]
        )
        if not path:
            return
        self.ffmpeg_path = path
        self.ffmpeg_var.set(path)
        self._log("OK", f"FFmpeg задано вручну: {path}")

    def check_ffmpeg(self):
        p = self.ffmpeg_var.get().strip()
        if p:
            self.ffmpeg_path = p
        if not self.ffmpeg_path:
            messagebox.showerror("FFmpeg", "FFmpeg не задано. Натисни 'Вказати ffmpeg.exe'.")
            return
        try:
            r = subprocess.run([self.ffmpeg_path, "-version"], capture_output=True, text=True)
            if r.returncode == 0:
                first_line = (r.stdout.splitlines() or [""])[0]
                self._log("OK", f"FFmpeg працює: {first_line}")
            else:
                self._log("ERROR", "FFmpeg не запускається. Перевір шлях до ffmpeg.exe")
        except Exception as e:
            self._log("ERROR", f"Помилка перевірки FFmpeg: {e}")

    # ---------------- Picking ----------------
    def pick_folder(self):
        folder = filedialog.askdirectory(title="Вибери папку з медіа (фото/відео)")
        if not folder:
            return
        self.src_var.set(folder)
        self.load_media_from_folder(Path(folder))

    def pick_files(self):
        paths = filedialog.askopenfilenames(
            title="Вибери файли (фото/відео)",
            filetypes=[
                ("Media", "*.mov *.mp4 *.mkv *.webm *.avi *.m4v *.flv *.wmv *.mts *.m2ts "
                          "*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.heic *.heif"),
                ("All files", "*.*")
            ],
        )
        if not paths:
            return
        self.add_files([Path(p) for p in paths])

    def pick_output(self):
        folder = filedialog.askdirectory(title="Вибери папку виводу")
        if folder:
            self.out_var.set(folder)

    def open_output_folder(self):
        out = Path(self.out_var.get()).expanduser()
        out.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            os.startfile(str(out))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.run(["open", str(out)], check=False)
        else:
            subprocess.run(["xdg-open", str(out)], check=False)

    def load_media_from_folder(self, folder: Path):
        if not folder.exists():
            messagebox.showerror("Помилка", "Папка не існує.")
            return
        files = [p for p in folder.rglob("*") if p.is_file()]
        self.add_files(files)

    def add_files(self, files: List[Path]):
        added = 0
        skipped = 0
        existing = {p.resolve() for p, _ in self.tasks}

        for f in files:
            if not f.exists() or not f.is_file():
                continue
            t = media_type(f)
            if t is None:
                skipped += 1
                continue
            r = f.resolve()
            if r in existing:
                continue
            self.tasks.append((f, t))
            existing.add(r)
            added += 1

        self.refresh_listbox()
        if added:
            self._queue_log("INFO", f"Додано: {added}. Всього: {len(self.tasks)}")
        if skipped:
            self._queue_log("WARN", f"Пропущено (непідтримувані розширення): {skipped}")
        self._update_progress(0, len(self.tasks))

    # ---------------- Queue ops ----------------
    def clear_list(self):
        self.tasks.clear()
        self.refresh_listbox()
        self._update_progress(0, 0)

    def remove_selected(self):
        sel = list(self.listbox.curselection())
        if not sel:
            return
        for idx in reversed(sel):
            del self.tasks[idx]
        self.refresh_listbox()
        self._update_progress(0, len(self.tasks))

    def _update_progress(self, done: int, total: int):
        self.progress["maximum"] = max(total, 1)
        self.progress["value"] = done
        self.progress_var.set(f"{done} / {total}")

    # ---------------- Video portrait filters ----------------
    def _portrait_filter(self) -> Optional[str]:
        preset = PORTRAIT_PRESETS.get(self.portrait_var.get(), None)
        if not preset:
            return None

        mode, w, h = preset

        # If input already portrait, scale will keep it OK.
        if mode == "crop":
            # Center-crop to 9:16 and scale to target
            # 1) scale so that one side fits, then crop center, then scale final
            return f"scale='if(gt(a,9/16),-2,{w})':'if(gt(a,9/16),{h},-2)',crop={w}:{h},setsar=1"
        else:
            # blur background fill: create blurred bg, overlay original scaled to fit
            # 1) bg: scale to fill, blur
            # 2) fg: scale to fit
            # 3) overlay center
            return (
                f"[0:v]scale={w}:{h}:force_original_aspect_ratio=increase,boxblur=20:1,crop={w}:{h}[bg];"
                f"[0:v]scale={w}:{h}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1"
            )

    # ---------------- Commands ----------------
    def _build_cmd_video(self, inp: Path, outp: Path) -> List[str]:
        overwrite = "-y" if self.overwrite_var.get() else "-n"

        # Portrait filter disables stream copy (because we need re-encode)
        portrait_vf = self._portrait_filter()
        can_stream_copy = self.fast_copy_var.get() and portrait_vf is None and outp.suffix.lower() != ".gif"

        if can_stream_copy:
            return [
                self.ffmpeg_path, overwrite,
                "-i", str(inp),
                "-map", "0",
                "-c", "copy",
                "-movflags", "+faststart",
                str(outp),
            ]

        crf = int(self.crf_var.get())
        preset = (self.preset_var.get() or "medium").strip()

        # GIF output
        if outp.suffix.lower() == ".gif":
            vf = "fps=12,scale=640:-1:flags=lanczos"
            if portrait_vf:
                vf = f"{portrait_vf},{vf}" if "[" not in portrait_vf else portrait_vf  # complex filter handles itself
            if portrait_vf and "[" in portrait_vf:
                return [self.ffmpeg_path, overwrite, "-i", str(inp), "-filter_complex", portrait_vf, "-vf", "fps=12,scale=640:-1:flags=lanczos", str(outp)]
            return [self.ffmpeg_path, overwrite, "-i", str(inp), "-vf", vf, str(outp)]

        # WEBM (VP9) path
        if outp.suffix.lower() == ".webm":
            cmd = [self.ffmpeg_path, overwrite, "-i", str(inp)]
            if portrait_vf:
                if "[" in portrait_vf:
                    cmd += ["-filter_complex", portrait_vf]
                else:
                    cmd += ["-vf", portrait_vf]
            cmd += ["-c:v", "libvpx-vp9", "-crf", str(crf), "-b:v", "0", "-c:a", "libopus", str(outp)]
            return cmd

        # Default H.264 + AAC
        cmd = [self.ffmpeg_path, overwrite, "-i", str(inp)]
        if portrait_vf:
            if "[" in portrait_vf:
                cmd += ["-filter_complex", portrait_vf]
            else:
                cmd += ["-vf", portrait_vf]
        cmd += [
            "-map", "0:v:0?",
            "-map", "0:a:0?",
            "-c:v", "libx264",
            "-preset", preset,
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-movflags", "+faststart",
            str(outp),
        ]
        return cmd

    def _build_cmd_image(self, inp: Path, outp: Path) -> List[str]:
        overwrite = "-y" if self.overwrite_var.get() else "-n"
        q = int(self.img_quality_var.get())
        ext = outp.suffix.lower()

        if ext in {".jpg", ".jpeg"}:
            qv = max(2, min(31, int(round(31 - (q / 100) * 29))))
            return [self.ffmpeg_path, overwrite, "-i", str(inp), "-q:v", str(qv), str(outp)]

        if ext == ".webp":
            return [self.ffmpeg_path, overwrite, "-i", str(inp), "-q:v", str(max(0, min(100, q))), str(outp)]

        return [self.ffmpeg_path, overwrite, "-i", str(inp), str(outp)]

    # ---------------- Worker ----------------
    def start(self):
        if self.worker_thread and self.worker_thread.is_alive():
            return

        entry_path = self.ffmpeg_var.get().strip()
        if entry_path:
            self.ffmpeg_path = entry_path

        if not self.ffmpeg_path:
            messagebox.showerror("FFmpeg", "FFmpeg не знайдено. Вкажи ffmpeg.exe або додай у PATH.")
            return

        if not self.tasks:
            messagebox.showinfo("Черга пуста", "Додай файли для конвертації.")
            return

        out_dir = Path(self.out_var.get()).expanduser()
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалося створити папку виводу:\n{e}")
            return

        self.stop_requested = False
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.status_var.set("Конвертація запущена...")

        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def stop(self):
        self.stop_requested = True
        self.status_var.set("Зупинка після поточного файлу...")

    def _worker(self):
        out_dir = Path(self.out_var.get()).expanduser()
        total = len(self.tasks)
        done = 0

        out_vid = (self.out_video_fmt_var.get().strip().lower() or "mp4")
        out_img = (self.out_image_fmt_var.get().strip().lower() or "jpg")

        portrait_name = self.portrait_var.get()
        if PORTRAIT_PRESETS.get(portrait_name):
            self._queue_log("INFO", f"Вертикалізація відео: {portrait_name}")

        self._queue_log("INFO", f"Старт. Файлів: {total}")
        self._queue_log("INFO", f"Відео → .{out_vid} | Фото → .{out_img}")
        self._update_progress(0, total)

        for inp, t in list(self.tasks):
            if self.stop_requested:
                self._queue_log("WARN", "Зупинено користувачем.")
                break

            if not inp.exists():
                self._queue_log("ERROR", f"Файл не знайдено: {inp}")
                done += 1
                self.after(0, lambda d=done, tot=total: self._update_progress(d, tot))
                continue

            out_ext = out_vid if t == "video" else out_img

            if self.overwrite_var.get():
                outp = out_dir / f"{inp.stem}.{out_ext}"
            else:
                outp = safe_output_name(out_dir, inp, out_ext)

            self.after(0, lambda name=inp.name: self.status_var.set(f"Обробка: {name}"))
            self._queue_log("INFO", f"→ {inp.name} ({t}) ==> {outp.name}")

            try:
                cmd = self._build_cmd_video(inp, outp) if t == "video" else self._build_cmd_image(inp, outp)

                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    universal_newlines=True,
                )

                assert proc.stderr is not None
                for line in proc.stderr:
                    line = line.strip()
                    if not line:
                        continue
                    low = line.lower()
                    if "error" in low or "invalid" in low or "failed" in low:
                        self._queue_log("WARN", line)

                rc = proc.wait()

                if rc == 0 and outp.exists():
                    self._queue_log("OK", f"Готово: {outp.name}")
                else:
                    self._queue_log("ERROR", f"Помилка конвертації: {inp.name} (код {rc})")

            except FileNotFoundError:
                self._queue_log("ERROR", "FFmpeg не знайдено під час запуску. Перевір шлях до ffmpeg.exe.")
                break
            except Exception as e:
                self._queue_log("ERROR", f"Несподівана помилка: {e}")

            done += 1
            self.after(0, lambda d=done, tot=total: self._update_progress(d, tot))

        self.after(0, self._finish)

    def _finish(self):
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.status_var.set("Зупинено." if self.stop_requested else "Готово ✅")

    def run(self):
        self.mainloop()


if __name__ == "__main__":
    try:
        if os.name == "nt":
            from ctypes import windll  # type: ignore
            windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass

    app = ConverterUI()
    app.run()
