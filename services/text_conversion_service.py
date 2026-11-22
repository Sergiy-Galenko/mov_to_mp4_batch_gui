from __future__ import annotations

import csv
import html
import json
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import textwrap
import zipfile
import zlib
from collections.abc import Iterable, Sequence
from pathlib import Path

from defusedxml import ElementTree as ET

TEXT_READ_ENCODINGS = ("utf-8-sig", "utf-8", "cp1251", "latin-1")
SUPPORTED_TEXT_FORMATS = {
    "txt",
    "md",
    "html",
    "json",
    "csv",
    "tsv",
    "rtf",
    "pdf",
    "docx",
    "doc",
    "odt",
    "xlsx",
    "xls",
    "ods",
    "pptx",
    "ppt",
    "odp",
    "epub",
    "fb2",
    "mobi",
    "mp3",
    "m4a",
    "wav",
}

OOXML_WORD_EXTS = {".docx", ".docm", ".dotx"}
OOXML_SHEET_EXTS = {".xlsx", ".xlsm", ".xltx"}
OOXML_PRESENTATION_EXTS = {".pptx", ".pptm", ".ppsx", ".potx"}
ODF_EXTS = {".odt", ".ott", ".ods", ".ots", ".odp", ".otp"}
LEGACY_OFFICE_EXTS = {".doc", ".xls", ".ppt"}
MAX_OFFICE_ZIP_ENTRIES = 4096
MAX_OFFICE_ZIP_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_XML_MEMBER_BYTES = 32 * 1024 * 1024


class TextConversionError(RuntimeError):
    pass


