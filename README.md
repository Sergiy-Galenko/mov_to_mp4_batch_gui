# Media Converter

Desktop GUI для пакетної обробки відео, аудіо, зображень і субтитрів через FFmpeg. Основний інтерфейс побудований на Python, PySide6 і QML.

## Можливості

- Signal Dark UI: темний pro-tool layout, sidebar, компактний header, session stats і Canvas analytics.
- Черга на `ListView` з lazy rendering, thumbnails, per-file shimmer progress, failed details, retry/skip/remove.
- Drag-and-drop файлів і папок, drag-reorder у черзі, multi-select, batch remove і batch override.
- Локалізація через JSON: українська, англійська, польська, німецька.
- Performance profiles: `Quality`, `Balanced`, `Fast`, `Small file`.
- Target output size: режим “зробити файл до N MB” із підбором bitrate.
- GPU-aware parallel conversion: до 2 одночасних незалежних FFmpeg задач для GPU encoder; CPU mode лишається 1 активна задача + ffprobe prefetch.
- Analytics без QtCharts/matplotlib: throughput, per-file timings, codec donut, CPU/GPU/RAM graph.
- Output size prediction, compression ratio per file, average encode speed timeline.
- Platform presets: YouTube, TikTok, Instagram, Telegram, WhatsApp, X/Twitter, LinkedIn, Discord.
- CLI mode для automation/hooks без запуску GUI.

## Вимоги

- Python `3.13+`
- FFmpeg
- FFprobe бажано для metadata, ETA, thumbnails і analytics
- PySide6

Встановлення залежностей:

```bash
python -m pip install -r requirements.txt
```

Перевірка FFmpeg:

```bash
ffmpeg -version
ffprobe -version
```

## Запуск GUI

```bash
python main.py
```

Швидкий flow:

1. Перетягни файли або папку в drop zone.
2. Обери preset або налаштуй формат, codec, profile, target size.
3. Перевір preview output paths.
4. Натисни `Start`.
5. Стеж за queue progress, session stats і analytics.

## CLI Mode

CLI запускається через `--cli` і не ініціалізує PySide/QML.

```bash
python main.py --cli -i input.mov -o ./converted --profile Balanced
```

Приклади:

```bash
python main.py --cli -i a.mov b.mov -o ./out --preset "Discord • Compact MP4"
python main.py --cli -i input.mp4 -o ./out --profile "Small file" --target-size-mb 25
python main.py --cli -i input.mov -o ./out --settings-json settings.json --language en
```

Корисні аргументи:

- `--preset` - використати GUI preset із preset store.
- `--settings-json` - JSON із GUI-compatible settings.
- `--profile` - `Quality`, `Balanced`, `Fast`, `Small file`.
- `--target-size-mb` - цільовий розмір вихідного файлу.
- `--cpu-load-limit`, `--gpu-load-limit` - відкласти старт наступної задачі, якщо навантаження вище ліміту.
- `--ffmpeg`, `--ffprobe` - явні шляхи до бінарників.
- `--language` - `uk`, `en`, `pl`, `de`.

## Локалізація

Переклади лежать у:

```text
ui/i18n/
  uk.json
  en.json
  pl.json
  de.json
```

`ui/qml/App/I18n.qml` читає переклади через backend, а Python backend використовує ті самі словники через `app/localization.py`, тому ключові log/status/dialog messages також можуть перекладатися вибраною мовою.

## Структура проєкту

```text
mov_to_mp4_batch_gui/
  main.py                 <- точка входу
  cli.py                  <- CLI режим для automation/hooks
  requirements.txt
  requirements-dev.txt
  pytest.ini
  app/                    <- конфіг, моделі, пресети, налаштування
    constants.py
    paths.py
    localization.py
    models.py
    performance_profiles.py
    presets.py
    settings.py
  services/               <- FFmpeg, конвертер, Whisper, історія, validation
    converter_service.py
    ffmpeg_service.py
    transcription_service.py
  ui/                     <- Python backend + QML
    backend.py
    i18n/
    qml/
      App/
        qmldir
        Theme.qml
        I18n.qml
      components/
      Main.qml
  utils/                  <- файли, форматування, стан
    files.py
    formatting.py
    state.py
  assets/                 <- іконки, зображення
  tests/                  <- тести
  scripts/                <- build-скрипти
    find_ffmpeg.py
    build_pyinstaller.py
  build/                  <- PyInstaller spec
    media_converter.spec
  .github/
    workflows/
```

## Performance Profiles

Профілі задають автоматичні defaults для CRF, preset, codec і hardware encoder:

- `Quality`: нижчий CRF, повільніший preset, вищий візуальний запас.
- `Balanced`: дефолт для щоденного використання.
- `Fast`: швидший encode.
- `Small file`: H.265 і агресивніший розмір.

Якщо задано `target_size_mb`, FFmpeg command builder рахує bitrate з duration і бажаного розміру. Для audio-only також підбирається bitrate, якщо відома duration.

## Analytics

QML Canvas панелі:

- **Throughput**: encode speed timeline.
- **Per-file**: топ-10 файлів за часом обробки.
- **Codecs**: donut chart за вихідними/виявленими codec labels.
- **Resources**: CPU/GPU/RAM timeline.

Backend signals:

```python
speedHistoryChanged = Signal(list)
fileTimingsChanged = Signal(list)
codecDistributionChanged = Signal(dict)
resourceHistoryChanged = Signal(list)
```

CPU/RAM беруться з `psutil`. GPU читається через `nvidia-smi`, якщо він доступний; якщо ні, графік лишається без GPU samples.

## Продуктивність

- Queue рендериться через `ListView`, не `Repeater`.
- Progress events throttled приблизно до 250 ms.
- FFprobe prefetch запускається після додавання файлів.
- Thumbnails завантажуються асинхронно.
- `highLoadMode` вимикає дорогі анімації для великих черг.
- GPU encoder дозволяє до 2 паралельних незалежних задач.
- Merge, auto-subtitle, split-chapters і hook-heavy сценарії йдуть послідовним fallback шляхом.

## Тести

```bash
python -m pytest -q
```

Поточний очікуваний результат:

```text
58 passed
```

## Збірка

PyInstaller spec у `build/media_converter.spec` включає `ui/qml`, `ui/i18n` і `assets`, тому QML components і JSON translations потрапляють у build разом із застосунком.

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python scripts/find_ffmpeg.py
python scripts/build_pyinstaller.py
```

Артефакт буде в:

```text
dist/MediaConverter/
```
