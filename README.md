# Media Converter — Фото + Відео (FFmpeg)

GUI-інструмент на Python (`PySide6` + QML) для пакетної обробки відео, зображень і аудіо через FFmpeg. Проєкт орієнтований на практичний desktop-workflow: черга задач, пер-file overrides, історія запусків, preview результату, відновлення після падіння, збірка для користувача.

## Можливості

- Пакетна черга файлів і папок
- Drag-and-run workflow через чергу, статуси, retry failed, reorder
- Вивід прогресу по файлу і загального ETA через `ffmpeg -progress`
- Конвертація відео й зображень
- `Audio-only` export
- `Thumbnail` і `Contact sheet`
- `Subtitle burn-in`, `Subtitle extract`, `Auto subtitle` через Whisper
- Trim, merge, resize, crop, rotate, speed
- Watermark, text overlay
- GPU-енкодери: NVENC, QSV, AMF
- Кодеки: H.264, H.265, AV1, VP9
- Fast copy, skip existing, output templates
- Готові platform presets:
  - YouTube
  - TikTok
  - Instagram Reels
  - Instagram Stories
  - Telegram
  - WhatsApp
- Аудіо-інструменти:
  - вибір конкретної аудіодоріжки
  - заміна аудіо у відео
  - EBU R128 normalization
  - peak limit
  - silence trim
  - cover art
  - split by chapters
- Метадані:
  - copy / strip
  - title, author, album, genre, year, track, comment, copyright
- Розширений media analysis через `ffprobe`:
  - duration, codec, resolution, size, container
  - fps
  - VFR/CFR
  - HDR/SDR
  - color space
  - rotation
  - chapter/audio/subtitle counts
  - warnings по aspect ratio та encoder-risk випадках
- Queue UX:
  - recent folders
  - watch folder
  - dedupe по path
  - dedupe по hash
  - per-file overrides
  - export log
- Стан і відновлення:
  - preview фінальних назв файлів до старту
  - історія запусків
  - export/import проєкту в `.json`
  - відновлення черги після аварійного завершення
  - before/after hooks для автоматизації

## Вимоги

- Python `3.10+`
- FFmpeg
- Бажано `ffprobe`
- `PySide6`

Перевірка:

```bash
ffmpeg -version
ffprobe -version
```

## Встановлення FFmpeg

### Windows

```powershell
winget install -e --id Gyan.FFmpeg
```

або:

```powershell
choco install ffmpeg
```

### macOS

```bash
brew install ffmpeg
```

### Linux

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

### 1. Створи venv

```bash
python3 -m venv .venv
```

macOS / Linux:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Встанови залежності

```bash
python3 -m pip install -r requirements.txt
```

### 3. Запусти застосунок

```bash
python3 main.py
```

## Optional: автостворення субтитрів

Для режиму `Авто субтитри` потрібен Whisper.

Варіант через Python-пакет:

```bash
python3 -m pip install openai-whisper
```

Або через CLI `whisper`, якщо він уже є в системі.

Примітка: ця функція залежить від локально встановленої моделі Whisper і не входить у базові `requirements.txt`.

## Швидкий старт

1. Запусти `python3 main.py`
2. Додай файли або папку
3. Обери режим роботи і формат виходу
4. За потреби застосуй platform preset
5. Перевір `Preview назв`
6. Натисни `Старт`

## Підтримувані формати

Вхідні відео:

`mov, mp4, mkv, webm, avi, m4v, flv, wmv, mts, m2ts`

Вхідні зображення:

`jpg, jpeg, png, webp, bmp, tif, tiff, heic, heif`

Вихід:

- Відео: `mp4, mkv, webm, mov, avi, gif`
- Зображення: `jpg, png, webp, bmp, tiff`
- Аудіо: `mp3, m4a, aac, wav, flac, opus`
- Субтитри: `srt, ass, vtt`

## Основні сценарії

### 1. Конвертація під платформу

- Відкрий вкладку з основними налаштуваннями
- Натисни один із preset-кнопок `YouTube`, `TikTok`, `Instagram Reels`, `Instagram Stories`, `Telegram`, `WhatsApp`
- За потреби підправ CRF, resize або output template

### 2. Audio-only export

- Обери `Лише аудіо`
- Вкажи формат `mp3 / m4a / wav / flac / opus`
- За потреби вибери потрібну аудіодоріжку, cover art або split by chapters

### 3. Auto subtitle

- Обери `Авто субтитри`
- Задай мову (`auto`, `uk`, `en`, ...)
- Обери модель Whisper (`tiny`, `base`, `small`, `medium`)

### 4. Відновлення після падіння

- Черга і останні налаштування автоматично пишуться в state
- При наступному запуску застосунок відновлює session-state

### 5. Проєкт у JSON

- `Експорт .json` зберігає:
  - чергу
  - overrides
  - вихідну папку
  - шлях до ffmpeg
  - активні налаштування
- `Імпорт .json` повертає цей стан у UI

## Hooks

Поля `Before hook` і `After hook` приймають shell-команди, які запускаються до та після batch-run.

Середовище передає базові змінні:

- `MC_OUT_DIR`
- `MC_TOTAL_FILES`
- `MC_OPERATION`
- `MC_STOPPED`
- `MC_FAILED_COUNT`

## Тести

```bash
python3 -m unittest discover -s tests -q
```

Або:

```bash
python3 -m pip install -r requirements.txt -r requirements-dev.txt
python3 -m pytest -q
```

## Збірка для користувача

### PyInstaller

```bash
python3 -m pip install -r requirements.txt -r requirements-dev.txt
python3 scripts/find_ffmpeg.py
python3 scripts/build_pyinstaller.py
```

Артефакт буде в `dist/MediaConverter/`.

### Пошук і бандлінг FFmpeg

- `scripts/find_ffmpeg.py` показує, де знайдено `ffmpeg` і `ffprobe`
- `scripts/build_pyinstaller.py` додає binaries в збірку, якщо вони знайдені поруч

Підтримуються env vars:

- `MEDIA_CONVERTER_FFMPEG`
- `MEDIA_CONVERTER_FFPROBE`
- `MEDIA_CONVERTER_BUNDLE_FFMPEG_DIR`
- `MEDIA_CONVERTER_FFMPEG_DIR`

## Структура проєкту

```text
mov_to_mp4_batch_gui/
  main.py
  requirements.txt
  requirements-dev.txt
  LICENSE
  config/
    constants.py
    paths.py
  core/
    models.py
    presets.py
    settings.py
  services/
    converter_service.py
    ffmpeg_service.py
    transcription_service.py
  ui/
    qml_backend.py
    qml/
      Main.qml
      Theme.qml
      components/
  utils/
    files.py
    formatting.py
    state.py
  tests/
  scripts/
```

## Tauri + Web UI

У репозиторії є окремий `tauri_app/` як експериментальна нова UI-гілка. Основний робочий desktop-flow зараз знаходиться в Python/QML-версії.

## Примітки

- Якщо FFmpeg не знайдено, вкажи його вручну в UI через кнопку `Вказати`
- Для точнішого analysis, ETA і warnings бажано мати `ffprobe`
- Fast copy працює лише там, де немає несумісних фільтрів, trim або заміни аудіо
- Auto subtitle не працюватиме без встановленого Whisper

## Ліцензія

MIT. Дивись [LICENSE](LICENSE).
