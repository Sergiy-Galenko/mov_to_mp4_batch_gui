import random
import zipfile

import pytest

from app.constants import OUT_TEXT_FORMATS
from services import native_acceleration
from services.text_conversion_service import (
    SUPPORTED_TEXT_FORMATS,
    _read_rtf,
    _to_rtf,
    _to_rtf_python,
    _unescape_pdf_literal,
    _unescape_pdf_literal_python,
    convert_text_file,
    read_text_file,
)


def test_configured_text_formats_are_supported_by_converter() -> None:
    assert set(OUT_TEXT_FORMATS) <= SUPPORTED_TEXT_FORMATS


def test_text_converter_writes_document_spreadsheet_and_presentation_formats(tmp_path) -> None:
    source = tmp_path / "notes.txt"
    source.write_text("alpha\nbeta,gamma\n", encoding="utf-8")

    for fmt in OUT_TEXT_FORMATS:
        output = tmp_path / f"notes.{fmt}"
        convert_text_file(source, output, fmt)
        assert output.exists(), fmt
        assert output.stat().st_size > 0, fmt

    assert (tmp_path / "notes.pdf").read_bytes().startswith(b"%PDF-")
    assert (tmp_path / "notes.doc").read_text(encoding="utf-8").startswith("{\\rtf1")
    assert "<table>" in (tmp_path / "notes.xls").read_text(encoding="utf-8")
    assert "<section>" in (tmp_path / "notes.ppt").read_text(encoding="utf-8")

    for fmt, member in {
        "docx": "word/document.xml",
        "xlsx": "xl/worksheets/sheet1.xml",
        "pptx": "ppt/slides/slide1.xml",
        "odt": "content.xml",
        "ods": "content.xml",
        "odp": "content.xml",
    }.items():
        with zipfile.ZipFile(tmp_path / f"notes.{fmt}") as zf:
            assert member in zf.namelist()


def test_generated_modern_documents_can_be_read_back(tmp_path) -> None:
    source = tmp_path / "notes.txt"
    source.write_text("alpha\nbeta\tgamma\n", encoding="utf-8")

    for fmt in ["docx", "xlsx", "pptx", "odt", "ods", "odp"]:
        output = tmp_path / f"notes.{fmt}"
        convert_text_file(source, output, fmt)
        text, detected = read_text_file(output)
        assert detected
        assert "alpha" in text


@pytest.mark.parametrize("text", ["", "Hello {world} \\", "Українська\nPolski\tDeutsch", "Emoji 🦀🎬😀\n漢字", "\x00\r\t\x7f"])
def test_rtf_roundtrip_and_fallback(text, tmp_path, monkeypatch):
    expected = _to_rtf_python(text)
    assert _to_rtf(text) == expected
    # Raw CR is a formatting delimiter in RTF, so test text roundtrip separately.
    if "\r" not in text:
        path = tmp_path / "text.rtf"
        path.write_text(expected, encoding="ascii")
        assert _read_rtf(path) == text
    monkeypatch.setattr(native_acceleration, "native", None)
    assert _to_rtf(text) == expected


def test_native_matches_python_for_random_binary_pdf_literals():
    native = native_acceleration.native
    if native is None:
        pytest.skip("Build native/ to exercise Rust/Python parity")
    rng = random.Random(42)
    samples = [bytes(range(256)), b"\\n\\r\\t\\b\\f\\777\\123\\12\\1\\8\\z\\(\\)\\\\", b"a\\\r\nb\\\nc\\"]
    samples += [rng.randbytes(rng.randrange(2048)) for _ in range(100)]
    for data in samples:
        assert native.unescape_pdf_literal(data) == _unescape_pdf_literal_python(data)


def test_native_matches_python_for_unicode_rtf():
    native = native_acceleration.native
    if native is None:
        pytest.skip("Build native/ to exercise Rust/Python parity")
    rng = random.Random(21)
    text = "".join(chr(rng.choice([rng.randrange(0xD800), rng.randrange(0xE000, 0x110000)])) for _ in range(10000))
    assert native.to_rtf(text) == _to_rtf_python(text)


def test_pdf_fallback(monkeypatch):
    monkeypatch.setattr(native_acceleration, "native", None)
    assert _unescape_pdf_literal(b"a\\n\\050b\\051\\777") == b"a\n(b)\xff"
