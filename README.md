# Media Converter

Desktop GUI для пакетної обробки відео, аудіо, зображень і субтитрів через FFmpeg. Основний інтерфейс побудований на Python, PySide6 і QML. У репозиторії також є експериментальний Tauri/Web UI у `tauri_app/`, але основний робочий flow зараз знаходиться в Python/QML-версії.

## Що нового

- Новий UI/UX у стилі **Signal Dark**: темний pro-tool layout, компактний titlebar, ліва collapsible sidebar, щільна права панель налаштувань.
- Черга на `ListView` з lazy rendering, `cacheBuffer`, drag/drop entry point, per-file status rows і кастомним shimmer progress bar.
- Нові індикатори: `ShimmerBar`, `PulseDot`, `ArcSpinner`.
- Нова вкладка analytics без важких chart-бібліотек: throughput line chart, per-file timing bars, codec donut chart на QML Canvas.
- Session stats panel: done/failed/skipped, elapsed, ETA, average speed, input/output/saved bytes.
- Platform presets у горизонтальному chip-row, включно з `X/Twitter`, `LinkedIn`, `Discord`.
- Backend analytics signals для QML: `speedHistory`, `fileTimings`, `codecDistribution`.
- FFprobe prefetch після додавання файлів, кеш metadata для запуску конвертації, throttling progress updates до приблизно 250 ms.

## Можливості

- Пакетна черга файлів і папок.
- Drag-and-drop для відео, аудіо, зображень, субтитрів і папок.
- Retry failed, skip active file, remove items, hash/path dedupe.
- Per-file progress, ETA, speed і status details для помилок.
- Preview майбутніх output paths перед запуском.
- Конвертація відео, аудіо, зображень і субтитрів.
- `Audio-only`, `Thumbnail`, `Contact sheet`.
- `Subtitle burn-in`, `Subtitle extract`, `Auto subtitle` через Whisper.
- Trim, merge, resize, crop, rotate, speed.
- Watermark і text overlay.
- GPU encoder detection: NVENC, QSV, AMF.
- Codecs: H.264, H.265, AV1, VP9.
- Fast copy, skip existing, output templates.
- Watch folder, recent folders, import/export project JSON.
- History, log export, crash/session recovery.
- Before/after hooks для batch automation.

## Вимоги

- Python `3.13+`
- FFmpeg
- FFprobe бажано, бо без нього metadata, ETA і analytics будуть менш точними
- PySide6

Перевірка FFmpeg:

```bash
ffmpeg -version
ffprobe -version
```

## Встановлення FFmpeg

Windows:

```powershell
winget install -e --id Gyan.FFmpeg
```

або:

```powershell
choco install ffmpeg
```

macOS:

```bash
brew install ffmpeg
```

Ubuntu / Debian:

```bash
sudo apt update
sudo apt install ffmpeg
```

Fedora:

```bash
sudo dnf install ffmpeg
```

Arch / Manjaro:

```bash
sudo pacman -S ffmpeg
```

## Встановлення і запуск

Створи virtual environment:

```bash
python -m venv .venv
```

Активуй його.

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Встанови залежності:

```bash
python -m pip install -r requirements.txt
```

Запусти застосунок:

```bash
python main.py
```

## Швидкий старт

1. Запусти `python main.py`.
2. Перетягни файли або папку в drop zone.
3. Обери preset або налаштуй формат, codec, CRF, resize, audio/subtitle options.
4. Перевір preview output paths.
5. Натисни `Start`.
6. Стеж за queue progress, total progress, session stats і analytics.

## Підтримувані формати

Вхідні відео:

`mov, mp4, mkv, webm, avi, m4v, flv, wmv, mts, m2ts`

Вхідні зображення:

`jpg, jpeg, png, webp, bmp, tif, tiff, heic, heif`

Вхідні аудіо:

`mp3, m4a, aac, wav, flac, opus, ogg, wma, aiff, aif, mka`

Вхідні субтитри:

`srt, ass, ssa, vtt, webvtt`

Вихід:

- Відео: `mp4, mkv, webm, mov, avi, gif`
- Зображення: `jpg, png, webp, bmp, tiff`
- Аудіо: `mp3, m4a, aac, wav, flac, opus`
- Субтитри: `srt, ass, vtt`

## Platform presets

Вбудовані presets включають:

