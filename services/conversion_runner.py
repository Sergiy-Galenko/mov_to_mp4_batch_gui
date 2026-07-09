from __future__ import annotations

from pathlib import Path

from app.models import ConversionSettings, TaskItem
from services.converter_service import ConverterService


class ConversionRunner:
    def __init__(self, converter: ConverterService) -> None:
        self.converter = converter

    @property
    def is_running(self) -> bool:
        return bool(self.converter.thread and self.converter.thread.is_alive())

    def start(self, tasks: list[TaskItem], settings: ConversionSettings, out_dir: Path) -> None:
        self.converter.start(tasks, settings, out_dir)

    def stop(self) -> None:
        self.converter.stop()

    def pause(self) -> None:
        self.converter.pause()

    def resume(self) -> None:
        self.converter.resume()

    def skip_current(self) -> None:
        self.converter.skip_current()
