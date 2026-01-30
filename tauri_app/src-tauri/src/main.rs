#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use serde::Serialize;
use std::path::PathBuf;
use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindowBuilder};

#[derive(Serialize, Clone)]
struct QueueItem {
    id: String,
    name: String,
    path: String,
    kind: String,
}

type Result<T> = std::result::Result<T, String>;

fn path_to_string(path: PathBuf) -> String {
    path.to_string_lossy().to_string()
}

fn kind_from_name(name: &str) -> String {
    let lower = name.to_lowercase();
    if lower.ends_with(".jpg")
        || lower.ends_with(".jpeg")
        || lower.ends_with(".png")
        || lower.ends_with(".webp")
        || lower.ends_with(".bmp")
    {
        "photo".to_string()
    } else {
        "video".to_string()
    }
}

#[tauri::command]
fn pick_files() -> Result<Vec<QueueItem>> {
    let selections = rfd::FileDialog::new().pick_files().unwrap_or_default();
    let mut items = Vec::new();
    for path in selections {
        let name = path
            .file_name()
            .and_then(|v| v.to_str())
            .unwrap_or("file")
            .to_string();
        items.push(QueueItem {
            id: uuid::Uuid::new_v4().to_string(),
            name: name.clone(),
            path: path_to_string(path),
            kind: kind_from_name(&name),
        });
    }
    Ok(items)
}

#[tauri::command]
fn pick_folder() -> Result<Vec<QueueItem>> {
    let path = rfd::FileDialog::new()
        .pick_folder()
        .map(path_to_string)
        .unwrap_or_default();

    if path.is_empty() {
        return Ok(Vec::new());
    }

    Ok(vec![QueueItem {
        id: uuid::Uuid::new_v4().to_string(),
        name: "folder_item.jpg".to_string(),
        path,
        kind: "photo".to_string(),
    }])
}

#[tauri::command]
fn pick_output() -> Result<String> {
    let path = rfd::FileDialog::new()
        .pick_folder()
        .map(path_to_string)
        .unwrap_or_default();
    Ok(path)
}

#[tauri::command]
fn open_output(path: String) -> Result<()> {
    if path.is_empty() {
        return Ok(());
    }

    #[cfg(target_os = "macos")]
    {
        let _ = std::process::Command::new("open").arg(path).status();
    }
    #[cfg(target_os = "windows")]
    {
        let _ = std::process::Command::new("explorer").arg(path).status();
    }
    #[cfg(target_os = "linux")]
    {
        let _ = std::process::Command::new("xdg-open").arg(path).status();
    }

    Ok(())
}

#[tauri::command]
fn open_settings_window(app: AppHandle) -> Result<()> {
    if let Some(window) = app.get_webview_window("settings") {
        let _ = window.show();
        let _ = window.set_focus();
        return Ok(());
    }

    let _ = WebviewWindowBuilder::new(
        &app,
        "settings",
        WebviewUrl::App("index.html?settings=1".into()),
    )
    .title("Налаштування")
    .inner_size(860.0, 760.0)
    .resizable(true)
    .build();

    Ok(())
}

#[tauri::command]
fn pick_ffmpeg() -> Result<String> {
    let path = rfd::FileDialog::new()
        .pick_file()
        .map(path_to_string)
        .unwrap_or_default();
    Ok(path)
}

#[tauri::command]
fn check_ffmpeg() -> Result<bool> {
    Ok(true)
}

#[tauri::command]
fn start_conversion(ffmpeg_path: String, output_dir: String) -> Result<()> {
    let _ = (ffmpeg_path, output_dir);
    Ok(())
}

#[tauri::command]
fn stop_conversion() -> Result<()> {
    Ok(())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            pick_files,
            pick_folder,
            pick_output,
            open_output,
            open_settings_window,
            pick_ffmpeg,
            check_ffmpeg,
            start_conversion,
            stop_conversion
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
