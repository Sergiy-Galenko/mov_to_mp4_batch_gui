from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from core.models import TASK_STATUSES, TaskItem, TaskStatus
from utils.files import file_sha256, media_type


class QueueManager:
    def serialize_task(self, item: TaskItem) -> Dict[str, Any]:
        return {
            "path": str(item.path),
            "media_type": item.media_type,
            "status": item.status,
            "last_error": item.last_error,
            "exit_code": item.exit_code,
            "attempts": item.attempts,
            "last_output": item.last_output,
            "preview_output": item.preview_output,
            "duration_text": item.duration_text,
            "size_text": item.size_text,
            "thumbnail_path": item.thumbnail_path,
            "content_hash": item.content_hash,
            "progress": item.progress,
            "eta_text": item.eta_text,
            "speed_text": item.speed_text,
            "elapsed_seconds": item.elapsed_seconds,
            "overrides": dict(item.overrides),
        }

    def deserialize_tasks(self, payload: Any, *, pending_recovery: bool = False) -> List[TaskItem]:
        if not isinstance(payload, list):
            return []
        items: List[TaskItem] = []
        for raw in payload:
            if not isinstance(raw, dict):
                continue
            path_value = str(raw.get("path") or "").strip()
            media_kind = str(raw.get("media_type") or "").strip()
            if not path_value or not media_kind:
                continue
            status = str(raw.get("status") or TaskStatus.QUEUED)
            if status not in TASK_STATUSES:
                status = TaskStatus.QUEUED
            if pending_recovery and status in {TaskStatus.ANALYZING, TaskStatus.RUNNING, TaskStatus.PAUSED}:
                status = TaskStatus.QUEUED
            items.append(
                TaskItem(
                    path=Path(path_value).expanduser(),
                    media_type=media_kind,
                    status=status,
                    last_error=str(raw.get("last_error") or ""),
                    exit_code=raw.get("exit_code"),
                    attempts=int(raw.get("attempts") or 0),
                    last_output=str(raw.get("last_output") or ""),
                    preview_output=str(raw.get("preview_output") or ""),
                    duration_text=str(raw.get("duration_text") or "—"),
                    size_text=str(raw.get("size_text") or "—"),
                    thumbnail_path=str(raw.get("thumbnail_path") or ""),
                    content_hash=str(raw.get("content_hash") or ""),
                    progress=float(raw.get("progress") or 0.0),
                    eta_text=str(raw.get("eta_text") or ""),
                    speed_text=str(raw.get("speed_text") or ""),
                    elapsed_seconds=float(raw.get("elapsed_seconds") or 0.0),
                    overrides=dict(raw.get("overrides") or {}),
                )
            )
        return items

    def build_items(self, paths: Iterable[Path], existing: Iterable[Path]) -> Tuple[List[TaskItem], int, int]:
        existing_paths = {path.expanduser().resolve() for path in existing}
        added: List[TaskItem] = []
        duplicate_count = 0
        unsupported_count = 0
        for raw_path in paths:
            path = raw_path.expanduser()
            kind = media_type(path)
            if not kind:
                unsupported_count += 1
                continue
            try:
                resolved = path.resolve()
            except Exception:
                resolved = path
            if resolved in existing_paths or any(item.path == resolved for item in added):
                duplicate_count += 1
                continue
            added.append(TaskItem(path=resolved, media_type=kind))
        return added, duplicate_count, unsupported_count

    def deduplicate_by_path(self, items: Sequence[TaskItem]) -> Tuple[List[TaskItem], int]:
        seen: set[Path] = set()
        unique: List[TaskItem] = []
        removed = 0
        for item in items:
            if item.path in seen:
                removed += 1
                continue
            seen.add(item.path)
            unique.append(item)
        return unique, removed

    def deduplicate_by_hash(self, items: Sequence[TaskItem]) -> Tuple[List[TaskItem], int, List[str]]:
        seen: Dict[tuple[int, str], TaskItem] = {}
        unique: List[TaskItem] = []
        removed = 0
        log_lines: List[str] = []
        for item in items:
            try:
                size = item.path.stat().st_size
            except Exception:
                unique.append(item)
                continue
            if not item.content_hash and item.path.exists():
                try:
                    item.content_hash = file_sha256(item.path)
                except Exception as exc:
                    log_lines.append(f"Не вдалося порахувати hash для {item.path.name}: {exc}")
                    unique.append(item)
                    continue
            key = (size, item.content_hash)
            if item.content_hash and key in seen:
                removed += 1
                log_lines.append(f"Hash duplicate: {item.path.name} == {seen[key].path.name}")
                continue
            if item.content_hash:
                seen[key] = item
            unique.append(item)
        return unique, removed, log_lines

    def paths_from_payload(self, paths: Iterable[Any]) -> set[Path]:
        normalized: set[Path] = set()
        for value in paths:
            text = str(value or "").strip()
            if text:
                normalized.add(Path(text).expanduser())
        return normalized

    def reorder(self, items: Sequence[TaskItem], indices: Iterable[int], direction: str) -> List[TaskItem]:
        result = list(items)
        selected = sorted({idx for idx in indices if 0 <= idx < len(result)})
        if not selected:
            return result
        if direction == "up":
            for idx in selected:
                if idx > 0 and idx - 1 not in selected:
                    result[idx - 1], result[idx] = result[idx], result[idx - 1]
        elif direction == "down":
            for idx in reversed(selected):
                if idx < len(result) - 1 and idx + 1 not in selected:
                    result[idx + 1], result[idx] = result[idx], result[idx + 1]
        elif direction == "top":
            moved = [result[idx] for idx in selected]
            rest = [item for idx, item in enumerate(result) if idx not in selected]
            result = moved + rest
        elif direction == "bottom":
            moved = [result[idx] for idx in selected]
            rest = [item for idx, item in enumerate(result) if idx not in selected]
            result = rest + moved
        return result

    def remove_indices(self, items: Sequence[TaskItem], indices: Iterable[int]) -> Tuple[List[TaskItem], int]:
        selected = {idx for idx in indices if 0 <= idx < len(items)}
        if not selected:
            return list(items), 0
        return [item for idx, item in enumerate(items) if idx not in selected], len(selected)

    def remove_paths(self, items: Sequence[TaskItem], paths: Iterable[Path]) -> Tuple[List[TaskItem], int]:
        selected = {path.expanduser() for path in paths}
        removed = 0
        kept: List[TaskItem] = []
        for item in items:
            if item.path in selected:
                removed += 1
            else:
                kept.append(item)
        return kept, removed

    def selected_indices_for_paths(self, items: Sequence[TaskItem], paths: Iterable[Path]) -> List[int]:
        selected = {path.expanduser() for path in paths}
        return [idx for idx, item in enumerate(items) if item.path in selected]

    def move_path_to_index(self, items: Sequence[TaskItem], path: Path, target_index: int) -> List[TaskItem]:
        result = list(items)
        source_index: Optional[int] = None
        for idx, item in enumerate(result):
            if item.path == path.expanduser():
                source_index = idx
                break
        if source_index is None:
            return result
        item = result.pop(source_index)
        target = max(0, min(target_index, len(result)))
        result.insert(target, item)
        return result
