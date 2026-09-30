import json
import re
import unittest
from pathlib import Path


class EditorI18nTest(unittest.TestCase):
    def test_every_static_editor_key_has_all_translations(self):
        root = Path(__file__).resolve().parents[1]
        qml_files = list((root / "ui" / "qml" / "editor").glob("*.qml")) + [
            root / "ui" / "qml" / "components" / "MontageEditorDialog.qml",
            root / "ui" / "qml" / "components" / "MontageMediaPool.qml",
            root / "ui" / "qml" / "components" / "MontageDualTimeline.qml",
        ]
        keys = set()
        for file in qml_files:
            keys.update(re.findall(r'I18n\.t\("(editor\.[^"]+)"', file.read_text()))

        for language in ("uk", "en", "pl", "de"):
            with self.subTest(language=language):
                dictionary = json.loads((root / "ui" / "i18n" / f"{language}.json").read_text())
                missing = sorted(key for key in keys if not dictionary.get(key))
                self.assertEqual(missing, [], f"Missing editor translations in {language}: {missing}")

    def test_dynamic_editor_keys_are_translated(self):
        root = Path(__file__).resolve().parents[1]
        expected = {
            "editor.all", "editor.video", "editor.audio", "editor.images",
            "editor.media", "editor.edit", "editor.color", "editor.titles",
            "editor.title", "editor.deliver", "editor.on", "editor.off",
            "editor.media_library", "editor.transitions",
            "editor.transition_cut", "editor.transition_fade", "editor.transition_dissolve",
            "editor.transition_wipe_left", "editor.transition_wipe_right",
            "editor.transition_slide_up", "editor.transition_slide_down", "editor.transition_circle",
            "editor.split", "editor.selection_tool", "editor.delete", "editor.zoom",
            "history.undo", "history.redo", "studio.play",
        }
        for language in ("uk", "en", "pl", "de"):
            with self.subTest(language=language):
                dictionary = json.loads((root / "ui" / "i18n" / f"{language}.json").read_text())
                self.assertEqual(sorted(key for key in expected if not dictionary.get(key)), [])
