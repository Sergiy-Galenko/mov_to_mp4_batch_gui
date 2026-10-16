# Reliable processing, cache and packaged validation

## Shared media cache

`CacheManager` stores thumbnails, preview strips, waveforms, snapshots, proxies and probe metadata below the application data directory's `cache` folder. Source identity includes the resolved path, size, nanosecond modification/change times and inode. Keys additionally include the artifact namespace, rendering parameters, schema and tool identity. Changing a source at the same path or changing dimensions/colors invalidates the appropriate artifact. In-memory probe metadata carries the same source identity.

The default artifact quota is 2 GiB with 30 days of inactivity. Constructors accept different limits. Cleanup evicts least-recently-used entries and removes expired entries. Active reader leases and the artifact being returned are protected: the quota can temporarily be exceeded by protected entries. A single artifact larger than the quota is rejected. Cleanup never deletes source files or unregistered files. The cache's SQLite index and lock files are outside the artifact byte quota.

Each key has a cross-process producer lock. Producers write a unique partial file, verify success and a nonempty result, check that the source did not change, then atomically replace the destination. Failed producers never register a hit. Stale partial files older than one hour are removed. Proxies used by a live montage service retain reader leases until that service closes; master/proxy mappings survive application restarts.

The system details dialog includes asynchronous cache clearing and diagnostic export. Cached previews may need to be regenerated after clearing. Legacy cache directories from earlier versions are left untouched.

## Durable tasks and calibration

Queue items now have UUID identities that survive serialization and creation of conversion-run tasks. The task journal uses short SQLite transactions and publication checkpoints. Batch preparation records task inputs/settings before worker admission. Recovery checks source/output filesystem identities and output size, rather than treating a file at the destination as proof of completion.

A normal output published before an application crash can be recovered as complete. If required post-processing was interrupted, recovery preserves the result and exposes a failure requiring attention. Merge/chapter tasks do not infer whole-task completion from publication of just one output. Changed or missing results are queued again; collision policy remains in effect. Recovery verifies filesystem identity, not a full content hash or a full media decode.

Task and workload databases use WAL and restrictive file permissions where supported. Up to 10,000 completed journal tasks, 2,000 recent transitions, 30 workload samples per profile and 3,000 workload samples overall are retained; queued/incomplete journal tasks are preserved. Profiles distinguish machine architecture/CPU count, tool identity, operation, codec, resolution class, source frame rate/pixel format, thread budget and selected processing settings.

Successful single-pass FFmpeg runs and managed transcription workers sample process RSS. Multi-pass phases and A/B samples do not train timing estimates. Three valid samples are required before applying measurements. Memory admission uses an upper quantile plus 25% headroom, and early ETA uses the median elapsed/media-duration ratio until current progress provides a useful speed reading. Paused, failed and cancelled runs do not train the timing model. Estimates retain conservative initial heuristics; they are not hard OS memory/CPU quotas. Large jobs can reserve the memory budget exclusively when live available memory permits them. Speech admission estimates account for model class and audio duration.

## Hardware frame paths

Linux VA-API is available explicitly and in automatic selection after encoder probing succeeds. Compatible 8-bit H.264/HEVC/VP9/AV1/MPEG-2 inputs with no rotation/HDR processing can use hardware decode and supported GPU scaling for CUDA/NVENC, QSV and VA-API. Unsupported filters stay on the CPU; VA-API adds an explicit upload before encoding, including the output of complex graphs. VideoToolbox and AMF keep their existing verified encoding paths.

CPU fallback removes device/decode options, converts supported hardware scalers into software scale filters, removes upload requirements and restores software pixel formats. Actual decode/profile/device compatibility is still determined at runtime. The common encoder probe verifies an encode, not every possible input format or driver.

See [FFmpeg device/decode options](https://www.ffmpeg.org/ffmpeg.html) and [FFmpeg hardware filters](https://www.ffmpeg.org/ffmpeg-filters.html). Hardware-specific tests still need real Linux render nodes, NVIDIA GPUs and Intel QSV hardware; mocked command tests do not establish driver compatibility.

## Packaged application checks

The shipped entry point supports:

```sh
MediaConverter --self-test --report package-smoke.json
python scripts/verify_package.py dist/MediaConverter/MediaConverter --report package-smoke.json
```

Self-tests establish a disposable portable directory before importing application services, load the actual QML, import a generated video, verify FFprobe metadata, convert/decode a result, exercise pause/resume, then cancel and check partial-file cleanup. They do not use the user's presets, queue, models or output folder. The verifier removes external tool overrides so a missing bundled executable cannot be masked by a system installation. Source-only smoke runs may opt into `--allow-missing-ffprobe`; the package verifier requires all checks.

CI builds and behavior-tests portable packages on Linux, macOS and Windows, then uploads the package, smoke JSON and benchmark reports. This is headless functional validation; native dialogs, GPU drivers and release signing/notarization still require their own environment.

## Repeatable benchmarks and regression gating

```sh
python scripts/performance_suite.py --ffmpeg /path/to/ffmpeg --report performance.json --repeats 3
python scripts/performance_suite.py --ffmpeg /path/to/ffmpeg --write-baseline baseline.json
python scripts/performance_suite.py --ffmpeg /path/to/ffmpeg --baseline baseline.json --max-regression 1.5
```

The suite measures a deterministic 4K encode and process peak RSS, importing 10,000 queue rows, 1,000 progress updates, cold/warm previews, warm waveforms and actual QML startup in isolated subprocesses. Speech benchmarking is opt-in:

```sh
python scripts/performance_suite.py --ffmpeg /path/to/ffmpeg --speech-audio /path/to/speech.wav --speech-model tiny
```

It requires an already installed runtime and downloaded model and never automatically downloads a model. Missing speech input is explicitly recorded as skipped. No source paths or audio contents are included in the JSON report.

Baseline comparison requires matching machine/tool/workload schema. Pull-request CI runs the base revision on the same runner using a disposable worktree and fails when a comparable metric exceeds 1.5 times its baseline. On first introduction of the benchmark or a changed environment/schema, CI records an unavailable/incompatible baseline instead of inventing a comparison. Hardware contention can affect timings; repeated medians and the threshold reduce noise but do not eliminate it.

## Private support reports

Diagnostic export includes application/Python/Qt/tool versions, OS/architecture/RAM, verified codec identifiers, cache totals, sanitized processing-plan summaries and categorized recent failures. It does not export source paths, filenames, raw commands/filter strings, settings, log messages, hostnames or secrets. Error categories are derived locally from messages. The report is written locally and is never sent automatically.

## Local validation evidence

On the development macOS ARM64 machine, the full suite passed 435 tests and 31 subtests; its one skipped short-audio integration test was then run with an explicit FFmpeg path and passed. Ruff and Python compilation passed. The built portable application passed all seven required behavior checks.

- [Packaged application report](reports/package-smoke-macos-arm64.json)
- [Repeated packaged launch](reports/package-smoke-macos-arm64-warm.json)
- [Three-repeat workload report](reports/performance-macos-arm64.json)

The first measured packaged startup took approximately 17.8 seconds; a repeated launch took 1.84 seconds. These observations do not establish a cause for the difference. The synthetic 4K fixture is one second at five frames per second; its encode timing is not a forecast for arbitrary 4K footage. No local Whisper runtime/model was available for actual speech timing, so the report explicitly records transcription as skipped. Windows/Linux packages and real VA-API/NVENC/QSV devices were not executed locally; their workflow/command coverage remains distinct from the tested macOS package.
