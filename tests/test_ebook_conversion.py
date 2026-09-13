import struct
import tempfile
import zipfile
from pathlib import Path

from services.text_conversion_service import (
    _write_epub,
    _write_fb2,
    convert_text_file,
    read_text_file,
)


def test_fb2_read_and_write():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        source = tmp / "sample.txt"
        source.write_text("Chapter 1: The Beginning\n\nOnce upon a time in a digital world.\nAnother line here.", encoding="utf-8")

        fb2_path = tmp / "book.fb2"
        _write_fb2(source.read_text(encoding="utf-8"), fb2_path, source)
        assert fb2_path.exists()

        text, fmt = read_text_file(fb2_path)
        assert fmt == "fb2"
        assert "Once upon a time in a digital world." in text


def test_epub_read_and_write():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        source = tmp / "book_source.txt"
        source.write_text("Introduction\n\nThis is an EPUB electronic book test.\nSecond paragraph.", encoding="utf-8")

        epub_path = tmp / "output.epub"
        _write_epub(source.read_text(encoding="utf-8"), epub_path, source)
        assert epub_path.exists()

        # Verify ZIP structure
        with zipfile.ZipFile(epub_path) as zf:
            names = zf.namelist()
            assert "mimetype" in names
            assert "META-INF/container.xml" in names
            assert "OEBPS/content.opf" in names

        # Read back
        text, fmt = read_text_file(epub_path)
        assert fmt == "epub"
        assert "This is an EPUB electronic book test." in text


def test_mobi_read_synthetic_palmdoc():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        mobi_path = tmp / "test.mobi"

        # Construct minimal PalmDOC / MOBI binary file
        header = bytearray(78)
        header[0:4] = b"MOBI"
        num_records = 2
        struct.pack_into(">H", header, 76, num_records)

        # Record info list (2 records * 8 bytes)
        rec_list = bytearray(num_records * 8)
        rec0_offset = 78 + len(rec_list)
        rec1_offset = rec0_offset + 16
        struct.pack_into(">I", rec_list, 0, rec0_offset)
        struct.pack_into(">I", rec_list, 8, rec1_offset)

        # Record 0: PalmDOC header (compression=1 uncompressed, 1 text record)
        rec0 = bytearray(16)
        struct.pack_into(">H2sIH2s", rec0, 0, 1, b"\x00\x00", 0, 1, b"\x00\x00")

        # Record 1: Text data
        content = b"<html><body><p>Hello from Mobipocket format!</p></body></html>"
        full_data = header + rec_list + rec0 + content
        mobi_path.write_bytes(full_data)

        text, fmt = read_text_file(mobi_path)
        assert fmt == "mobi"
        assert "Hello from Mobipocket format!" in text


def test_convert_ebook_to_txt_and_docx():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        source = tmp / "story.txt"
        source.write_text("Hello World\n\nChapter One\nIt was a dark and stormy night.", encoding="utf-8")

        epub_file = tmp / "story.epub"
        _write_epub(source.read_text(encoding="utf-8"), epub_file, source)

        txt_out = tmp / "converted.txt"
        convert_text_file(epub_file, txt_out, "txt")
        assert txt_out.exists()
        assert "Chapter One" in txt_out.read_text(encoding="utf-8")

        docx_out = tmp / "converted.docx"
        convert_text_file(epub_file, docx_out, "docx")
        assert docx_out.exists()
        assert docx_out.stat().st_size > 0
