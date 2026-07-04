# Media Converter

Desktop batch media converter for video, audio, images, and subtitles. The app is built with Python, PySide6, QML, and FFmpeg.

## Features

- Dark desktop UI with a sidebar, queue screen, analytics screen, presets, FFmpeg tools, and settings.
- Drag-and-drop files or folders into the queue.
- Explicit output-folder selection before any conversion or YouTube download starts.
- Batch conversion for video, image, audio, and subtitle files.
- Automatic media-type aware output formats: images use image formats, videos use video formats, audio uses audio formats, and subtitles use subtitle formats.
- Right-click quick conversion: choose only the output format for one queued file and convert it immediately.
- Queue controls for retry, skip, remove, reorder, multi-select, batch remove, and per-file overrides.
- Presets for common formats and platform targets.
- FFmpeg/FFprobe integration for metadata, thumbnails, progress, ETA, and previews.
- Automatic FFmpeg bootstrap on Windows x64: if FFmpeg is missing, the app downloads a local managed copy and checks it for updates on startup.
- Automatic Python dependency bootstrap: missing runtime libraries from `requirements.txt` are installed on startup with `python -m pip install -r requirements.txt`.
- YouTube download support through `yt-dlp`: download a video or extract audio into the queue.
- Device profiles for iPhone/iPad/Apple TV/Android/Samsung TV/consoles/TV sticks/action cameras/DVD/Blu-ray targets.
- Smart Convert mode for per-file codec/CRF/preset recommendations, remux detection, two-pass target-size encoding, quality checks, and A/B samples.
- Lightweight editor filters for deinterlace, stabilization, denoise, color correction, LUT files, and speed changes.
- Subtitle tools for offset adjustment and styled burn-in output.
- Privacy and security tools: manual blur regions, metadata sanitization, checksum sidecars, and secure-delete after conversion.
- Optional cloud upload after conversion through an external `rclone` remote.
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
- Optional: `rclone`, used for Google Drive, OneDrive, Dropbox, S3/MinIO, FTP, and SFTP uploads

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

The app also runs this dependency check automatically at startup. To disable automatic Python package installation in managed environments, set:

```bash
MEDIA_CONVERTER_SKIP_DEP_BOOTSTRAP=1
```

Check FFmpeg:

```bash
ffmpeg -version
ffprobe -version
```

On Windows x64 the GUI can install FFmpeg automatically into the app data folder:

```text
%LOCALAPPDATA%\MediaConverter\ffmpeg\current
```

The app does not modify the system `PATH`. If you manually choose an external FFmpeg binary, that path is respected and the app does not overwrite it.

## Run The GUI

```bash
python main.py
```

Basic workflow:

1. Choose the output folder where all converted files and downloads will be saved.
2. Drag files or a folder into the queue.
3. Choose a preset or configure the output settings.
4. Use `Convert all` on the Queue screen to start the whole queue.
5. Right-click a queued file to open Quick convert for that one file.
6. Watch progress, session stats, logs, and analytics.

## YouTube Downloads

The Downloads screen includes a YouTube download panel. Paste or drag a URL into the URL field and choose:

- `Download video`: downloads the best practical video and adds it to the queue.
- `Download audio`: extracts audio, defaults to MP3 behavior in the backend, and adds it to the queue.
- Quality: `best`, `1080p`, `720p`, or `audio_only`.
- Optional playlist downloads.
- Optional subtitle download.
- Optional `cookies.txt` file for private, age-restricted, or account-bound videos.
- Download history for recent URLs.
- Cancel button for an active download.

Downloaded files are saved to the configured output directory. Audio extraction and some video merges require FFmpeg, so keep the FFmpeg path configured.

If no output folder has been selected yet, the GUI asks for it before starting the download.

## Quick Convert

Right-click any item in the queue to open a focused conversion panel. The panel shows only the selected file, its media type, and the matching output formats.

- Image files show formats such as `jpg`, `png`, `webp`, `bmp`, and `tiff`.
- Video files show formats such as `mp4`, `mkv`, `webm`, `mov`, `avi`, and `gif`.
- Audio files show formats such as `mp3`, `m4a`, `aac`, `wav`, `flac`, and `opus`.
- Subtitle files show formats such as `srt`, `ass`, and `vtt`.

Use `Save format` to store the format as a per-file override, or `Convert this file` to save the override and run only that file.

## Device Profiles

The Settings sidebar includes a Device profiles screen. Profiles apply practical container, video codec, audio codec, CRF, and preset defaults for targets such as:

- iPhone 14/15/16, iPad Pro, Apple TV 4K HDR, and Android phones.
- Samsung TV, PlayStation 5, Xbox Series X, Chromecast / Fire TV, and Steam Deck.
- GoPro and DJI import workflows.
- DVD-compatible MPEG-2 output and Blu-ray-oriented H.264/AC3 output.

Profiles intentionally override generic performance defaults. Leave the profile as `None` when you want fully manual codec/CRF/preset control.

## Smart Convert

The Settings sidebar includes a Smart Convert screen. When enabled, each video can be analyzed before conversion and the app can:

- Detect likely content type: automatic, live action, animation, or screencast.
- Recommend codec, CRF, and preset based on resolution, FPS, HDR hints, target container, and quality target.
- Avoid unnecessary re-encoding when the source is already compatible, using remux where possible.
- Use two-pass encoding when a target output size is set.
- Run a post-conversion corruption check with FFmpeg.
- Measure output quality with SSIM or VMAF.
- Generate short A/B sample files with several CRF values for quick visual comparison.

VMAF depends on an FFmpeg build that includes the `libvmaf` filter. If that filter is missing, conversion still finishes and the app logs a warning for the metric step.

## Editor, Subtitles, And Privacy

The new side tabs expose FFmpeg-backed controls:

- Video editor: deinterlace, deshake stabilization, `hqdn3d`/`nlmeans` denoise, brightness, contrast, saturation, gamma, and `.cube`/`.3dl` LUT files.
- Subtitle tools: millisecond offset for subtitle conversion plus burn-in style controls for font, size, color, outline, shadow, and alignment.
- Privacy / Security: manual `x:y:w:h` blur rectangles, metadata sanitization, MD5/SHA256 sidecar generation, and secure-delete of the original after a successful conversion.

Manual blur regions use FFmpeg `delogo`. Automatic face/body/license-plate detection, profanity detection, OCR subtitles, translation APIs, and speaker diarization are not bundled yet; those need separate ML/API integrations.

## Cloud Integration

Cloud upload is implemented through `rclone copy` after a successful conversion. Configure credentials and remotes yourself in `rclone` or the provider tool, then set:

- Provider label.
- rclone executable path.
- Remote path such as `drive:converted`, `s3:bucket/path`, or `sftp:server/out`.

The app does not store provider secrets directly.

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
python main.py --cli -o ./downloads --download-url "https://youtu.be/PLAYLIST_ID" --download-playlist --download-quality 720p
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
- `--download-quality`: choose `best`, `1080p`, `720p`, or `audio_only`.
- `--download-audio-format`: choose `mp3`, `m4a`, `opus`, `wav`, `flac`, or `aac`.
- `--download-playlist`: allow playlist downloads.
- `--download-subtitles`: download subtitles next to the media.
- `--download-cookies`: use a Netscape `cookies.txt` file.
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
78 passed
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
