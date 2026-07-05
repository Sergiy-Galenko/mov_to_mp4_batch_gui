from __future__ import annotations

BODY = r'''            skipped = sum(1 for item in results if item.get("status") == TaskStatus.SKIPPED)
            cancelled = sum(1 for item in results if item.get("status") == TaskStatus.CANCELLED)
            lines.append(
                f"{started_at} | {entry.get('operation', '—')} | файлів {entry.get('total_files', 0)} | "
                f"failed {failed} | skipped {skipped} | cancelled {cancelled} | {entry.get('output_dir', '—')}"
            )
        return "\n".join(lines)

    @QtCore.Property(int, notify=queueStatsChanged)
    def queueCount(self) -> int:
        return len(self.queue_model.items())

    @QtCore.Property(int, notify=queueStatsChanged)
    def completedCount(self) -> int:
        return sum(1 for item in self.queue_model.items() if item.status in {TaskStatus.SUCCESS, TaskStatus.SKIPPED})

    @QtCore.Property(int, notify=queueStatsChanged)
    def failedCount(self) -> int:
        return sum(1 for item in self.queue_model.items() if item.status == TaskStatus.FAILED)

    @QtCore.Property(int, notify=queueStatsChanged)
    def skippedCount(self) -> int:
        return sum(1 for item in self.queue_model.items() if item.status == TaskStatus.SKIPPED)

    @QtCore.Property(int, notify=queueStatsChanged)
    def runningCount(self) -> int:
        return sum(1 for item in self.queue_model.items() if item.status in {TaskStatus.RUNNING, TaskStatus.PAUSED})

    @QtCore.Property(int, notify=queueStatsChanged)
    def cancelledCount(self) -> int:
        return sum(1 for item in self.queue_model.items() if item.status == TaskStatus.CANCELLED)

    @QtCore.Property("QVariantList", notify=speedHistoryChanged)
    def speedHistory(self) -> List[Dict[str, float]]:
        return list(self._speed_history)

    @QtCore.Property("QVariantList", notify=fileTimingsChanged)
    def fileTimings(self) -> List[Dict[str, Any]]:
        return list(self._file_timings)

    @QtCore.Property("QVariantMap", notify=codecDistributionChanged)
    def codecDistribution(self) -> Dict[str, int]:
        return dict(self._codec_distribution)

    @QtCore.Property("QVariantList", notify=resourceHistoryChanged)
    def resourceHistory(self) -> List[Dict[str, float]]:
        return list(self._resource_history)

    @QtCore.Property(str, notify=resourceHistoryChanged)
    def cpuLoadText(self) -> str:
        return self._cpu_load_text

    @QtCore.Property(str, notify=resourceHistoryChanged)
    def gpuLoadText(self) -> str:
        return self._gpu_load_text

    @QtCore.Property(str, notify=resourceHistoryChanged)
    def ramLoadText(self) -> str:
        return self._ram_load_text

    @QtCore.Property(str, notify=sessionStatsChanged)
    def sessionElapsedText(self) -> str:
        return self._session_elapsed_text

    @QtCore.Property(str, notify=sessionStatsChanged)
    def sessionEtaText(self) -> str:
        return self._session_eta_text

    @QtCore.Property(str, notify=sessionStatsChanged)
    def sessionAvgSpeedText(self) -> str:
        return self._session_avg_speed_text

    @QtCore.Property(str, notify=sessionStatsChanged)
    def sessionInputText(self) -> str:
        return self._session_input_text

    @QtCore.Property(str, notify=sessionStatsChanged)
    def sessionOutputText(self) -> str:
        return self._session_output_text

    @QtCore.Property(str, notify=sessionStatsChanged)
    def sessionSavedText(self) -> str:
        return self._session_saved_text
'''
