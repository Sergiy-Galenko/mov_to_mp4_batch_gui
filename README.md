# Media Converter — Фото + Відео (FFmpeg)

Зручний GUI‑інструмент на Python (PySide6) для пакетної конвертації відео та зображень через FFmpeg. Орієнтований на щоденну роботу: черга файлів, пресети, прогрес/ETA, GPU‑кодування, розширені фільтри й метадані.

## ✅ Можливості

- Пакетна обробка відео й фото (додавання файлів/папок)
- Прогрес по файлу + загальний ETA (через `ffmpeg -progress`)
- Пресети (збереження/завантаження параметрів)
- Trim/merge, resize/crop/rotate, speed
- Водяний знак / текст
- GPU‑кодування: NVENC / QSV / AMF
- Кодеки: H.264, H.265, AV1, VP9
- ffprobe‑інфо (тривалість, кодеки, розмір)
- Fast copy (копіювання без перекодування, коли можливо)
- Метадані: копіювання / очищення / власні поля
- Світла **тема**

## Вимоги

- **Python 3.10+**
- **FFmpeg** (і бажано ffprobe)
- **PySide6** (встановлюється через `pip`)

Перевірка:
```bash
ffmpeg -version
ffprobe -version
```

## Встановлення FFmpeg (різні платформи)

### Windows

Через winget:
```powershell
winget install -e --id Gyan.FFmpeg
```

Через Chocolatey:
```powershell
choco install ffmpeg
```

Або вручну: завантажити build, розпакувати та вказати `ffmpeg.exe` в UI (або додати в PATH).

### macOS

Через Homebrew:
```bash
brew install ffmpeg
```

### Linux

Ubuntu/Debian:
```bash
sudo apt update
sudo apt install ffmpeg
```

Fedora:
```bash
sudo dnf install ffmpeg
```

Arch/Manjaro:
```bash
sudo pacman -S ffmpeg
```

## Встановлення та запуск

### 1) Створити віртуальне середовище (рекомендовано)
```bash
python -m venv .venv
```

Активація:
- **Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
- **Windows (CMD):**
  ```bat
  .\.venv\Scripts\activate.bat
  ```
- **macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

### 2) Встановити залежності
```bash
pip install -r requirements.txt
```

### 3) Запуск
```bash
python main.py
```

## Швидкий старт

1. Запусти `python main.py`
2. Додай файли або папку
3. Обери формат виходу та параметри
4. Натисни **Старт**

## Підтримувані формати

**Вхідні відео:**
`mov, mp4, mkv, webm, avi, m4v, flv, wmv, mts, m2ts`

**Вхідні зображення:**
`jpg, jpeg, png, webp, bmp, tif, tiff, heic, heif`

**Вихідні формати:**
- Відео: `mp4, mkv, webm, mov, avi, gif`
- Фото: `jpg, png, webp, bmp, tiff`

---

## Tauri + Web UI (нова версія інтерфейсу)

Проєкт має окрему гілку інтерфейсу на **Tauri + React** з сучасним дизайном у стилі Netflix та можливістю змінювати тему/акцентні кольори.

### Запуск Tauri‑версії

```bash
cd tauri_app
npm install
npm run tauri dev
```

### Що вже є

- сучасний UI (Netflix‑style)
- кастомізація щільності інтерфейсу, розміру кнопок і теми
- можливість задавати accent‑колір

### Що ще треба доробити

- інтеграція з FFmpeg (через Python sidecar або перепис на Rust)
- реальні діалоги вибору файлів/папок і лог‑стрімінг

## Структура проєкту

```
mov_to_mp4_batch_gui/
  main.py
  requirements.txt
  config/
    constants.py
    paths.py
  core/
    models.py
    presets.py
  services/
    converter_service.py
    ffmpeg_service.py
  ui/
    qt_app.py
    app.py
    styles.py
  utils/
    files.py
    formatting.py
  assets/
```

## Примітки

- Якщо FFmpeg не знайдено — натисни **Вказати** і вибери `ffmpeg` (або `ffmpeg.exe` у Windows).
- Для коректного ETA потрібен `ffprobe`.
- Fast copy працює лише коли немає фільтрів/trim та контейнер сумісний з кодеком.

---

Ліцензія: вільне використання для власних проєктів.
