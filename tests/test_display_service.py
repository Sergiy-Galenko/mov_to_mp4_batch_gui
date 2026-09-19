from __future__ import annotations

import unittest
from pathlib import Path

from PySide6 import QtWidgets

from services.display_service import (
    DisplayService,
    ScreenMetrics,
    calculate_screen_metrics,
    classify_display,
)
from services.theme_manager import ThemeManager


class DisplayServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import os

        from PySide6.QtQuickControls2 import QQuickStyle

        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        os.environ.setdefault("QT_QUICK_CONTROLS_STYLE", "Basic")
        QQuickStyle.setStyle("Basic")
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    def test_classify_display_categories(self) -> None:
        # Compact / small screen (laptop with scaling or small display)
        cat, is_port, is_ultra = classify_display(1100, 700, dpr=1.25)
        self.assertEqual(cat, "compact")
        self.assertFalse(is_port)
        self.assertFalse(is_ultra)

        # Standard 1080p desktop (available area 1920x1040)
        cat, is_port, is_ultra = classify_display(1920, 1040, dpr=1.0)
        self.assertEqual(cat, "standard")
        self.assertFalse(is_port)
        self.assertFalse(is_ultra)

        # Large 2K / 4K display (available area 2560x1400)
        cat, is_port, is_ultra = classify_display(2560, 1400, dpr=1.0)
        self.assertEqual(cat, "large")
        self.assertFalse(is_port)
        self.assertFalse(is_ultra)

        # Ultrawide (3440x1400)
        cat, is_port, is_ultra = classify_display(3440, 1400, dpr=1.0)
        self.assertEqual(cat, "ultrawide")
        self.assertFalse(is_port)
        self.assertTrue(is_ultra)

        # Portrait monitor (1080x1920)
        cat, is_port, is_ultra = classify_display(1080, 1880, dpr=1.0)
        self.assertTrue(is_port)

    def test_calculate_screen_metrics_compact(self) -> None:
        metrics = calculate_screen_metrics(
            screen_width=1280,
            screen_height=720,
            available_width=1100,
            available_height=680,
            available_x=0,
            available_y=0,
            dpr=1.25,
            logical_dpi=120.0,
            physical_dpi=120.0,
        )
        self.assertEqual(metrics.category, "compact")
        self.assertEqual(metrics.recommended_layout_mode, "compact")
        self.assertTrue(metrics.recommended_sidebar_collapsed)
        self.assertLessEqual(metrics.recommended_font_scale, 0.95)
        self.assertLessEqual(metrics.recommended_window_width, 1100)
        self.assertLessEqual(metrics.recommended_window_height, 680)
        # Verify centered
        expected_x = (1100 - metrics.recommended_window_width) // 2
        self.assertEqual(metrics.recommended_window_x, expected_x)

    def test_calculate_screen_metrics_standard(self) -> None:
        metrics = calculate_screen_metrics(
            screen_width=1920,
            screen_height=1080,
            available_width=1920,
            available_height=1040,
            available_x=0,
            available_y=0,
            dpr=1.0,
            logical_dpi=96.0,
            physical_dpi=96.0,
        )
        self.assertEqual(metrics.category, "standard")
        self.assertEqual(metrics.recommended_layout_mode, "comfortable")
        self.assertFalse(metrics.recommended_sidebar_collapsed)
        self.assertEqual(metrics.recommended_font_scale, 1.0)
        self.assertGreaterEqual(metrics.recommended_window_width, 800)
        self.assertLessEqual(metrics.recommended_window_width, 1400)

    def test_screen_metrics_dict_export(self) -> None:
        metrics = ScreenMetrics(
            screen_width=1920,
            screen_height=1080,
            available_width=1920,
            available_height=1040,
        )
        d = metrics.to_dict()
        self.assertIn("screenWidth", d)
        self.assertIn("screenHeight", d)
        self.assertIn("availableWidth", d)
        self.assertIn("availableHeight", d)
        self.assertIn("devicePixelRatio", d)
        self.assertIn("category", d)
        self.assertIn("recommendedLayoutMode", d)
        self.assertIn("recommendedWindowWidth", d)

    def test_ensure_window_in_bounds_offscreen_recovery(self) -> None:
        service = DisplayService()
        # Simulated offscreen coordinates (e.g. was on a second monitor at x=3000, y=2000)
        recovered_x, recovered_y, _w, _h = service.ensure_window_in_bounds(3000, 2000, 1200, 800)
        # Should be brought back within active screen area
        self.assertLess(recovered_x, service.current_metrics().available_width)
        self.assertLess(recovered_y, service.current_metrics().available_height)
        self.assertGreaterEqual(recovered_x, 0)
        self.assertGreaterEqual(recovered_y, 0)

    def test_theme_manager_auto_display_adaptation(self) -> None:
        test_path = Path("scratch_display_theme.json")
        tm = ThemeManager(test_path)
        try:
            self.assertTrue(tm.auto_display_adaptation())
            tm.set_auto_display_adaptation(False)
            self.assertFalse(tm.auto_display_adaptation())
            tm.set_auto_display_adaptation(True)
            self.assertTrue(tm.auto_display_adaptation())

            # Layout mode can be set to 'auto'
            tm.set_layout_mode("auto")
            self.assertEqual(tm.layout_mode(), "auto")
        finally:
            test_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()

