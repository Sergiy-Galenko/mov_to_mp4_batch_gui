import zipfile

from app.constants import OUT_TEXT_FORMATS
from services.text_conversion_service import SUPPORTED_TEXT_FORMATS, convert_text_file, read_text_file


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
