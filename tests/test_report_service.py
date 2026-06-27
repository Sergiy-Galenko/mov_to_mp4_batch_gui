import json
import tempfile
import unittest
from pathlib import Path

from services.report_service import ReportService


class ReportServiceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.results = [
            {"path": "/tmp/a.mp4", "status": "success", "message": "", "output_path": "/tmp/out/a.mp4"},
            {"path": "/tmp/b.mp4", "status": "failed", "message": "codec error", "output_path": ""},
            {"path": "/tmp/c.mp4", "status": "skipped", "message": "exists", "output_path": ""},
        ]

    def test_csv_output(self) -> None:
        csv = ReportService.to_csv(self.results, output_dir="/tmp/out", started_at=1700000000.0)
        self.assertIn("Файл", csv)
        self.assertIn("a.mp4", csv)
        self.assertIn("Успішно", csv)
        self.assertIn("1", csv)

    def test_json_output(self) -> None:
        raw = ReportService.to_json(self.results, output_dir="/tmp/out", started_at=1700000000.0)
        data = json.loads(raw)
        self.assertEqual(data["summary"]["total"], 3)
        self.assertEqual(data["summary"]["success"], 1)
        self.assertEqual(data["summary"]["failed"], 1)
        self.assertEqual(data["summary"]["skipped"], 1)

    def test_export_csv_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report.csv"
            result = ReportService.export_file(path, self.results, fmt="csv")
            self.assertTrue(result.exists())
            content = result.read_text(encoding="utf-8")
            self.assertIn("a.mp4", content)

    def test_export_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "report.json"
            result = ReportService.export_file(path, self.results, fmt="json")
            self.assertTrue(result.exists())
            data = json.loads(result.read_text(encoding="utf-8"))
            self.assertEqual(len(data["results"]), 3)

    def test_empty_results(self) -> None:
        csv = ReportService.to_csv([])
        self.assertIn("Всього", csv)
        raw = ReportService.to_json([])
        data = json.loads(raw)
        self.assertEqual(data["summary"]["total"], 0)


if __name__ == "__main__":
    unittest.main()