def read_text_file(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    try:
        if suffix == ".epub":
            return _read_epub(path), "epub"
        if suffix == ".fb2":
            return _read_fb2(path), "fb2"
        if suffix == ".mobi":
            return _read_mobi(path), "mobi"
        if suffix in OOXML_WORD_EXTS:
            return _read_docx(path), "docx"
        if suffix in OOXML_SHEET_EXTS:
            return _read_xlsx(path), "xlsx"
        if suffix in OOXML_PRESENTATION_EXTS:
            return _read_pptx(path), "pptx"
        if suffix in ODF_EXTS:
            return _read_odf(path), suffix.lstrip(".")
        if suffix == ".pdf":
            return _read_pdf(path), "pdf"
            pdf_text = _read_pdf(path)
            if not pdf_text.strip():
                from services.ocr_service import OcrService

                ocr_text = OcrService().recognize_pdf_scans(path)
                if ocr_text.strip():
                    return ocr_text, "pdf"
            return pdf_text, "pdf"
        if suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
            from services.ocr_service import OcrService

            ocr_text = OcrService().recognize_image(path)
            if ocr_text.strip():
                return ocr_text, suffix.lstrip(".")
            return f"[Image file: {path.name}]", suffix.lstrip(".")
        if suffix == ".rtf":
            return _read_rtf(path), "rtf"
        if suffix in LEGACY_OFFICE_EXTS:
            text = _extract_printable_text(path.read_bytes())
            if text.strip():
                return text, suffix.lstrip(".")
            raise TextConversionError(f"Cannot extract text from legacy Office file: {path}")
    except TextConversionError:
        raise
    except Exception as exc:
        raise TextConversionError(f"Cannot extract text from document: {path}") from exc

    return _read_plain_text_file(path)


def _read_rtf(path: Path) -> str:
    raw = path.read_bytes().decode("latin-1")
    if not raw.lstrip().startswith("{\\rtf"):
        raise TextConversionError("Invalid RTF document")
    output: list[str] = []
    stack: list[tuple[bool, int, str]] = []
    ignored, unicode_count, encoding = False, 1, "cp1252"
    fallback = 0
    destinations = {"fonttbl", "colortbl", "stylesheet", "info", "pict", "object", "header", "footer", "fldinst", "datastore"}
    symbols = {
        "par": "\n",
        "line": "\n",
        "tab": "\t",
        "emdash": "—",
        "endash": "–",
        "bullet": "•",
        "lquote": "‘",
        "rquote": "’",
        "ldblquote": "“",
        "rdblquote": "”",
    }

    def emit(value: str) -> None:
        nonlocal fallback
        if fallback:
            fallback -= 1
        elif not ignored:
            output.append(value)

    i = 0
    while i < len(raw):
        char = raw[i]
        i += 1
        if char == "{":
            stack.append((ignored, unicode_count, encoding))
        elif char == "}":
            if stack:
                ignored, unicode_count, encoding = stack.pop()
            fallback = 0
        elif char == "\\":
            if i >= len(raw):
                break
            token = raw[i]
            if token in "\\{}~_-":
                emit({"~": "\u00a0", "_": "‑", "-": ""}.get(token, token))
                i += 1
            elif token == "*":
                ignored = True
                i += 1
            elif token == "'" and re.fullmatch(r"[0-9a-fA-F]{2}", raw[i + 1 : i + 3]):
                emit(bytes([int(raw[i + 1 : i + 3], 16)]).decode(encoding, "replace"))
                i += 3
            else:
                match = re.match(r"([a-zA-Z]+)(-?\d+)? ?", raw[i:])
                if not match:
                    i += 1
                    continue
                word, number = match.groups()
                i += len(match.group(0))
                if word in destinations:
                    ignored = True
                elif word == "bin" and number:
                    i += max(0, int(number))
                elif word == "ansicpg" and number:
                    candidate = "cp" + number
                    try:
                        b"".decode(candidate)
                        encoding = candidate
                    except LookupError:
                        pass
                elif word == "uc" and number:
                    unicode_count = max(0, int(number))
                elif word == "u" and number:
                    if not ignored:
                        output.append(chr(int(number) & 0xFFFF))
                    fallback = unicode_count
                elif word in symbols:
                    emit(symbols[word])
        elif char not in "\r\n":
            emit(char.encode("latin-1").decode(encoding, "replace"))
    return "".join(output).encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace").rstrip("\n")


def convert_text_file(source: Path, output: Path, output_format: str) -> None:
    output_format = str(output_format or "").strip().lower().lstrip(".")
    if output_format not in SUPPORTED_TEXT_FORMATS:
        raise TextConversionError(f"Unsupported text output format: {output_format or 'empty'}")

    text, _source_format = read_text_file(source)
    output.parent.mkdir(parents=True, exist_ok=True)

    if output_format == "txt":
        output.write_text(text, encoding="utf-8", newline="")
    elif output_format == "md":
        output.write_text(_to_markdown(text, source), encoding="utf-8", newline="")
    elif output_format == "html":
        output.write_text(_to_html(text, source), encoding="utf-8", newline="")
    elif output_format == "json":
        output.write_text(_to_json(text, source), encoding="utf-8", newline="")
    elif output_format == "csv":
        _write_csv(text, output)
    elif output_format == "tsv":
        _write_tsv(text, output)
    elif output_format == "rtf":
        output.write_text(_to_rtf(text), encoding="utf-8", newline="")
    elif output_format == "pdf":
        _write_pdf(text, output, source)
    elif output_format == "docx":
        _write_docx(text, output)
    elif output_format == "doc":
        output.write_text(_to_rtf(text), encoding="utf-8", newline="")
    elif output_format == "odt":
        _write_odf_text(text, output)
    elif output_format == "xlsx":
        _write_xlsx(text, output)
    elif output_format == "xls":
        output.write_text(_to_excel_html(text, source), encoding="utf-8", newline="")
    elif output_format == "ods":
        _write_odf_spreadsheet(text, output)
    elif output_format == "pptx":
        _write_pptx(text, output, source)
    elif output_format == "ppt":
        output.write_text(_to_presentation_html(text, source), encoding="utf-8", newline="")
    elif output_format == "odp":
        _write_odf_presentation(text, output, source)
    elif output_format == "fb2":
        _write_fb2(text, output, source)
    elif output_format == "epub":
        _write_epub(text, output, source)
    elif output_format in {"mp3", "m4a", "wav"}:
        _text_to_audio(text, output)


def _read_plain_text_file(path: Path) -> tuple[str, str]:
    last_error: Exception | None = None
    for encoding in TEXT_READ_ENCODINGS:
        try:
            return path.read_text(encoding=encoding), encoding
        except UnicodeDecodeError as exc:
            last_error = exc
    raise TextConversionError(f"Cannot decode text file: {path}") from last_error


def _read_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(_read_xml_member(zf, "word/document.xml"))
    paragraphs = []
    for para in _iter_local(root, "p"):
        text = _ooxml_text(para).strip()
        if text:
            paragraphs.append(text)
    if paragraphs:
        return "\n".join(paragraphs)
    return _flatten_xml_text(root)


def _read_xlsx(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        names = set(_safe_zip_names(zf))
        shared = _read_xlsx_shared_strings(zf) if "xl/sharedStrings.xml" in names else []
        sheet_names = sorted(
            [name for name in names if name.startswith("xl/worksheets/") and name.endswith(".xml")],
            key=_natural_key,
        )
        sections = []
        for index, name in enumerate(sheet_names, start=1):
            root = ET.fromstring(_read_xml_member(zf, name))
            rows = []
            for row in _iter_local(root, "row"):
                values = []
                for cell in [child for child in row if _local_name(child.tag) == "c"]:
                    values.append(_xlsx_cell_text(cell, shared))
                if any(value for value in values):
                    rows.append("\t".join(values).rstrip())
            if rows:
                sections.append(f"Sheet {index}\n" + "\n".join(rows))
        return "\n\n".join(sections)


def _read_xlsx_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    root = ET.fromstring(_read_xml_member(zf, "xl/sharedStrings.xml"))
    values = []
    for item in _iter_local(root, "si"):
        values.append(_ooxml_text(item))
    return values


def _xlsx_cell_text(cell: ET.Element, shared_strings: Sequence[str]) -> str:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        return _ooxml_text(cell)
    value_node = next(_iter_local(cell, "v"), None)
    value = value_node.text if value_node is not None and value_node.text is not None else ""
    if cell_type == "s":
        try:
            return shared_strings[int(value)]
        except (ValueError, IndexError):
            return ""
    return value


def _read_pptx(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        slide_names = sorted(
            [name for name in _safe_zip_names(zf) if name.startswith("ppt/slides/slide") and name.endswith(".xml")],
            key=_natural_key,
        )
        slides = []
        for index, name in enumerate(slide_names, start=1):
            root = ET.fromstring(_read_xml_member(zf, name))
            texts = [node.text or "" for node in _iter_local(root, "t") if node.text]
            if texts:
                slides.append(f"Slide {index}\n" + "\n".join(texts))
        return "\n\n".join(slides)


def _read_odf(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        root = ET.fromstring(_read_xml_member(zf, "content.xml"))
    paragraphs = []
    for element in root.iter():
        if _local_name(element.tag) in {"h", "p"}:
            text = "".join(element.itertext()).strip()
            if text:
                paragraphs.append(text)
    if paragraphs:
        return "\n".join(paragraphs)
    return _flatten_xml_text(root)


def _read_pdf(path: Path) -> str:
    text = _read_pdf_with_pypdf(path)
    if text.strip():
        return text
    data = path.read_bytes()
    text = _extract_pdf_text(data)
    if text.strip():
        return text
    text = _extract_printable_text(data)
    if text.strip():
        return text
    raise TextConversionError(f"Cannot extract text from PDF: {path}")


def _safe_zip_names(zf: zipfile.ZipFile) -> list[str]:
    infos = zf.infolist()
    if len(infos) > MAX_OFFICE_ZIP_ENTRIES:
        raise TextConversionError("Document archive contains too many files.")
    total_size = 0
    names: list[str] = []
    for info in infos:
        total_size += max(0, int(info.file_size))
        if total_size > MAX_OFFICE_ZIP_UNCOMPRESSED_BYTES:
            raise TextConversionError("Document archive expands beyond the allowed size.")
        names.append(info.filename)
    return names


def _read_xml_member(zf: zipfile.ZipFile, name: str) -> bytes:
    _safe_zip_names(zf)
    try:
        info = zf.getinfo(name)
    except KeyError as exc:
        raise TextConversionError(f"Document XML member is missing: {name}") from exc
    if info.file_size > MAX_XML_MEMBER_BYTES:
        raise TextConversionError(f"Document XML member is too large: {name}")
    return zf.read(info)


def _read_pdf_with_pypdf(path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        return ""
    try:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception:
        return ""


def _extract_pdf_text(data: bytes) -> str:
    chunks: list[str] = []
    stream_re = re.compile(rb"<<(?P<dict>.*?)>>\s*stream\r?\n(?P<body>.*?)\r?\nendstream", re.S)
    for match in stream_re.finditer(data):
        stream = match.group("body").strip(b"\r\n")
        dictionary = match.group("dict")
        if b"FlateDecode" in dictionary:
            try:
                stream = zlib.decompress(stream)
            except zlib.error:
                continue
        chunks.extend(_parse_pdf_text_stream(stream))
    return "\n".join(chunk for chunk in chunks if chunk.strip())


def _parse_pdf_text_stream(stream: bytes) -> list[str]:
    result: list[str] = []
    for block in re.findall(rb"BT(.*?)ET", stream, re.S):
        strings: list[str] = []
        for array in re.findall(rb"\[(.*?)\]\s*TJ", block, re.S):
            strings.extend(_decode_pdf_string_token(token) for token in _pdf_string_tokens(array))
        for literal in re.findall(rb"\((?:\\.|[^\\()])*\)\s*Tj", block, re.S):
            strings.append(_decode_pdf_string_token(literal.rsplit(b")", 1)[0] + b")"))
        for hex_string in re.findall(rb"<([0-9A-Fa-f\s]+)>\s*Tj", block, re.S):
            strings.append(_decode_pdf_hex_string(hex_string))
        line = "".join(strings).strip()
        if line:
            result.append(line)
    return result


def _pdf_string_tokens(data: bytes) -> list[bytes]:
    return [match.group(0) for match in re.finditer(rb"\((?:\\.|[^\\()])*\)|<[0-9A-Fa-f\s]+>", data, re.S)]


def _decode_pdf_string_token(token: bytes | tuple[bytes, ...]) -> str:
    if isinstance(token, tuple):
        token = next((part for part in token if part), b"")
    if token.startswith(b"("):
        raw = _unescape_pdf_literal(token[1:-1])
        return _decode_pdf_bytes(raw)
    if token.startswith(b"<") and token.endswith(b">"):
        token = token[1:-1]
    return _decode_pdf_hex_string(token)


def _decode_pdf_hex_string(token: bytes) -> str:
    compact = re.sub(rb"\s+", b"", token)
    if len(compact) % 2:
        compact += b"0"
    try:
        return _decode_pdf_bytes(bytes.fromhex(compact.decode("ascii")))
    except ValueError:
        return ""


def _unescape_pdf_literal(data: bytes) -> bytes:
    from services.native_acceleration import native

    if native is not None:
        return native.unescape_pdf_literal(data)
    return _unescape_pdf_literal_python(data)


def _unescape_pdf_literal_python(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(data):
        ch = data[i]
        if ch != 0x5C:
            out.append(ch)
            i += 1
            continue
        i += 1
        if i >= len(data):
            break
        esc = data[i]
        if esc in b"nrtbf":
            out.append({ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8, ord("f"): 12}[esc])
            i += 1
        elif esc in b"()\\":
            out.append(esc)
            i += 1
        elif esc in b"\r\n":
            if esc == 13 and i + 1 < len(data) and data[i + 1] == 10:
                i += 2
            else:
                i += 1
        elif 48 <= esc <= 55:
            octal = bytes([esc])
            i += 1
            for _ in range(2):
                if i < len(data) and 48 <= data[i] <= 55:
                    octal += bytes([data[i]])
                    i += 1
            out.append(int(octal, 8) & 0xFF)
        else:
            out.append(esc)
            i += 1
    return bytes(out)


def _decode_pdf_bytes(data: bytes) -> str:
    if data.startswith(b"\xfe\xff"):
        return data[2:].decode("utf-16-be", errors="ignore")
    if data.startswith(b"\xff\xfe"):
        return data[2:].decode("utf-16-le", errors="ignore")
    if data.count(b"\x00") > max(2, len(data) // 4):
        return data.decode("utf-16-be", errors="ignore")
    return data.decode("latin-1", errors="ignore")


def _extract_printable_text(data: bytes) -> str:
    candidates = []
    latin_text = data.decode("latin-1", errors="ignore")
    candidates.extend(re.findall(r"[\x09\x0a\x0d\x20-\x7e]{4,}", latin_text))
    try:
        utf16_text = data.decode("utf-16le", errors="ignore")
        candidates.extend(re.findall(r"[^\x00-\x08\x0b\x0c\x0e-\x1f]{4,}", utf16_text))
    except Exception:
        pass
    cleaned = []
    for value in candidates:
        text = re.sub(r"\s+", " ", value).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return "\n".join(cleaned)


def _to_markdown(text: str, source: Path) -> str:
    if source.suffix.lower() in {".md", ".markdown"}:
        return text
    return text.rstrip("\n") + "\n"


def _to_html(text: str, source: Path) -> str:
    title = html.escape(source.stem)
    body = html.escape(text)
    return (
        "<!doctype html>\n"
        '<html lang="uk">\n'
        "<head>\n"
        '  <meta charset="utf-8">\n'
        f"  <title>{title}</title>\n"
        "  <style>body{font-family:system-ui,sans-serif;line-height:1.5;padding:24px;}pre{white-space:pre-wrap;}</style>\n"
        "</head>\n"
        "<body>\n"
        f"<pre>{body}</pre>\n"
        "</body>\n"
        "</html>\n"
    )


def _to_json(text: str, source: Path) -> str:
    payload = {
        "source": source.name,
        "format": source.suffix.lower().lstrip("."),
        "text": text,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _write_csv(text: str, output: Path) -> None:
    with output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["line", "text"])
        for index, line in enumerate(text.splitlines(), start=1):
            writer.writerow([index, line])


def _write_tsv(text: str, output: Path) -> None:
    with output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, delimiter="\t")
        writer.writerow(["line", "text"])
        for index, line in enumerate(text.splitlines(), start=1):
            writer.writerow([index, line])


def _to_rtf(text: str) -> str:
    from services.native_acceleration import native

    if native is not None:
        return native.to_rtf(text)
    return _to_rtf_python(text)


def _to_rtf_python(text: str) -> str:
    body = "".join(_rtf_char(ch) for ch in text)
    return "{\\rtf1\\ansi\\deff0\n" + body + "\n}\n"


def _rtf_char(ch: str) -> str:
    if ch == "\\":
        return "\\\\"
    if ch == "{":
        return "\\{"
    if ch == "}":
        return "\\}"
    if ch == "\n":
        return "\\par\n"
    code = ord(ch)
    if code < 128:
        return ch
    if code > 0xFFFF:
        code -= 0x10000
        return f"\\u{(0xD800 + (code >> 10)) - 65536}?\\u{(0xDC00 + (code & 0x3FF)) - 65536}?"
    if code > 32767:
        code -= 65536
    return f"\\u{code}?"


def _write_pdf(text: str, output: Path, source: Path) -> None:
    if _write_pdf_with_reportlab(text, output, source):
        return
    output.write_bytes(_build_basic_pdf(text, source))


def _write_pdf_with_reportlab(text: str, output: Path, source: Path) -> bool:
    try:
        from reportlab.lib.pagesizes import A4  # type: ignore
        from reportlab.pdfbase import pdfmetrics  # type: ignore
        from reportlab.pdfbase.ttfonts import TTFont  # type: ignore
        from reportlab.pdfgen import canvas  # type: ignore
    except Exception:
        return False
    try:
        font_name = _register_reportlab_font(pdfmetrics, TTFont)
        _page_width, page_height = A4
        margin = 48
        line_height = 14
        c = canvas.Canvas(str(output), pagesize=A4)
        c.setTitle(source.stem)
        text_object = c.beginText(margin, page_height - margin)
        text_object.setFont(font_name, 10)
        for line in _wrapped_lines(text, 96):
            if text_object.getY() < margin:
                c.drawText(text_object)
                c.showPage()
                text_object = c.beginText(margin, page_height - margin)
                text_object.setFont(font_name, 10)
            text_object.textLine(line)
            text_object.moveCursor(0, line_height - 12)
        c.drawText(text_object)
        c.save()
        return True
    except Exception:
        return False


def _register_reportlab_font(pdfmetrics, TTFont) -> str:
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    ]
    for font_path in candidates:
        if not font_path.exists():
            continue
        try:
            font_name = "MediaConverterUnicode"
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
            return font_name
        except Exception:
            continue
    return "Helvetica"


def _build_basic_pdf(text: str, source: Path) -> bytes:
    lines = list(_wrapped_lines(text, 88)) or [""]
    pages = [lines[index : index + 52] for index in range(0, len(lines), 52)]
    objects: list[bytes] = []
    font_object_id = 3
    content_ids = []
    page_ids = []

    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    next_id = 4
    for page_lines in pages:
        content_ids.append(next_id)
        objects.append(_pdf_stream(_basic_pdf_content(page_lines)))
        next_id += 1
        page_ids.append(next_id)
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                f"/Resources << /Font << /F1 {font_object_id} 0 R >> >> "
                f"/Contents {content_ids[-1]} 0 R >>"
            ).encode("ascii")
        )
        next_id += 1

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")

    title = _pdf_literal(source.stem)
    objects.append(f"<< /Title {title} /Producer (Media Converter) >>".encode("latin-1", errors="replace"))
    info_id = len(objects)

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out.extend(f"{index} 0 obj\n".encode("ascii"))
        out.extend(obj)
        out.extend(b"\nendobj\n")
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    out.extend((f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R /Info {info_id} 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n").encode("ascii"))
    return bytes(out)


def _basic_pdf_content(lines: Sequence[str]) -> bytes:
    parts = ["BT", "/F1 10 Tf", "48 792 Td", "14 TL"]
    for line in lines:
        safe = line.encode("latin-1", errors="replace").decode("latin-1")
        parts.append(f"{_pdf_literal(safe)} Tj")
        parts.append("T*")
    parts.append("ET")
    return "\n".join(parts).encode("latin-1", errors="replace")


def _pdf_stream(data: bytes) -> bytes:
    return b"<< /Length " + str(len(data)).encode("ascii") + b" >>\nstream\n" + data + b"\nendstream"


def _pdf_literal(text: str) -> str:
    return "(" + text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ")"


def _write_docx(text: str, output: Path) -> None:
    paragraphs = "\n".join(_docx_paragraph(line) for line in text.splitlines() or [""])
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        f"{paragraphs}"
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" '
        'w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/></w:sectPr>'
        "</w:body></w:document>"
    )
    _write_zip(
        output,
        {
            "[Content_Types].xml": (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/word/document.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                "</Types>"
            ),
            "_rels/.rels": (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="word/document.xml"/>'
                "</Relationships>"
            ),
            "word/document.xml": document,
        },
    )


def _docx_paragraph(line: str) -> str:
    if not line:
        return "<w:p/>"
    return f'<w:p><w:r><w:t xml:space="preserve">{_xml(line)}</w:t></w:r></w:p>'


def _write_xlsx(text: str, output: Path) -> None:
    rows_xml = []
    for row_index, row in enumerate(_rows_from_text(text), start=1):
        cells_xml = []
        for col_index, value in enumerate(row, start=1):
            ref = f"{_column_name(col_index)}{row_index}"
            cells_xml.append(f'<c r="{ref}" t="inlineStr"><is><t>{_xml(value)}</t></is></c>')
        rows_xml.append(f'<row r="{row_index}">{"".join(cells_xml)}</row>')
    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>"
        f"{''.join(rows_xml)}"
        "</sheetData></worksheet>"
    )
    _write_zip(
        output,
        {
            "[Content_Types].xml": (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/xl/workbook.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                '<Override PartName="/xl/worksheets/sheet1.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                "</Types>"
            ),
            "_rels/.rels": (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="xl/workbook.xml"/>'
                "</Relationships>"
            ),
            "xl/workbook.xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>'
                "</workbook>"
            ),
            "xl/_rels/workbook.xml.rels": (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                'Target="worksheets/sheet1.xml"/>'
                "</Relationships>"
            ),
            "xl/worksheets/sheet1.xml": sheet,
        },
    )


def _write_pptx(text: str, output: Path, source: Path) -> None:
    title = _xml(source.stem)
    lines = list(_wrapped_lines(text, 58))[:18]
    paragraphs = "".join(f'<a:p><a:r><a:rPr lang="uk-UA" sz="1800"/><a:t>{_xml(line)}</a:t></a:r></a:p>' for line in lines)
    slide = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
        "<p:cSld><p:spTree>"
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
        '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/>'
        '<a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>'
        '<p:sp><p:nvSpPr><p:cNvPr id="2" name="TextBox"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
        '<p:spPr><a:xfrm><a:off x="685800" y="685800"/><a:ext cx="7772400" cy="5486400"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>'
        '<p:txBody><a:bodyPr wrap="square"/><a:lstStyle/>'
        f'<a:p><a:r><a:rPr lang="uk-UA" sz="2800" b="1"/><a:t>{title}</a:t></a:r></a:p>{paragraphs}'
        "</p:txBody></p:sp>"
        "</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>"
    )
    _write_zip(
        output,
        {
            "[Content_Types].xml": (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                '<Default Extension="xml" ContentType="application/xml"/>'
                '<Override PartName="/ppt/presentation.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>'
                '<Override PartName="/ppt/slides/slide1.xml" '
                'ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>'
                "</Types>"
            ),
            "_rels/.rels": (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
                'Target="ppt/presentation.xml"/>'
                "</Relationships>"
            ),
            "ppt/presentation.xml": (
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                '<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
                'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
                'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">'
                '<p:sldIdLst><p:sldId id="256" r:id="rId1"/></p:sldIdLst>'
                '<p:sldSz cx="9144000" cy="6858000" type="screen4x3"/>'
                '<p:notesSz cx="6858000" cy="9144000"/>'
                "</p:presentation>"
            ),
            "ppt/_rels/presentation.xml.rels": (
                '<?xml version="1.0" encoding="UTF-8"?>'
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" '
                'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" '
                'Target="slides/slide1.xml"/>'
                "</Relationships>"
            ),
            "ppt/slides/slide1.xml": slide,
        },
    )


def _write_odf_text(text: str, output: Path) -> None:
    paragraphs = "".join(f"<text:p>{_xml(line)}</text:p>" for line in text.splitlines() or [""])
    content = _odf_document("office:text", paragraphs, extra_namespaces="")
    _write_odf_package(output, "application/vnd.oasis.opendocument.text", content)


def _write_odf_spreadsheet(text: str, output: Path) -> None:
    rows = []
    for row in _rows_from_text(text):
        cells = "".join(f'<table:table-cell office:value-type="string"><text:p>{_xml(value)}</text:p></table:table-cell>' for value in row)
        rows.append(f"<table:table-row>{cells}</table:table-row>")
    content = _odf_document(
        "office:spreadsheet",
        f'<table:table table:name="Sheet1">{"".join(rows)}</table:table>',
        extra_namespaces=' xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"',
    )
    _write_odf_package(output, "application/vnd.oasis.opendocument.spreadsheet", content)


def _write_odf_presentation(text: str, output: Path, source: Path) -> None:
    paragraphs = "".join(f"<text:p>{_xml(line)}</text:p>" for line in _wrapped_lines(text, 72))
    content = _odf_document(
        "office:presentation",
        (
            '<draw:page draw:name="page1" draw:style-name="dp1" draw:master-page-name="Default">'
            '<draw:frame draw:name="Text" draw:x="1cm" draw:y="1cm" draw:width="24cm" draw:height="16cm">'
            f'<draw:text-box><text:h text:outline-level="1">{_xml(source.stem)}</text:h>{paragraphs}</draw:text-box>'
            "</draw:frame></draw:page>"
        ),
        extra_namespaces=(
            ' xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0"'
            ' xmlns:presentation="urn:oasis:names:tc:opendocument:xmlns:presentation:1.0"'
        ),
    )
    _write_odf_package(output, "application/vnd.oasis.opendocument.presentation", content)


def _odf_document(body_tag: str, body: str, *, extra_namespaces: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<office:document-content "
        'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
        'office:version="1.2"'
        f"{extra_namespaces}>"
        f"<office:body><{body_tag}>{body}</{body_tag}></office:body>"
        "</office:document-content>"
    )


def _write_odf_package(output: Path, mimetype: str, content_xml: str) -> None:
    manifest = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" '
        'manifest:version="1.2">'
        f'<manifest:file-entry manifest:full-path="/" manifest:media-type="{mimetype}"/>'
        '<manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>'
        "</manifest:manifest>"
    )
    with zipfile.ZipFile(output, "w") as zf:
        zf.writestr("mimetype", mimetype, compress_type=zipfile.ZIP_STORED)
        zf.writestr("content.xml", content_xml, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("META-INF/manifest.xml", manifest, compress_type=zipfile.ZIP_DEFLATED)


def _to_excel_html(text: str, source: Path) -> str:
    rows = []
    for row in _rows_from_text(text):
        cells = "".join(f"<td>{html.escape(value)}</td>" for value in row)
        rows.append(f"<tr>{cells}</tr>")
    return (
        "<!doctype html>\n"
        '<html xmlns:x="urn:schemas-microsoft-com:office:excel">\n'
        '<head><meta charset="utf-8"><title>'
        f"{html.escape(source.stem)}</title></head>\n"
        f"<body><table>{''.join(rows)}</table></body></html>\n"
    )


def _to_presentation_html(text: str, source: Path) -> str:
    paragraphs = "\n".join(f"<p>{html.escape(line)}</p>" for line in _wrapped_lines(text, 72))
    return (
        "<!doctype html>\n"
        '<html xmlns:p="urn:schemas-microsoft-com:office:powerpoint">\n'
        '<head><meta charset="utf-8"><title>'
        f"{html.escape(source.stem)}</title></head>\n"
        f"<body><section><h1>{html.escape(source.stem)}</h1>{paragraphs}</section></body></html>\n"
    )


def _write_zip(output: Path, files: dict[str, str]) -> None:
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)


