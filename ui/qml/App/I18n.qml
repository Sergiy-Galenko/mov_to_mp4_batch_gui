pragma Singleton
import QtQuick 2.15

QtObject {
    id: root

    property string language: "uk"
    property int revision: 0

    readonly property var languageCodes: ["uk", "en", "pl", "de"]
    readonly property var languageLabels: ({
        "uk": "Українська",
        "en": "English",
        "pl": "Polski",
        "de": "Deutsch"
    })
    readonly property var fallback: ({
        "app.title": "Media Converter",
        "language": "Language",
        "ukrainian": "Ukrainian",
        "english": "English",
        "polish": "Polish",
        "german": "German",
        "queue": "Queue",
        "queue_tools": "Queue tools",
        "queue_search": "Search queue",
        "errors_only": "Errors only",
        "failed_items": "Failed items",
        "analytics": "Analytics",
        "settings": "Settings",
        "downloads": "Downloads",
        "smart_convert": "Smart Convert",
        "smart_convert_enabled": "Enable Smart Convert",
        "smart_content_type": "Content type",
        "smart_quality_target": "Quality target",
        "smart_reencode_detection": "Smart remux",
        "smart_two_pass": "Two-pass target size",
        "smart_integrity_check": "Integrity check",
        "smart_quality_metric": "Quality metric",
        "smart_ab_test": "A/B samples",
        "smart_ab_crfs": "A/B CRF values",
        "smart_ab_duration": "A/B duration, sec",
        "smart_convert_hint": "Smart Convert analyzes each video and can choose codec, CRF and preset, remux compatible files, run two-pass target-size encoding, and check output quality after conversion.",
        "device_profiles": "Device profiles",
        "video_editor": "Video editor",
        "subtitle_tools": "Subtitle tools",
        "privacy_security": "Privacy / Security",
        "cloud_integration": "Cloud integration",
        "audio_codec": "Audio codec",
        "expand": "Expand",
        "collapse": "Collapse",
        "settings_panel_hint": "Settings are on the right. Start with format and output folder, then open advanced tools only when needed.",
        "advanced_settings": "Advanced settings",
        "advanced_settings_hint": "Video tools, audio, subtitles, watermark, metadata, privacy, cloud and FFmpeg/watch options.",
        "output_folder": "Output folder",
        "choose_output_folder": "Choose output folder",
        "output_folder_required": "Choose output folder first",
        "output_folder_required_detail": "Choose where converted files and URL downloads will be saved before starting.",
        "start": "Start",
        "convert_all": "Convert all",
        "quick_convert": "Quick convert",
        "quick_convert_hint": "Choose the output format for this file only.",
        "convert_this_file": "Convert this file",
        "save_format": "Save format",
        "youtube_download": "Video URL download",
        "youtube_url": "Video/source URL",
        "youtube_quality": "Quality",
        "youtube.preview_source": "Preview source",
        "download_video": "Download video",
        "download_audio": "Download audio",
        "enable_tray": "Enable tray",
        "push_notifications": "Push notifications",
        "update_ffmpeg": "Update FFmpeg",
        "selected_file": "Selected file",
        "media_type": "Media type",
        "output_format": "Output format",
        "cancel": "Cancel",
        "stop": "Stop",
        "open_output": "Open output",
        "status.pending": "pending",
        "status.processing": "processing",
        "status.done": "done",
        "status.failed": "failed",
        "whats_new_ebooks_title": "E-Books & Audiobooks",
        "whats_new_ebooks_body": "Full support for EPUB, FB2, MOBI: structural reading, conversion to PDF, DOCX, TXT, and generating audiobooks.",
        "whats_new_ocr_title": "OCR Text Recognition from Scans",
        "whats_new_ocr_body": "Extract text from images (PNG, JPG, TIFF, WebP) and scanned PDFs with export to TXT, DOCX, MD.",
        "whats_new_editor_title": "Visual Editing: Trim & Crop",
        "whats_new_editor_body": "Interactive timeline slider with dual In/Out markers and interactive visual crop frame directly over preview.",
        "whats_new_merge_loudnorm_title": "Media Merge & EBU R128 Loudness",
        "whats_new_merge_loudnorm_body": "Fast concatenation for audio/video files and two-pass EBU R128 loudness normalization.",
        "whats_new_apple_whisper_title": "Apple Silicon & Whisper Model Manager",
        "whats_new_apple_whisper_body": "VideoToolbox hardware acceleration on macOS M1-M4 and modal manager for Whisper AI models.",
        "montage_editor": "Montage Editor",
        "waveform_loading": "Loading waveform…",
        "crop": "Crop",
        "nav_montage": "Video montage"
    })

    Component.onCompleted: syncFromBackend()

    onLanguageChanged: {
        var normalized = normalize(language)
        if (language !== normalized) {
            language = normalized
            return
        }
        if (hasBackend() && backend.currentLanguage !== normalized)
            backend.setLanguage(normalized)
        revision += 1
    }

    property Connections backendConnection: Connections {
        target: root.hasBackend() ? backend : null
        function onLanguageChanged() {
            root.syncFromBackend()
        }
    }

    function hasBackend() {
        return typeof backend !== "undefined" && backend !== null
    }

    function normalize(code) {
        var normalized = String(code || "uk").toLowerCase()
        return languageCodes.indexOf(normalized) >= 0 ? normalized : "uk"
    }

    function labelFor(code) {
        var normalized = normalize(code)
        return languageLabels[normalized] || normalized
    }

    function setLanguage(code) {
        language = normalize(code)
    }

    function syncFromBackend() {
        if (!hasBackend())
            return
        var next = normalize(backend.currentLanguage || backend.uiLanguage)
        if (language !== next)
            language = next
        else
            revision += 1
    }

    function t(key) {
        var rev = revision
        if (hasBackend())
            return backend.tr(key)
        return fallback[key] || key
    }
}
