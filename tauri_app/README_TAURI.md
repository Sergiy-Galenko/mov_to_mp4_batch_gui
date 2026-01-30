# Tauri + React UI

Це нова версія інтерфейсу на Tauri + React. Вона відокремлена від поточної PySide/QML реалізації.

## Запуск (dev)

1. Встановити залежності:
   - `npm install`
2. Запустити dev-сервер:
   - `npm run dev`
3. Запустити Tauri:
   - `npm run tauri dev`

## Структура
- `tauri_app/src` — React UI.
- `tauri_app/src-tauri` — Rust backend (команди Tauri).

## Що вже є
- UI‑каркас з табами і секціями (черга, вивід, налаштування, лог, прогрес).
- Tauri команди‑заглушки (pick_files, start_conversion, stop_conversion тощо).

## Що треба доробити
- Реальна інтеграція з FFmpeg (можна викликати Python як sidecar або переписати логіку на Rust).
- Реальні діалоги вибору файлів/папок.
- Логи/прогрес через events (emit/listen).