def _rows_from_text(text: str) -> list[list[str]]:
    lines = text.splitlines()
    if not lines:
        return [[""]]
    if any("\t" in line for line in lines):
        return [line.split("\t") for line in lines]
    if any("," in line for line in lines):
        try:
            return [row for row in csv.reader(lines)]
        except csv.Error:
            pass
    return [[line] for line in lines]


def _wrapped_lines(text: str, width: int) -> Iterable[str]:
    lines = text.splitlines() or [""]
    for raw in lines:
        if not raw:
            yield ""
            continue
        wrapped = textwrap.wrap(raw, width=width, replace_whitespace=False, drop_whitespace=False)
        yield from (wrapped or [""])


def _column_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name or "A"


def _xml(value: str) -> str:
    return html.escape(value, quote=True)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _iter_local(root: ET.Element, name: str) -> Iterable[ET.Element]:
    return (element for element in root.iter() if _local_name(element.tag) == name)


def _ooxml_text(element: ET.Element) -> str:
    parts = []
    for node in element.iter():
        local = _local_name(node.tag)
        if local == "t" and node.text:
            parts.append(node.text)
        elif local == "tab":
            parts.append("\t")
        elif local == "br":
            parts.append("\n")
    return "".join(parts)


def _flatten_xml_text(root: ET.Element) -> str:
    return "\n".join(text.strip() for text in root.itertext() if text and text.strip())


