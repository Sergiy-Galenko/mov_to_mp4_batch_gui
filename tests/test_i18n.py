import json
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


if __name__ == "__main__":
    unittest.main()
