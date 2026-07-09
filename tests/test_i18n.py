import json
import re
import unittest
from pathlib import Path


class I18nTest(unittest.TestCase):
    def test_translation_files_have_english_keys(self) -> None:
        i18n_dir = Path(__file__).resolve().parents[1] / "ui" / "i18n"
        english = json.loads((i18n_dir / "en.json").read_text(encoding="utf-8"))
        expected_keys = set(english)

        for language in ["uk", "pl", "de"]:
            with self.subTest(language=language):
                data = json.loads((i18n_dir / f"{language}.json").read_text(encoding="utf-8"))
                self.assertFalse(expected_keys - set(data))

    def test_qml_i18n_keys_exist(self) -> None:
        project_root = Path(__file__).resolve().parents[1]
        i18n_dir = project_root / "ui" / "i18n"
        english = json.loads((i18n_dir / "en.json").read_text(encoding="utf-8"))
        qml_paths = [project_root / "ui" / "qml" / "Main.qml"]
        qml_paths.extend((project_root / "ui" / "qml" / "components").glob("*.qml"))

        used_keys = set()
        for path in qml_paths:
            used_keys.update(re.findall(r'I18n\.t\("([^"]+)"\)', path.read_text(encoding="utf-8")))

        self.assertFalse(used_keys - set(english))


if __name__ == "__main__":
    unittest.main()