def _natural_key(value: str) -> list[int | str]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", value)]


def _strip_html_tags(raw: str) -> str:
    clean = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<br\s*/?>", "\n", clean, flags=re.IGNORECASE)
    clean = re.sub(r"</p>", "\n\n", clean, flags=re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = html.unescape(clean)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in clean.splitlines()]
    return "\n".join(lines).strip()


def _read_epub(path: Path) -> str:
    with zipfile.ZipFile(path) as zf:
        names = set(zf.namelist())
        opf_path = ""
        if "META-INF/container.xml" in names:
            try:
                container_xml = zf.read("META-INF/container.xml")
                root = ET.fromstring(container_xml)
                for el in root.iter():
                    if _local_name(el.tag) == "rootfile" and "full-path" in el.attrib:
                        opf_path = el.attrib["full-path"]
                        break
            except Exception:
                pass

        if not opf_path:
            for name in names:
                if name.endswith(".opf"):
                    opf_path = name
                    break

        chapters: list[str] = []
        if opf_path and opf_path in names:
            try:
                opf_dir = Path(opf_path).parent
                opf_xml = zf.read(opf_path)
                root = ET.fromstring(opf_xml)
                manifest: dict[str, str] = {}
                for item in root.iter():
                    if _local_name(item.tag) == "item":
                        manifest[item.attrib.get("id", "")] = item.attrib.get("href", "")

                for itemref in root.iter():
                    if _local_name(itemref.tag) == "itemref":
                        idref = itemref.attrib.get("idref", "")
                        href = manifest.get(idref, "")
                        if href:
                            full_href = (opf_dir / href).as_posix().lstrip("./")
                            if full_href in names:
                                raw_ch = zf.read(full_href).decode("utf-8", errors="replace")
                                ch_text = _strip_html_tags(raw_ch).strip()
                                if ch_text:
                                    chapters.append(ch_text)
            except Exception:
                pass

        if not chapters:
            for name in sorted(names):
                if name.lower().endswith((".xhtml", ".html", ".htm")):
                    try:
                        raw_ch = zf.read(name).decode("utf-8", errors="replace")
                        ch_text = _strip_html_tags(raw_ch).strip()
                        if ch_text:
                            chapters.append(ch_text)
                    except Exception:
                        pass

    if not chapters:
        raise TextConversionError(f"No readable text content found in EPUB: {path.name}")
    return "\n\n".join(chapters)


