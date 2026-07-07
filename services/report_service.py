"""Session report exporter.

Exports conversion session results as CSV or JSON for post-processing or archival.
"""

from __future__ import annotations

import csv
import html
import io
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional


class ReportService:
    """Generates session reports in CSV and JSON formats."""

    @staticmethod
    def to_csv(
        results: List[Dict[str, Any]],
        *,
        settings: Optional[Dict[str, Any]] = None,
        output_dir: str = "",
        started_at: Optional[float] = None,
    ) -> str:
        """Render session results as a CSV string."""
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")

        # Header
        writer.writerow([
            "Файл",
            "Статус",
            "Повідомлення",
            "Вихідний файл",
        ])

        for result in results:
            writer.writerow([
                result.get("path", ""),
                result.get("status", ""),
                result.get("message", ""),
                result.get("output_path", ""),
            ])

        # Summary footer
        total = len(results)
        success = sum(1 for r in results if r.get("status") == "success")
        failed = sum(1 for r in results if r.get("status") == "failed")
        skipped = sum(1 for r in results if r.get("status") == "skipped")
        writer.writerow([])
        writer.writerow(["Всього", total])
        writer.writerow(["Успішно", success])
        writer.writerow(["Помилок", failed])
        writer.writerow(["Пропущено", skipped])
        if output_dir:
            writer.writerow(["Папка виводу", output_dir])
        if started_at:
            writer.writerow(["Час запуску", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(started_at))])

        return output.getvalue()

    @staticmethod
    def to_json(
        results: List[Dict[str, Any]],
        *,
        settings: Optional[Dict[str, Any]] = None,
        output_dir: str = "",
        started_at: Optional[float] = None,
    ) -> str:
        """Render session results as a formatted JSON string."""
        total = len(results)
        success = sum(1 for r in results if r.get("status") == "success")
        failed = sum(1 for r in results if r.get("status") == "failed")
        skipped = sum(1 for r in results if r.get("status") == "skipped")

        payload = {
            "version": 1,
            "exported_at": time.time(),
            "started_at": started_at,
            "output_dir": output_dir,
            "summary": {
                "total": total,
                "success": success,
                "failed": failed,
                "skipped": skipped,
            },
            "results": results,
        }
        if settings:
            payload["settings"] = settings

        return json.dumps(payload, ensure_ascii=False, indent=2)

    @staticmethod
    def to_html(
        results: List[Dict[str, Any]],
        *,
        settings: Optional[Dict[str, Any]] = None,
        output_dir: str = "",
        started_at: Optional[float] = None,
    ) -> str:
        """Render session results as a standalone HTML report."""
        total = len(results)
        success = sum(1 for r in results if r.get("status") == "success")
        failed = sum(1 for r in results if r.get("status") == "failed")
        skipped = sum(1 for r in results if r.get("status") == "skipped")
        started = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(started_at)) if started_at else ""
        rows = []
        for result in results:
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(result.get('path', '')))}</td>"
                f"<td>{html.escape(str(result.get('status', '')))}</td>"
                f"<td>{html.escape(str(result.get('message', '')))}</td>"
                f"<td>{html.escape(str(result.get('output_path', '')))}</td>"
                "</tr>"
            )
        return "\n".join(
            [
                "<!doctype html>",
                '<html lang="uk">',
                "<head>",
                '<meta charset="utf-8">',
                "<title>Conversion report</title>",
                "<style>",
                "body{font-family:Segoe UI,Arial,sans-serif;margin:24px;color:#18202a;background:#f7f8fa}",
                "table{width:100%;border-collapse:collapse;background:white}",
                "th,td{border:1px solid #d8dde6;padding:8px;text-align:left;font-size:13px}",
                "th{background:#eef2f7} .summary{display:flex;gap:12px;flex-wrap:wrap;margin:16px 0}",
                ".pill{background:white;border:1px solid #d8dde6;border-radius:6px;padding:8px 10px}",
                "</style>",
                "</head>",
                "<body>",
                "<h1>Conversion report</h1>",
                '<div class="summary">',
                f'<div class="pill">Всього: {total}</div>',
                f'<div class="pill">Успішно: {success}</div>',
                f'<div class="pill">Помилок: {failed}</div>',
                f'<div class="pill">Пропущено: {skipped}</div>',
                f'<div class="pill">Папка виводу: {html.escape(output_dir)}</div>' if output_dir else "",
                f'<div class="pill">Час запуску: {html.escape(started)}</div>' if started else "",
                "</div>",
                "<table><thead><tr><th>Файл</th><th>Статус</th><th>Повідомлення</th><th>Вихідний файл</th></tr></thead><tbody>",
                "\n".join(rows),
                "</tbody></table>",
                "</body></html>",
            ]
        )

    @staticmethod
    def export_file(
        path: Path,
        results: List[Dict[str, Any]],
        *,
        fmt: str = "csv",
        settings: Optional[Dict[str, Any]] = None,
        output_dir: str = "",
        started_at: Optional[float] = None,
    ) -> Path:
        """Export results to a file. Format can be 'csv', 'json', or 'html'.

        Returns the path to the exported file.
        """
        fmt = fmt.lower().strip()
        if fmt == "json":
            content = ReportService.to_json(
                results,
                settings=settings,
                output_dir=output_dir,
                started_at=started_at,
            )
        elif fmt in {"html", "htm"}:
            content = ReportService.to_html(
                results,
                settings=settings,
                output_dir=output_dir,
                started_at=started_at,
            )
        else:
            content = ReportService.to_csv(
                results,
                settings=settings,
                output_dir=output_dir,
                started_at=started_at,
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path