- YouTube
- TikTok
- Instagram Reels
- Instagram Stories
- Telegram
- WhatsApp
- X/Twitter
- LinkedIn
- Discord
- H.264 / H.265 / AV1 / VP9 targets
- Fast Copy
- Audio Only
- Thumbnail
- Contact Sheet

Presets відображаються як горизонтальний scrollable chip-row у верхній частині workspace.

## Analytics

Analytics реалізовано на чистому QML Canvas, без QtCharts, matplotlib або сторонніх chart-бібліотек.

Доступні панелі:

- **Throughput**: історія speed samples під час сесії.
- **Per-file**: топ-10 файлів за часом обробки.
- **Codecs**: donut chart розподілу codec metadata з ffprobe.

Backend подає дані через QML properties і signals:

```python
speedHistoryChanged = Signal(list)
fileTimingsChanged = Signal(list)
codecDistributionChanged = Signal(dict)
```

## Performance notes

- Черга рендериться через `ListView`, не через `Repeater`.
- Queue delegate використовує кастомний `Rectangle` progress bar замість QuickControls2 `ProgressBar`.
- Shimmer animation керується shared phase у `Main.qml`, щоб не запускати окрему нескінченну анімацію на кожен item.
- Для черги понад 50 файлів увімкнено `highLoadMode`, який вимикає дорогі анімації.
- Thumbnails завантажуються асинхронно.
- FFprobe prefetch запускається після додавання файлів і кешує metadata для подальшого запуску.
- Progress events throttled до приблизно 250 ms, щоб UI не отримував надлишкових updates.
- Субпроцеси FFmpeg/FFprobe виконуються поза UI thread, а UI оновлюється через event queue і Qt signals.

Поточний conversion pipeline зберігає послідовну семантику для pause/skip/merge/hooks. У коді є GPU-aware worker-limit hook і prefetch path, але повний parallel conversion scheduling ще має врахувати merge, hooks і active-process control.

## Auto subtitle

Для режиму `auto_subtitle` потрібен локальний Whisper.

Python package:

```bash
python -m pip install openai-whisper
```

Або системний CLI `whisper`, якщо він уже встановлений.

Whisper не входить у базовий `requirements.txt`.

## Hooks

Поля `Before hook` і `After hook` приймають shell-команди, які запускаються до та після batch-run.

Передаються базові environment variables:

- `MC_OUT_DIR`
- `MC_TOTAL_FILES`
- `MC_OPERATION`
- `MC_STOPPED`
- `MC_FAILED_COUNT`

## Тести

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python -m pytest -q
```

Поточний очікуваний результат:

```text
21 passed
```

## Збірка

PyInstaller spec уже включає всю директорію `ui/qml`, тому нові QML components потрапляють у build автоматично.

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python scripts/find_ffmpeg.py
python scripts/build_pyinstaller.py
```

Артефакт буде у:

```text
dist/MediaConverter/
```

FFmpeg можна додати в bundle через env vars:

- `MEDIA_CONVERTER_FFMPEG`
- `MEDIA_CONVERTER_FFPROBE`
- `MEDIA_CONVERTER_BUNDLE_FFMPEG_DIR`
- `MEDIA_CONVERTER_FFMPEG_DIR`

## Структура проєкту

```text
mov_to_mp4_batch_gui/
  main.py
  media_converter.spec
  config/
  core/
    models.py
    presets.py
    settings.py
  services/
    converter_service.py
    ffmpeg_service.py
    media_analysis_service.py
    queue_manager.py
  ui/
    models.py
    qml_backend.py
    qml/
      Main.qml
      Theme.qml
      components/
        AnalyticsPanel.qml
        ArcSpinner.qml
        DropZone.qml
        PresetsBar.qml
        PulseDot.qml
        QueueItem.qml
        SessionStats.qml
        ShimmerBar.qml
        SidebarPanel.qml
  tests/
  scripts/
  tauri_app/
```

## Tauri/Web UI

`tauri_app/` залишається експериментальним web UI. Основний підтримуваний desktop workflow зараз у Python/PySide6/QML.

## Примітки

- Якщо FFmpeg не знайдено, вкажи шлях вручну в UI.
- Для точного analysis, ETA, codec chart і warnings потрібен `ffprobe`.
- Fast copy працює тільки коли немає несумісних фільтрів, trim або audio replacement.
- Auto subtitle не працюватиме без локального Whisper.

## Ліцензія

MIT. Дивись [LICENSE](LICENSE).