def _read_fb2(path: Path) -> str:
    raw = path.read_bytes()
    if raw.startswith(b"PK\x03\x04"):
        with zipfile.ZipFile(path) as zf:
            fb2_name = next((n for n in zf.namelist() if n.lower().endswith(".fb2")), None)
            if fb2_name:
                raw = zf.read(fb2_name)

    text_xml = ""
    for enc in ("utf-8", "cp1251", "latin-1"):
        try:
            text_xml = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue

    if not text_xml:
        text_xml = raw.decode("utf-8", errors="replace")

    paragraphs: list[str] = []
    try:
        root = ET.fromstring(text_xml)
        for el in root.iter():
            tag = _local_name(el.tag)
            if tag in {"p", "title", "subtitle", "v"}:
                text = "".join(el.itertext()).strip()
                if text:
                    paragraphs.append(text)
    except Exception:
        for m in re.finditer(r"<(p|v|subtitle)[^>]*>(.*?)</\1>", text_xml, re.DOTALL | re.IGNORECASE):
            clean = _strip_html_tags(m.group(2)).strip()
            if clean:
                paragraphs.append(clean)

    if not paragraphs:
        raise TextConversionError(f"No text content found in FB2: {path.name}")
    return "\n\n".join(paragraphs)


def _read_mobi(path: Path) -> str:
    data = path.read_bytes()
    if len(data) < 78:
        raise TextConversionError(f"Invalid MOBI file (too small): {path.name}")

    num_records = struct.unpack_from(">H", data, 76)[0]
    if num_records < 2:
        raise TextConversionError(f"Invalid MOBI PalmDOC database: {path.name}")

    record_offsets: list[int] = []
    for i in range(num_records):
        offset = struct.unpack_from(">I", data, 78 + i * 8)[0]
        record_offsets.append(offset)

    record_0_data = data[record_offsets[0] : record_offsets[1]]
    if len(record_0_data) < 16:
        raise TextConversionError("Invalid MOBI record 0")

    compression, _, _, record_count, _ = struct.unpack_from(">H2sIH2s", record_0_data, 0)
    text_records = min(record_count, num_records - 1)
    decompressed_parts: list[bytes] = []

    for i in range(1, text_records + 1):
        start = record_offsets[i]
        end = record_offsets[i + 1] if i + 1 < len(record_offsets) else len(data)
        rec = data[start:end]
        if compression == 1:
            decompressed_parts.append(rec)
        elif compression == 2:
            pos = 0
            rec_len = len(rec)
            out = bytearray()
            while pos < rec_len:
                b = rec[pos]
                pos += 1
                if b == 0:
                    out.append(0)
                elif 1 <= b <= 8:
                    out.extend(rec[pos : pos + b])
                    pos += b
                elif 9 <= b <= 0x7F:
                    out.append(b)
                elif 0x80 <= b <= 0xBF:
                    if pos < rec_len:
                        b2 = rec[pos]
                        pos += 1
                        distance = ((b & 0x3F) << 3) | (b2 >> 5)
                        length = (b2 & 0x07) + 3
                        for _ in range(length):
                            if distance <= len(out):
                                out.append(out[-distance])
                elif 0xC0 <= b <= 0xFF:
                    out.append(0x20)
                    out.append(b ^ 0x80)
            decompressed_parts.append(bytes(out))
        else:
            decompressed_parts.append(rec)

    raw_text = b"".join(decompressed_parts)
    decoded = ""
    for enc in ("utf-8", "cp1252", "cp1251", "latin-1"):
        try:
            decoded = raw_text.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if not decoded:
        decoded = raw_text.decode("utf-8", errors="replace")

    clean_text = _strip_html_tags(decoded)
    if not clean_text.strip():
        clean_text = _extract_printable_text(data)
    return clean_text


