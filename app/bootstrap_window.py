"""First-run progress before Qt itself is installed; falls back to the launch log."""

from __future__ import annotations

import queue
import sys
import threading
from pathlib import Path

from app.dependency_bootstrap import BootstrapCancelled, BootstrapProcess, PreparedRuntime, missing_runtime_dependencies, prepare_runtime


def run_bootstrap(path: Path, *, gui=True) -> PreparedRuntime:
    from app.dependency_bootstrap import bootstrap_enabled
    from app.paths import APP_DATA_DIR

    if not bootstrap_enabled() or not missing_runtime_dependencies(path):
        return prepare_runtime(path)
    window = None
    if gui:
        try:
            import tkinter as tk
            from tkinter import ttk

            window = tk.Tk()
        except (ImportError, RuntimeError):
            window = None
        except Exception:
            # A headless session may have tkinter installed but no display.
            window = None
    log_path = APP_DATA_DIR / "dependency-setup.log"
    with log_path.open("w", encoding="utf-8") as log:
        events = queue.Queue()

        def progress(line):
            log.write(line + "\n")
            log.flush()
            if window:
                events.put(("progress", line))
            elif sys.stderr:
                print(line, file=sys.stderr, flush=True)

        if window is None:
            return prepare_runtime(path, BootstrapProcess(progress))

        window.title("Media Converter — Підготовка / Setup")
        window.geometry("640x300")
        window.resizable(True, False)
        status = tk.StringVar(value="Завантаження необхідних бібліотек / Downloading required libraries…")
        ttk.Label(window, textvariable=status, wraplength=600).pack(padx=20, pady=20, fill="x")
        bar = ttk.Progressbar(window, mode="indeterminate")
        bar.pack(padx=20, fill="x")
        ttk.Label(window, text=f"Журнал / Log: {log_path}", wraplength=600).pack(padx=20, pady=12, fill="x")
        controls = ttk.Frame(window)
        controls.pack(padx=20, pady=12, fill="x")
        cancelled = threading.Event()
        outcome = {}
        worker = None

        def execute():
            try:
                events.put(("done", prepare_runtime(path, BootstrapProcess(progress, cancelled))))
            except Exception as exc:
                events.put(("error", exc))

        def start():
            nonlocal worker
            cancelled.clear()
            retry.configure(state="disabled")
            cancel.configure(state="normal")
            bar.start()
            worker = threading.Thread(target=execute, daemon=True)
            worker.start()

        def close():
            cancelled.set()
            cancel.configure(state="disabled")
            if worker and worker.is_alive():
                status.set("Скасування… / Cancelling…")
            else:
                outcome["error"] = BootstrapCancelled("Library installation cancelled")
                window.destroy()

        def poll():
            while not events.empty():
                kind, value = events.get_nowait()
                if kind == "progress":
                    status.set(value[-500:])
                elif kind == "done":
                    outcome["result"] = value
                    window.destroy()
                    return
                else:
                    bar.stop()
                    if cancelled.is_set():
                        outcome["error"] = value
                        window.destroy()
                        return
                    status.set("Не вдалося встановити / Installation failed:\n" + str(value)[-400:])
                    retry.configure(state="normal")
            window.after(100, poll)

        retry = ttk.Button(controls, text="Повторити / Retry", command=start)
        retry.pack(side="left")
        cancel = ttk.Button(controls, text="Скасувати / Cancel", command=close)
        cancel.pack(side="right")
        window.protocol("WM_DELETE_WINDOW", close)
        start()
        window.after(100, poll)
        window.mainloop()
        if worker:
            worker.join(timeout=10)
        if "error" in outcome:
            raise outcome["error"]
        return outcome["result"]
