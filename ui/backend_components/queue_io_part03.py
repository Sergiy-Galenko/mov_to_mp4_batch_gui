from __future__ import annotations

BODY = r'''            except Exception:
                pass
        saved = max(input_bytes - output_bytes, 0)
        speeds = [point.get("speed", 0.0) for point in self._speed_history if point.get("speed", 0.0) > 0]
        avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
        self._session_elapsed_text = format_time(elapsed)
        self._session_eta_text = format_time(total_eta) if total_eta is not None else self._session_eta_text
        self._session_avg_speed_text = f"{avg_speed:.1f}x" if avg_speed else "--"
        self._session_input_text = format_bytes(input_bytes)
        self._session_output_text = format_bytes(output_bytes)
        self._session_saved_text = format_bytes(saved)
        self.sessionStatsChanged.emit()

    def _refresh_codec_distribution(self) -> None:
        distribution: Dict[str, int] = {}
        for item in self.queue_model.items():
            info = self.media_info_cache.get(item.path) or item.probe_data
            codec = (info.vcodec if info else None) or "Unknown"
            codec = self._display_codec(codec)
            distribution[codec] = distribution.get(codec, 0) + 1
        self._codec_distribution = distribution
        self.codecDistributionChanged.emit(dict(self._codec_distribution))

    def _display_codec(self, codec: str) -> str:
        normalized = str(codec or "").lower()
        if normalized in {"h264", "libx264"}:
            return "H.264"
        if normalized in {"hevc", "h265", "libx265"}:
            return "H.265"
        if "av1" in normalized:
            return "AV1"
        if "vp9" in normalized:
            return "VP9"
        return codec or "Unknown"

    def _sample_resources(self) -> Dict[str, float]:
        cpu = 0.0
        ram = 0.0
        gpu = 0.0
        try:
            import psutil  # type: ignore

            cpu = float(psutil.cpu_percent(interval=None))
            ram = float(psutil.virtual_memory().percent)
        except Exception:
            pass
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=0.4,
            )
            if result.returncode == 0:
                values = [float(line.strip()) for line in result.stdout.splitlines() if line.strip()]
                if values:
                    gpu = max(values)
        except Exception:
            pass
        return {"cpu": cpu, "gpu": gpu, "ram": ram}

    def _append_resource_sample(self, now: float) -> None:
        if not self._run_started_monotonic:
            return
        sample = self._sample_resources()
        sample["time"] = now - self._run_started_monotonic
        self._resource_history.append(sample)
        self._resource_history = self._resource_history[-120:]
        self._cpu_load_text = f"CPU {sample['cpu']:.0f}%"
        self._gpu_load_text = f"GPU {sample['gpu']:.0f}%"
        self._ram_load_text = f"RAM {sample['ram']:.0f}%"
        self.resourceHistoryChanged.emit(list(self._resource_history))

    def _record_file_timing(self, path: Path, status: str) -> None:
        started = self._task_started_at.pop(path, None)
        if started is None:
            return
        duration = max(time.monotonic() - started, 0.0)
        name = path.name
        item = self.queue_model.item_by_path(path)
        self._file_timings = [item for item in self._file_timings if item.get("name") != name]
        self._file_timings.append(
            {
                "name": name,
                "duration": duration,
                "status": status,
                "compression": item.compression_ratio if item else 0.0,
                "predictedSize": item.predicted_output_bytes if item else 0,
            }
        )
        self._file_timings.sort(key=lambda item: float(item.get("duration") or 0), reverse=True)
        self._file_timings = self._file_timings[:10]
        self.fileTimingsChanged.emit(list(self._file_timings))
'''
