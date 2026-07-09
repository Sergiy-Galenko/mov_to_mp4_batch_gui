# Media Converter

Desktop batch converter for video, photos, audio, subtitles, and text files. The app is built with Python, PySide6, QML, FFmpeg, and a lightweight built-in text converter.

## Features

- **Arc/Linear-Inspired UI**: Completely redesigned interface with deep dark modes, glassmorphism, soft shadows, and clean layouts.
- **Progressive Disclosure**: Advanced settings and sidebar are hidden by default to keep the main conversion screen incredibly simple and focused.
- **Emoji-Driven Navigation**: Uses clear emoji indicators (🎬, 🎵, ✅, ⏳, 📥) instead of text for instant visual recognition of media types and status.
- **Modern Drag & Drop Zone**: A large, interactive glassmorphism drop zone for importing files directly from the desktop.
- Top workspace switcher for `Photo`, `Video`, and `Text` modes. Each mode filters the queue, file picker, folder import, preview, and relevant edit controls.
- Large centered selected-file preview: photos display as a larger image, videos display their generated frame thumbnail, and text files show a readable text preview.
- Batch conversion for video, image, audio, subtitle, and text files with automatic media-type aware output formats.
- Right-click quick conversion: choose only the output format for one queued file and convert it immediately.
- Queue controls for retry, skip, remove, reorder, multi-select, batch remove, and per-file overrides.
- Batch workflow automation with watch-folder auto-convert, folder rules, scheduler, completion actions, and HTTP/Discord/Telegram notifications.
- Explicit output-folder selection before any conversion or URL download starts.
- Presets for common formats and platform targets (iPhone, PlayStation 5, etc).
- FFmpeg/FFprobe integration for metadata, thumbnails, progress, ETA, and previews.
- Built-in document conversion between plain text, PDF, Word, Excel, PowerPoint, and OpenDocument-style formats; text/document-only conversion does not require FFmpeg.
- Opt-in FFmpeg, Python dependency, and Desktop `.exe` bootstrap on Windows x64.
- Video/source URL download support through `yt-dlp`, with direct media URL fallback: download a video or extract audio into the queue.
- Smart Convert mode for per-file codec/CRF/preset recommendations, remux detection, two-pass target-size encoding, quality checks, and A/B samples.
- Lightweight editor filters for deinterlace, stabilization, denoise, color correction, LUT files, and speed changes.
- Subtitle tools for offset adjustment and styled burn-in output.
- Privacy and security tools: manual blur regions, metadata sanitization, checksum sidecars, and secure-delete after conversion.
- Optional cloud upload after conversion through an external `rclone` remote.
- Commercial licensing with key activation, offline license files, trial mode, Pro feature gates, commercial export gating, and paid-build update checks.
- GPU-aware parallel conversion when a supported hardware encoder is available.
- Built-in analytics for speed, per-file timings, codec distribution, and system resources.
- Full batch rename preview with copy/export to CSV before conversion starts.
- JSON-based localization for Ukrainian, English, Polish, and German.
- CLI mode for automation without starting the GUI.

## Requirements

- Python `3.12+`
- FFmpeg, required for video, photo, audio, subtitle, URL audio extraction, and media merge workflows
- FFprobe, recommended for metadata, ETA, thumbnails, and analytics
- PySide6
- yt-dlp, used for supported video-site downloads
- Optional: `rclone`, used for Google Drive, OneDrive, Dropbox, S3/MinIO, FTP, and SFTP uploads

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

On Windows, `run_windows.cmd` checks Python automatically and starts the app when Python 3.12+ is already available.
System Python installation, package installation, and launch-time Desktop `.exe` creation are explicit opt-in actions:

```powershell
.\scripts\python_bootstrap.ps1 -Mode run -AllowSystemInstall -AllowDependencyInstall -AllowDesktopBuild
```

The app checks imports at startup, but does not run `pip install` unless this is explicitly enabled:

