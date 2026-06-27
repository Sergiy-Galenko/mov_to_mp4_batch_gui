pragma Singleton
import QtQuick 2.15

QtObject {
    id: root

    property string language: "uk"
    property int revision: 0
    property var translations: ({})

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

    Component.onCompleted: loadLanguage(language)
    onLanguageChanged: loadLanguage(language)

    function normalize(code) {
        var normalized = String(code || "uk").toLowerCase()
        return languageCodes.indexOf(normalized) >= 0 ? normalized : "uk"
    }

    function labelFor(code) {
        var normalized = normalize(code)
        return languageLabels[normalized] || normalized
    }

    function loadLanguage(code) {
        var normalized = normalize(code)
        if (language !== normalized) {
            language = normalized
            return
        }

        var next = ({})
        var xhr = new XMLHttpRequest()
        try {
            xhr.open("GET", Qt.resolvedUrl("translations/" + normalized + ".json"), false)
            xhr.send()
            if (xhr.status === 0 || (xhr.status >= 200 && xhr.status < 300))
                next = JSON.parse(xhr.responseText)
        } catch (e) {
            next = ({})
        }

        translations = next
        revision += 1
    }

    function t(key) {
        var lang = language
        var rev = revision
        return translations[key] || fallback[key] || key
    }
}