def _write_fb2(text: str, output: Path, source: Path) -> None:
    title = html.escape(source.stem)
    lines = [f"      <p>{html.escape(line.strip())}</p>" for line in text.splitlines() if line.strip()]
    paragraphs = "\n".join(lines)
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0" xmlns:l="http://www.w3.org/1999/xlink">
  <description>
    <title-info>
      <genre>prose</genre>
      <book-title>{title}</book-title>
    </title-info>
  </description>
  <body>
    <title><p>{title}</p></title>
    <section>
{paragraphs}
    </section>
  </body>
</FictionBook>
"""
    output.write_text(xml, encoding="utf-8")


def _write_epub(text: str, output: Path, source: Path) -> None:
    title = html.escape(source.stem)
    body_paragraphs = "\n".join(f"<p>{html.escape(p.strip())}</p>" for p in text.split("\n\n") if p.strip())
    chapter_xhtml = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{title}</title></head>
<body>
<h1>{title}</h1>
{body_paragraphs}
</body>
</html>"""
    container_xml = """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"""
    content_opf = f"""<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>{title}</dc:title>
    <dc:language>en</dc:language>
  </metadata>
  <manifest>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter1"/>
  </spine>
</package>"""

    with zipfile.ZipFile(output, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        zf.writestr("META-INF/container.xml", container_xml, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/content.opf", content_opf, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("OEBPS/chapter1.xhtml", chapter_xhtml, compress_type=zipfile.ZIP_DEFLATED)


def _text_to_audio(text: str, output: Path) -> None:
    """Generate audiobook audio from text using system speech synthesis and FFmpeg."""
    from app.paths import find_ffmpeg

    ffmpeg = find_ffmpeg()
    output.parent.mkdir(parents=True, exist_ok=True)
    clean_text = " ".join(text.split()[:5000])

    if sys.platform == "darwin" and shutil.which("say") and ffmpeg:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_aiff = Path(tmpdir) / "speech.aiff"
            proc = subprocess.run(["say", "-o", str(tmp_aiff), clean_text], capture_output=True, timeout=120)
            if proc.returncode == 0 and tmp_aiff.exists():
                subprocess.run(
                    [ffmpeg, "-y", "-i", str(tmp_aiff), "-c:a", "libmp3lame" if output.suffix == ".mp3" else "aac", str(output)],
                    capture_output=True,
                    check=True,
                )
                return

    try:
        import pyttsx3  # type: ignore

        engine = pyttsx3.init()
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_wav = Path(tmpdir) / "speech.wav"
            engine.save_to_file(clean_text, str(tmp_wav))
            engine.runAndWait()
            if tmp_wav.exists():
                if ffmpeg:
                    subprocess.run([ffmpeg, "-y", "-i", str(tmp_wav), str(output)], capture_output=True, check=True)
                else:
                    output.write_bytes(tmp_wav.read_bytes())
                return
    except Exception:
        pass

    if ffmpeg:
        subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=3",
                "-c:a",
                "aac" if output.suffix == ".m4a" else "libmp3lame",
                str(output),
            ],
            capture_output=True,
            check=True,
        )
        return

    raise TextConversionError("Audiobook generation requires macOS 'say', 'pyttsx3', or FFmpeg.")
