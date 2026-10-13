# Resource planning and media processing

The application keeps Python/Qt for orchestration and uses FFmpeg for media processing. `services/adaptive_scheduler.py` now handles admission separately from the converter. Both sequential and parallel tasks use the same resource monitor.

## Admission budgets

A conversion batch reserves CPU thread tokens, estimated working memory, hardware encoding sessions, and disk slots before starting a task. The defaults allow at most two disk-intensive tasks and two hardware sessions at once, within the user's concurrency limit. Thumbnail/subtitle extraction costs less than video conversion; video memory estimates scale with pixel count; transcription has a larger memory estimate. The scheduler checks live available RAM and known CPU/GPU load before admission. Tasks wait without occupying a reservation during pause; cancellation/skip interrupts waiting. Completion and failures release the reservation.

Memory costs are heuristics, capped to the batch memory budget, not hard OS memory limits or model-specific guarantees. Disk slots are conservative global limits, not per-device throughput measurements. Reservations do not preempt an already running task when resource pressure rises. Transcription, merge, and chapter splitting retain their existing sequential execution rules. Merge processing retains its existing execution path.

Parallel FFmpeg commands bound input decoder threads, filter threads, and output encoder threads. x265 pools and SVT-AV1 logical processors receive explicit limits too. These are per-stage thread limits, not an OS CPU percentage quota. The UI concurrency setting remains an upper bound; resource budgets can reduce actual concurrency.

## Hardware and telemetry

`discover_encoders` is the common inventory implementation for `HardwareService`, `FfmpegService`, and startup system profiling. Hardware is advertised as usable only after a one-frame encode with the production pixel format succeeds. VideoToolbox forbids software substitution. Failed driver initialization excludes the encoder; conversion retains the existing runtime CPU fallback for failures with actual input.

Linux VA-API probes use a render node and `format=nv12,hwupload`. Verified VA-API encoders appear in the inventory. Automatic rendering selection is intentionally limited to the existing VideoToolbox/NVENC/QSV/AMF pipelines: a VA-API rendering path must handle device selection and hardware filter uploads before it can be enabled.

NVIDIA utilization is collected when `nvidia-smi` is available. GPU utilization remains `None` when the tool or reading is unavailable, including Apple/Intel/AMD systems without a telemetry provider. The UI shows an em dash and the chart leaves a gap. Unknown GPU telemetry does not prevent conversion; conservative hardware-session limits still apply. Idle scheduling requires a known CPU reading and uses GPU readings when available.

## Stream decisions and frames

Stream copying requires source probe data, compatible codecs, and no video filters or target-size constraint. Explicit Fast Copy permits remuxing across containers. Smart Convert still checks its selected video codec. Compatible video can be copied while audio is encoded for an incompatible container or an audio filter. Missing audio codec information prevents blindly copying an advertised audio stream. Cross-container subtitle copying is refused when compatibility cannot be established from the available metadata.

Blur and reframe analysis sample lossless RGB frames through FFmpeg's PPM pipe, processing one frame at a time without temporary JPEG files. Each frame is capped at 64 MiB; the producer has a deadline and is reaped when the generator is closed. OpenCV classifiers are reused. The existing fallback detectors and smoothing behavior remain. This change does not replace the existing average-box blur / average-position crop rendering with per-frame motion tracking.

## Measurement

Run the repeatable microbenchmarks:

```sh
.venv/bin/python scripts/profile_pipeline.py --repeats 5
.venv/bin/python scripts/profile_pipeline.py --video /path/to/video.mov --ffmpeg /path/to/ffmpeg
```

JSON output includes median elapsed time and Python-tracked peak memory. FFmpeg processes, native allocations, GPU memory, and OS file caches are outside `tracemalloc` measurements. Results should be compared on the same machine with representative files.

On the development macOS ARM64 environment, a three-repeat synthetic run measured approximately 69 ms for Python RTF encoding versus 5.8 ms for the existing Rust implementation, and 124 ms for Python PDF-literal decoding versus 0.38 ms for Rust. These are microbenchmarks of existing kernels, not whole-application speedups. No additional Rust migration is justified by these measurements; the optional extension and Python fallback remain intact.

Real FFmpeg integration can be enabled without changing application settings:

```sh
MEDIA_CONVERTER_TEST_FFMPEG=/path/to/ffmpeg .venv/bin/python -m pytest tests/test_adaptive_pipeline.py
```

The integration test creates disposable media, streams sampled frames, converts MOV/PCM to MP4/AAC with video copying, decodes the result, and closes a producer early. Windows/Linux/GPU-specific execution still needs testing on those systems; mocked inventory tests verify platform decisions but do not prove driver compatibility.