```bash
MEDIA_CONVERTER_AUTO_INSTALL_DEPS=1
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

Text-only conversion does not require FFmpeg or FFprobe.

## Run The GUI

```bash
python main.py
```

Or on Windows with Python bootstrap:

```bat
run_windows.cmd
```

Launch-time Desktop `.exe` creation is disabled by default. To build or refresh `MediaConverter.exe` on the Desktop
while starting the app:

```bat
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\python_bootstrap.ps1 -Mode run -AllowDependencyInstall -AllowDesktopBuild
```

Basic workflow:

1. Choose the output folder where all converted files and downloads will be saved.
2. Choose the top workspace mode: `Conversion` for everything, or `Photo`, `Video`, or `Text` for focused work.
3. Drag files or a folder into the queue, or use the mode-aware add buttons.
4. Select a photo, video, or text file to see it larger in the center preview and adjust the matching output/edit settings.
5. Choose a preset or configure the output settings.
6. Use `Convert all` on the Queue screen to start the whole queue.
7. Right-click a queued file to open Quick convert for that one file.
8. Watch progress, session stats, logs, and analytics.

## Photo, Video, And Text Workspaces

The top toolbar includes focused workspace modes:

- `Photo`: shows image files, opens image-aware file filters, and puts photo quality, resize/crop, watermark, and text overlay controls close to the preview workflow.
- `Video`: shows video files, opens video-aware file filters, and links directly to video editor, trim/resize, and audio/subtitle controls.
- `Text`: shows text files, opens text-aware file filters, previews text content in the center panel, and exposes text output formats.

The default `Conversion` mode still shows every supported file type in one queue.

## Video URL Downloads

The Downloads screen includes a video/source URL download panel. Paste or drag a URL into the URL field and choose:

- `Download video`: downloads the best practical video and adds it to the queue.
- `Download audio`: extracts audio, defaults to MP3 behavior in the backend, and adds it to the queue.
- Quality: `best`, `1080p`, `720p`, or `audio_only`.
- Batch URL import from `.txt` or `.csv` files.
- Automatic preview with detected source type, title, duration, available quality summary, and thumbnail when the source exposes one.
- Optional playlist downloads.
- Optional subtitle download.
- Optional `cookies.txt` file for private, age-restricted, or account-bound videos.
- Optional download speed limit.
- Failed/cancelled download retry and a separate download log.
- Built-in `yt-dlp` update button.
- Download history for recent URLs.
- Cancel button for an active download.

The app uses `yt-dlp` for supported video sites and falls back to plain HTTP(S) for direct media links such as `.mp4`, `.mov`, `.webm`, `.mp3`, or `.m4a`. DRM-protected streams, paywalled content, or sources that require bypassing access controls are not supported. Downloaded files are saved to the configured output directory. Audio extraction and some video merges require FFmpeg, so keep the FFmpeg path configured.

If no output folder has been selected yet, the GUI asks for it before starting the download.

## Quick Convert

Right-click any item in the queue to open a focused conversion panel. The panel shows only the selected file, its media type, and the matching output formats.

- Image files show formats such as `jpg`, `png`, `webp`, `bmp`, and `tiff`.
- Video files show formats such as `mp4`, `mkv`, `webm`, `mov`, `avi`, and `gif`.
- Audio files show formats such as `mp3`, `m4a`, `aac`, `wav`, `flac`, and `opus`.
- Subtitle files show formats such as `srt`, `ass`, and `vtt`.
- Text/document files show formats such as `txt`, `md`, `html`, `pdf`, `docx`, `xlsx`, `pptx`, `odt`, `ods`, and `odp`.

Use `Save format` to store the format as a per-file override, or `Convert this file` to save the override and run only that file.

## Text Conversion

Text and document files are first-class queue items. Supported input extensions include:

```text
.txt .md .markdown .html .htm .json .csv .tsv .xml .yaml .yml .log .rtf
.pdf .docx .docm .dotx .doc .odt .ott
.xlsx .xlsm .xltx .xls .ods .ots
.pptx .pptm .ppsx .potx .ppt .odp .otp
```

Supported output formats are:

```text
txt md html json csv tsv rtf pdf docx doc odt xlsx xls ods pptx ppt odp
```

Text/document conversion uses Python document handlers instead of FFmpeg, so a text-only queue can run even when FFmpeg is not configured. `docx`, `xlsx`, `pptx`, `odt`, `ods`, and `odp` are generated as real document packages; legacy `doc`, `xls`, and `ppt` use compatibility fallbacks.

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

## Commercial License

The Settings sidebar includes a Commercial License screen for paid/commercial builds:

- Activate a license key or load an offline JSON license file.
- Start a local trial mode for Pro features.
- View license status, plan, holder, expiry, trial time, and commercial export availability.
- Enable paid auto-update checks from a configured manifest URL.

Pro-gated features include AI blur, batch automation, cloud upload, and advanced JSON/HTML reports. Watermark-free commercial export is blocked unless an active Commercial license is present. AI blur is license-gated here, but the automatic ML detector itself still requires a separate integration.

Production licensing must set `MEDIA_CONVERTER_LICENSE_SECRET` during paid-build packaging. The development fallback
secret is disabled unless `MEDIA_CONVERTER_ALLOW_DEV_LICENSE_SECRET=1` is set.

## Reports And History

Conversion history is stored locally and can be rerun or reused for settings. The latest run can be exported from Analytics as CSV, JSON, or HTML.

## Batch Workflow Automation

The FFmpeg / Watch settings panel includes automation controls for longer unattended runs:

- Watch-folder auto-convert starts conversion for newly detected stable files.
- Folder rules can apply per-file overrides such as `Downloads -> mp4`, `Camera -> h265 priority=3`, or `Audio -> mp3`.
- Scheduler modes can start queued work by time, by low CPU/GPU load, or by both conditions.
- Completion actions can do nothing, open the output folder, sleep, or schedule shutdown.
- Notifications can be sent through desktop tray notifications, a generic webhook, Discord webhook, or Telegram bot/chat.
- Output preview can be copied or exported as `rename-preview.csv` before conversion.

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
- `--download-url`: download a video/source URL before conversion, or download only when no `--input` is provided.
- `--download-mode`: choose `video` or `audio`.
- `--download-quality`: choose `best`, `1080p`, `720p`, or `audio_only`.
- `--download-audio-format`: choose `mp3`, `m4a`, `opus`, `wav`, `flac`, or `aac`.
- `--download-playlist`: allow playlist downloads.
- `--download-subtitles`: download subtitles next to the media.
- `--download-cookies`: use a Netscape `cookies.txt` file.
- `--download-rate-limit-kbps`: limit download speed in KB/s; `0` means unlimited.
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
  services/               # FFmpeg, conversion, text conversion, URL download, transcription, validation
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
96 passed
```

## Build

The PyInstaller spec is in `build/media_converter.spec` and includes QML, translations, and assets.

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python scripts/find_ffmpeg.py
python scripts/build_pyinstaller.py
```

Or on Windows with Python bootstrap and explicit dependency install:

```bat
build_exe_windows.cmd
```

The PyInstaller build output is created in:

```text
dist/MediaConverter.exe
```

The built `.exe` includes the Python runtime, so end users do not need Python installed to run it.
