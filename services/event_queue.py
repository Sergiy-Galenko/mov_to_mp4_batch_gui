"""Collapse redundant progress updates without losing task transitions or logs."""

from queue import Queue


class UiEventQueue(Queue):
    @staticmethod
    def _progress_key(event: tuple) -> tuple | None:
        if event[0] == "progress":
            return ("progress",)
        if event[0] == "task_progress":
            return ("task_progress", event[1])
        if event[0] == "youtube_download_progress":
            return (event[0], event[1] if len(event) >= 7 else None)
        return None

    def _put(self, item: tuple) -> None:
        # Queue calls this with its mutex held. Never cross a non-progress event:
        # a terminal state must stay after the last progress for that task.
        key = self._progress_key(item)
        if key is not None and self.queue and self._progress_key(self.queue[-1]) == key:
            self.queue[-1] = item
            self.unfinished_tasks -= 1
        else:
            super()._put(item)
