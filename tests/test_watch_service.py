import tempfile
import time
import unittest
from pathlib import Path

from services.watch_service import WatchService


class WatchServiceTest(unittest.TestCase):
    def test_scan_once_emits_only_after_debounce(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            folder = Path(tmpdir)
            service = WatchService(debounce_sec=0.05)
            service._folder = folder
            service._seen = set()

            source = folder / "clip.mp4"
            source.write_text("partial", encoding="utf-8")

            self.assertEqual(service.scan_once(), [])
            time.sleep(0.06)

            self.assertEqual(service.scan_once(), [source.resolve()])


if __name__ == "__main__":
    unittest.main()
