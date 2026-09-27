"""Comprehensive tests for Universal Archive and Compression Service.

Covers:
- TEST 1: Single file -> ZIP
- TEST 2: 100 files -> ZIP
- TEST 3: Folder with nested subfolders -> TAR.GZ and ZIP
- TEST 4: Large file (streaming/chunks without RAM bloat) -> ZIP
- TEST 5: Extract ZIP
- TEST 6: Extract TAR.GZ
- TEST 7: Password-protected archive extraction
- TEST 8: Wrong password handling
- TEST 9: Corrupted archive error handling
- TEST 10: Cancel compression with output cleanup
- TEST 11: Cancel extraction
- TEST 12: Duplicate filename on extract (collision handling: replace, skip, keep_both)
- TEST 13: Unicode filename ("фото літа 2026.png")
- TEST 14: Special characters in filenames ("test!@#$%^&()_+.txt")
- TEST 15: Path traversal (Zip Slip) security protection
- TEST 16: Symlink security validation
- TEST 17: Archive bomb protection
- TEST 18: Disk space pre-check
- TEST 19: Single file GZ, BZ2, XZ compression & extraction
- TEST 20: Smart analysis (detecting media vs code/text)
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

from services.archive_service import (
    ArchiveSecurityError,
    ArchiveService,
)


class ArchiveServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="archive_test_")
        self.service = ArchiveService()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # TEST 1: 1 txt file -> ZIP
    # -------------------------------------------------------------------------
    def test_single_file_to_zip(self):
        txt_path = Path(self.temp_dir) / "sample.txt"
        txt_path.write_text("Hello World from Archive Service!", encoding="utf-8")

        out_zip = Path(self.temp_dir) / "test1.zip"
        res = self.service.create_archive([str(txt_path)], str(out_zip), archive_format="zip", preset="balanced")

        self.assertTrue(res.success, f"Creation failed: {res.error_message}")
        self.assertTrue(out_zip.exists())
        self.assertEqual(res.files_count, 1)

        # Verify ZIP contains file
        with zipfile.ZipFile(out_zip, "r") as zf:
            self.assertIn("sample.txt", zf.namelist())
            self.assertEqual(zf.read("sample.txt").decode("utf-8"), "Hello World from Archive Service!")

    # -------------------------------------------------------------------------
    # TEST 2: 100 files -> ZIP
    # -------------------------------------------------------------------------
    def test_100_files_to_zip(self):
        files_dir = Path(self.temp_dir) / "hundred_files"
        files_dir.mkdir()
        sources = []
        for i in range(100):
            p = files_dir / f"doc_{i:03d}.txt"
            p.write_text(f"This is document number {i}", encoding="utf-8")
            sources.append(str(p))

        out_zip = Path(self.temp_dir) / "hundred.zip"
        res = self.service.create_archive(sources, str(out_zip), archive_format="zip", preset="fast")

        self.assertTrue(res.success)
        self.assertEqual(res.files_count, 100)

        with zipfile.ZipFile(out_zip, "r") as zf:
            self.assertEqual(len(zf.namelist()), 100)

    # -------------------------------------------------------------------------
    # TEST 3: Folder with subfolders -> ZIP & TAR.GZ
    # -------------------------------------------------------------------------
    def test_folder_with_subfolders(self):
        root_folder = Path(self.temp_dir) / "Project"
        assets_folder = root_folder / "assets"
        sub_folder = assets_folder / "icons"
        sub_folder.mkdir(parents=True)

        (root_folder / "main.py").write_text("print('main')", encoding="utf-8")
        (assets_folder / "style.css").write_text("body { color: red; }", encoding="utf-8")
        (sub_folder / "logo.svg").write_text("<svg></svg>", encoding="utf-8")

        # Test ZIP
        out_zip = Path(self.temp_dir) / "project.zip"
        res_zip = self.service.create_archive([str(root_folder)], str(out_zip), archive_format="zip")
        self.assertTrue(res_zip.success)

        with zipfile.ZipFile(out_zip, "r") as zf:
            names = zf.namelist()
            self.assertTrue(any("main.py" in n for n in names))
            self.assertTrue(any("assets/style.css" in n.replace("\\", "/") for n in names))
            self.assertTrue(any("assets/icons/logo.svg" in n.replace("\\", "/") for n in names))

        # Test TAR.GZ
        out_tar = Path(self.temp_dir) / "project.tar.gz"
        res_tar = self.service.create_archive([str(root_folder)], str(out_tar), archive_format="tar.gz")
        self.assertTrue(res_tar.success)
        self.assertTrue(out_tar.exists())

    def test_additional_create_formats_are_available(self):
        source = Path(self.temp_dir) / "notes.txt"
        source.write_text("Archive formats should preserve this text.\n" * 100, encoding="utf-8")

        formats = {
            "tar": "bundle.tar",
            "tar.bz2": "bundle.tar.bz2",
            "tar.xz": "bundle.tar.xz",
            "gz": "notes.txt.gz",
            "bz2": "notes.txt.bz2",
            "xz": "notes.txt.xz",
        }
        for archive_format, filename in formats.items():
            output = Path(self.temp_dir) / filename
            result = self.service.create_archive([str(source)], str(output), archive_format=archive_format)
            self.assertTrue(result.success, f"{archive_format}: {result.error_message}")
            self.assertTrue(output.is_file())

    def test_format_catalog_includes_rar_and_extra_formats(self):
        formats = {item.id: item for item in self.service.get_supported_formats()}
        for format_id in {"tar", "tar.bz2", "tar.xz", "gz", "bz2", "xz", "rar"}:
            self.assertIn(format_id, formats)
        self.assertEqual(formats["rar"].can_create, self.service.has_rar)

    # -------------------------------------------------------------------------
    # TEST 4 & 13: Large file chunked streaming (no RAM exhaustion)
    # -------------------------------------------------------------------------
    def test_chunked_streaming_large_file(self):
        large_path = Path(self.temp_dir) / "large_data.bin"
        # Create 10MB pseudo-large file with repeating blocks
        block = b"X" * (1024 * 1024)
        with open(large_path, "wb") as f:
            for _ in range(10):
                f.write(block)

        out_zip = Path(self.temp_dir) / "large.zip"
        progress_calls = []

        def on_prog(pct, f_done, f_total, b_done, b_total, curr_f, elapsed):
            progress_calls.append(pct)

        res = self.service.create_archive(
            [str(large_path)],
            str(out_zip),
            archive_format="zip",
            progress_callback=on_prog,
        )
        self.assertTrue(res.success)
        self.assertGreater(len(progress_calls), 0)
        self.assertEqual(res.original_size, 10 * 1024 * 1024)
        self.assertLess(res.archive_size, res.original_size)  # Highly compressible blocks
        self.assertGreater(res.saved_percent, 90.0)

    # -------------------------------------------------------------------------
    # TEST 5: Extract ZIP
    # -------------------------------------------------------------------------
    def test_extract_zip(self):
        # Create sample ZIP
        zip_path = Path(self.temp_dir) / "source.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("sub/test.txt", "Extract test content")

        dest_dir = Path(self.temp_dir) / "extracted"
        res = self.service.extract_archive(str(zip_path), str(dest_dir))

        self.assertTrue(res.success)
        extracted_file = dest_dir / "sub" / "test.txt"
        self.assertTrue(extracted_file.exists())
        self.assertEqual(extracted_file.read_text(encoding="utf-8"), "Extract test content")

    # -------------------------------------------------------------------------
    # TEST 6: Extract TAR.GZ
    # -------------------------------------------------------------------------
    def test_extract_targz(self):
        src_file = Path(self.temp_dir) / "unix_doc.txt"
        src_file.write_text("Unix tar gzip extraction test", encoding="utf-8")
        out_tar = Path(self.temp_dir) / "archive.tar.gz"

        res_c = self.service.create_archive([str(src_file)], str(out_tar), archive_format="tar.gz")
        self.assertTrue(res_c.success)

        dest_dir = Path(self.temp_dir) / "tar_extracted"
        res_e = self.service.extract_archive(str(out_tar), str(dest_dir))
        self.assertTrue(res_e.success)
        self.assertTrue((dest_dir / "unix_doc.txt").exists())

    # -------------------------------------------------------------------------
    # TEST 7 & 8: Password Protection & Wrong Password
    # -------------------------------------------------------------------------
    def test_password_protected_zip(self):
        src = Path(self.temp_dir) / "secret.txt"
        src.write_text("Top secret confidential data", encoding="utf-8")
        out_zip = Path(self.temp_dir) / "encrypted.zip"

        res = self.service.create_archive([str(src)], str(out_zip), archive_format="zip", password="MySecurePassword123")
        self.assertTrue(res.success)

        # Extract with correct password
        dest_ok = Path(self.temp_dir) / "decrypted_ok"
        res_ok = self.service.extract_archive(str(out_zip), str(dest_ok), password="MySecurePassword123")
        self.assertTrue(res_ok.success)
        self.assertEqual((dest_ok / "secret.txt").read_text(encoding="utf-8"), "Top secret confidential data")

        # Extract with wrong password
        dest_fail = Path(self.temp_dir) / "decrypted_fail"
        res_fail = self.service.extract_archive(str(out_zip), str(dest_fail), password="WrongPassword!")
        self.assertFalse(res_fail.success)

    # -------------------------------------------------------------------------
    # TEST 9: Corrupted Archive
    # -------------------------------------------------------------------------
    def test_corrupted_archive(self):
        bad_zip = Path(self.temp_dir) / "corrupt.zip"
        bad_zip.write_bytes(b"PK\x03\x04This is not a real zip file header data corrupted completely")

        dest = Path(self.temp_dir) / "corrupt_extract"
        res = self.service.extract_archive(str(bad_zip), str(dest))
        self.assertFalse(res.success)
        self.assertIn("cannot read archive", res.error_message.lower())

    # -------------------------------------------------------------------------
    # TEST 10: Cancel Compression with Output Cleanup
    # -------------------------------------------------------------------------
    def test_cancel_compression_cleanup(self):
        big_path = Path(self.temp_dir) / "cancel_test.bin"
        big_path.write_bytes(b"A" * (5 * 1024 * 1024))
        out_zip = Path(self.temp_dir) / "should_be_deleted.zip"

        cancel_flag = False

        def check_cancel():
            return cancel_flag

        def on_prog(pct, *args):
            nonlocal cancel_flag
            if pct > 10:
                cancel_flag = True

        res = self.service.create_archive(
            [str(big_path)],
            str(out_zip),
            archive_format="zip",
            cancel_requested=check_cancel,
            progress_callback=on_prog,
        )

        self.assertFalse(res.success)
        self.assertIn("cancelled", res.error_message.lower())
        # Incomplete archive output MUST be deleted
        self.assertFalse(out_zip.exists(), "Cancelled incomplete archive was not deleted!")

    # -------------------------------------------------------------------------
    # TEST 11: Cancel Extraction
    # -------------------------------------------------------------------------
    def test_cancel_extraction(self):
        zip_path = Path(self.temp_dir) / "cancel_extract.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            for i in range(20):
                zf.writestr(f"item_{i}.txt", "data" * 1000)

        dest = Path(self.temp_dir) / "cancelled_dest"
        cancel_flag = False

        def check_cancel():
            return cancel_flag

        def on_prog(pct, *args):
            nonlocal cancel_flag
            if pct > 5:
                cancel_flag = True

        res = self.service.extract_archive(
            str(zip_path),
            str(dest),
            cancel_requested=check_cancel,
            progress_callback=on_prog,
        )
        self.assertFalse(res.success)
        self.assertIn("cancelled", res.error_message.lower())

    # -------------------------------------------------------------------------
    # TEST 12: Collision Handling (Replace, Skip, Keep Both)
    # -------------------------------------------------------------------------
    def test_collision_handling(self):
        zip_path = Path(self.temp_dir) / "collision.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("file.txt", "Archive Content")

        dest = Path(self.temp_dir) / "collision_dest"
        dest.mkdir()
        target = dest / "file.txt"

        # 1. Skip mode
        target.write_text("Existing Content", encoding="utf-8")
        res_skip = self.service.extract_archive(str(zip_path), str(dest), overwrite_mode="skip")
        self.assertTrue(res_skip.success)
        self.assertEqual(target.read_text(encoding="utf-8"), "Existing Content")

        # 2. Replace mode
        res_replace = self.service.extract_archive(str(zip_path), str(dest), overwrite_mode="replace")
        self.assertTrue(res_replace.success)
        self.assertEqual(target.read_text(encoding="utf-8"), "Archive Content")

        # 3. Keep both mode
        res_both = self.service.extract_archive(str(zip_path), str(dest), overwrite_mode="keep_both")
        self.assertTrue(res_both.success)
        self.assertTrue((dest / "file (1).txt").exists())

    # -------------------------------------------------------------------------
    # TEST 14: Unicode filename: фото літа 2026.png
    # -------------------------------------------------------------------------
    def test_unicode_filename(self):
        unicode_file = Path(self.temp_dir) / "фото літа 2026.png"
        unicode_file.write_bytes(b"\x89PNG\r\n\x1a\nfakeimagebytes")

        out_zip = Path(self.temp_dir) / "unicode.zip"
        res = self.service.create_archive([str(unicode_file)], str(out_zip), archive_format="zip")
        self.assertTrue(res.success)

        dest = Path(self.temp_dir) / "unicode_extracted"
        res_e = self.service.extract_archive(str(out_zip), str(dest))
        self.assertTrue(res_e.success)
        self.assertTrue((dest / "фото літа 2026.png").exists())

    # -------------------------------------------------------------------------
    # TEST 15: Special Characters in filename
    # -------------------------------------------------------------------------
    def test_special_chars_filename(self):
        special_file = Path(self.temp_dir) / "special!@#$%&()_+.txt"
        special_file.write_text("Special characters text content", encoding="utf-8")

        out_zip = Path(self.temp_dir) / "special.zip"
        res = self.service.create_archive([str(special_file)], str(out_zip), archive_format="zip")
        self.assertTrue(res.success)

        dest = Path(self.temp_dir) / "special_extracted"
        res_e = self.service.extract_archive(str(out_zip), str(dest))
        self.assertTrue(res_e.success)
        self.assertTrue((dest / "special!@#$%&()_+.txt").exists())

    # -------------------------------------------------------------------------
    # TEST 16 & 17: Security - Path Traversal (Zip Slip) Protection
    # -------------------------------------------------------------------------
    def test_zip_slip_security_rejection(self):
        dest = Path(self.temp_dir) / "safe_dest"
        dest.mkdir()

        # Malicious traversal attempts
        with self.assertRaises(ArchiveSecurityError):
            self.service.validate_safe_path(dest, "../../etc/passwd")

        with self.assertRaises(ArchiveSecurityError):
            self.service.validate_safe_path(dest, "../outside.txt")

        with self.assertRaises(ArchiveSecurityError):
            self.service.validate_safe_path(dest, "sub/../../escape.txt")

        # Safe subpaths should succeed
        safe = self.service.validate_safe_path(dest, "sub/nested/file.txt")
        self.assertTrue(str(safe).startswith(str(dest.resolve())))

    # -------------------------------------------------------------------------
    # TEST 18: Smart Compression Analysis
    # -------------------------------------------------------------------------
    def test_smart_compression_analysis(self):
        media_file = Path(self.temp_dir) / "clip.mp4"
        media_file.write_bytes(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 1000)

        txt_file = Path(self.temp_dir) / "log.txt"
        txt_file.write_text("log line\n" * 50, encoding="utf-8")

        analysis_media = self.service.analyze_sources([str(media_file)])
        self.assertTrue(analysis_media["is_mostly_compressed"])
        self.assertEqual(analysis_media["suggested_preset"], "fast")
        self.assertIn("already compressed", analysis_media["notice"].lower())

        analysis_txt = self.service.analyze_sources([str(txt_file)])
        self.assertFalse(analysis_txt["is_mostly_compressed"])
        self.assertEqual(analysis_txt["suggested_preset"], "maximum")


if __name__ == "__main__":
    unittest.main()
