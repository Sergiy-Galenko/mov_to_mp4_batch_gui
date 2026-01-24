# Media Converter — Фото + Відео (FFmpeg)

Зручний GUI‑інструмент на Python (Tkinter) для пакетної конвертації відео та зображень через FFmpeg. Орієнтований на щоденну роботу: черга файлів, пресети, прогрес/ETA, GPU‑кодування, розширені фільтри й метадані.

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
- Light/Dark тема

## Вимоги

- **Python 3.10+**
- **FFmpeg** (і бажано ffprobe)

Перевірка:
```bash
ffmpeg -version
ffprobe -version
```

## Встановлення FFmpeg (Windows)

Через winget:
```powershell
winget install -e --id Gyan.FFmpeg
```

Або вручну: завантажити build, розпакувати та вказати `ffmpeg.exe` в UI (або додати в PATH).

## Запуск

```bash
pip install -r requirements.txt
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
    app.py
    styles.py
  utils/
    files.py
    formatting.py
  assets/
```

## Примітки

- Якщо FFmpeg не знайдено — натисни **Вказати** і вибери `ffmpeg.exe`.
- Для коректного ETA потрібен `ffprobe`.
- Fast copy працює лише коли немає фільтрів/trim та контейнер сумісний з кодеком.

---

Ліцензія: вільне використання для власних проєктів.
