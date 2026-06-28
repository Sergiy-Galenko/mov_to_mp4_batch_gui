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
        "analytics": "Analytics",
        "settings": "Settings",
        "start": "Start",
        "stop": "Stop",
        "status.pending": "pending",
        "status.processing": "processing",
        "status.done": "done",
        "status.failed": "failed"
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
