# Media Converter

Desktop batch media converter for video, audio, images, and subtitles. The app is built with Python, PySide6, QML, and FFmpeg.

## Features

- Dark desktop UI with a sidebar, queue screen, analytics screen, presets, FFmpeg tools, and settings.
- Drag-and-drop files or folders into the queue.
- Batch conversion for video, image, audio, and subtitle files.
- Automatic media-type aware output formats: images use image formats, videos use video formats, audio uses audio formats, and subtitles use subtitle formats.
- Right-click quick conversion: choose only the output format for one queued file and convert it immediately.
- Queue controls for retry, skip, remove, reorder, multi-select, batch remove, and per-file overrides.
- Presets for common formats and platform targets.
- FFmpeg/FFprobe integration for metadata, thumbnails, progress, ETA, and previews.
- YouTube download support through `yt-dlp`: download a video or extract audio into the queue.
- Performance profiles: `Quality`, `Balanced`, `Fast`, and `Small file`.
- Target output size mode with bitrate estimation.
- GPU-aware parallel conversion when a supported hardware encoder is available.
- Built-in analytics for speed, per-file timings, codec distribution, and system resources.
- JSON-based localization for Ukrainian, English, Polish, and German.
- CLI mode for automation without starting the GUI.

## Requirements

- Python `3.13+`
- FFmpeg
- FFprobe, recommended for metadata, ETA, thumbnails, and analytics
- PySide6
- yt-dlp, used for YouTube and other supported video-site downloads

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

Check FFmpeg:

```bash
ffmpeg -version
ffprobe -version
```

## Run The GUI

```bash
python main.py
```

Basic workflow:

1. Drag files or a folder into the queue.
2. Choose a preset or configure the output settings.
3. Use `Convert all` on the Queue screen to start the whole queue.
4. Right-click a queued file to open Quick convert for that one file.
5. Watch progress, session stats, logs, and analytics.

## YouTube Downloads

The FFmpeg / Watch screen includes a YouTube download panel. Paste a URL and choose:

- `Download video`: downloads the best practical video and adds it to the queue.
- `Download audio`: extracts audio, defaults to MP3 behavior in the backend, and adds it to the queue.

Downloaded files are saved to the configured output directory. Audio extraction and some video merges require FFmpeg, so keep the FFmpeg path configured.

## Quick Convert

Right-click any item in the queue to open a focused conversion panel. The panel shows only the selected file, its media type, and the matching output formats.

- Image files show formats such as `jpg`, `png`, `webp`, `bmp`, and `tiff`.
- Video files show formats such as `mp4`, `mkv`, `webm`, `mov`, `avi`, and `gif`.
- Audio files show formats such as `mp3`, `m4a`, `aac`, `wav`, `flac`, and `opus`.
- Subtitle files show formats such as `srt`, `ass`, and `vtt`.

Use `Save format` to store the format as a per-file override, or `Convert this file` to save the override and run only that file.

## CLI Mode

CLI mode uses `--cli` and does not initialize PySide or QML.

```bash
python main.py --cli -i input.mov -o ./converted --profile Balanced
```

Examples:

```bash
python main.py --cli -i a.mov b.mov -o ./out --preset "Discord - Compact MP4"
python main.py --cli -i input.mp4 -o ./out --profile "Small file" --target-size-mb 25
python main.py --cli -i input.mov -o ./out --settings-json settings.json --language en
python main.py --cli -o ./downloads --download-url "https://youtu.be/VIDEO_ID" --download-mode video
python main.py --cli -o ./downloads --download-url "https://youtu.be/VIDEO_ID" --download-mode audio --download-audio-format mp3
```

Useful CLI arguments:

- `--preset`: use a saved GUI preset.
- `--settings-json`: load GUI-compatible settings from JSON.
- `--profile`: choose `Quality`, `Balanced`, `Fast`, or `Small file`.
- `--target-size-mb`: estimate bitrate for a target output size.
- `--cpu-load-limit` and `--gpu-load-limit`: delay new tasks when system load is above the limit.
- `--ffmpeg` and `--ffprobe`: set explicit binary paths.
- `--language`: choose `uk`, `en`, `pl`, or `de`.
- `--download-url`: download a YouTube/video-site URL before conversion, or download only when no `--input` is provided.
- `--download-mode`: choose `video` or `audio`.
- `--download-audio-format`: choose `mp3`, `m4a`, `opus`, `wav`, `flac`, or `aac`.
- `--download-only`: download URL(s) and exit without conversion.

## Localization

Translations are stored in:

```text
ui/i18n/
  uk.json
  en.json
  pl.json
  de.json
```

`ui/qml/App/I18n.qml` reads translations through the backend. Python services use the same dictionaries through `app/localization.py`, so key logs, status messages, and dialogs can follow the selected UI language.

## Project Structure

```text
mov_to_mp4_batch_gui/
  main.py                 # GUI entry point
  cli.py                  # CLI mode for automation
  requirements.txt
  requirements-dev.txt
  pytest.ini
  app/                    # config, models, presets, settings
  services/               # FFmpeg, conversion, YouTube download, transcription, validation
  ui/                     # Python backend and QML UI
    backend.py
    i18n/
    qml/
      App/
      components/
      Main.qml
  utils/                  # file helpers, formatting, persisted state
  assets/                 # icons and images
  tests/                  # automated tests
  scripts/                # helper/build scripts
  build/                  # PyInstaller spec
```

## Performance Profiles

Profiles set practical defaults for CRF, preset, codec, and hardware encoder behavior:

- `Quality`: lower CRF and slower preset for better visual quality.
- `Balanced`: default profile for everyday work.
- `Fast`: faster encoding.
- `Small file`: more aggressive size reduction.

When `target_size_mb` is set, the command builder estimates bitrate from duration and desired size. Audio-only output can also use estimated bitrate when duration is known.

## Analytics

The QML analytics screen includes:

- Throughput timeline.
- Top completed files by processing time.
- Codec distribution chart.
- CPU, GPU, and RAM timeline.

CPU and RAM metrics use `psutil`. GPU metrics use `nvidia-smi` when available.

## Tests

```bash
python -m pytest -q
```

Current expected result:

```text
69 passed
```

## Build

The PyInstaller spec is in `build/media_converter.spec` and includes QML, translations, and assets.

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python scripts/find_ffmpeg.py
python scripts/build_pyinstaller.py
```

The build output is created in:

```text
dist/MediaConverter/
```
