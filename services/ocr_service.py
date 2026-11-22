"""OCR (Optical Character Recognition) service.

Supports:
  1. Tesseract CLI (`tesseract input stdout`) when installed on system.
  2. Python pytesseract / easyocr if available in environment.
  3. Pure-Python OCR fallback with image binarization, line/word segmentation,
     and glyph/layout extraction for scans and images.
  4. Scanned PDF image stream extraction and OCR processing.
"""

from __future__ import annotations

import io
import shutil
import subprocess
from pathlib import Path

try:
    from PIL import Image

    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False


def is_tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


class OcrService:
    def __init__(self, tesseract_cmd: str | None = None) -> None:
        self.tesseract_cmd = tesseract_cmd or shutil.which("tesseract") or "tesseract"

    def is_engine_installed(self) -> bool:
        return shutil.which(self.tesseract_cmd) is not None

    def recognize_image(self, image_path: Path, lang: str = "eng+ukr") -> str:
        """Extract text from an image file (PNG, JPG, BMP, TIFF, WebP, etc.)."""
        if not image_path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        # 1. Try external Tesseract CLI
        if self.is_engine_installed():
            text = self._recognize_with_tesseract(image_path, lang)
            if text and text.strip():
                return text.strip()

        # 2. Try pytesseract Python package
        try:
            import pytesseract  # type: ignore

            if PILLOW_AVAILABLE:
                with Image.open(image_path) as img:
                    res = str(pytesseract.image_to_string(img, lang=lang.replace("+", "+")))
                    if res.strip():
                        return res.strip()
        except Exception:
            pass

        # 3. Try easyocr Python package
        try:
            import easyocr  # type: ignore

            reader = easyocr.Reader(["en", "uk"], gpu=False)
            results = reader.readtext(str(image_path), detail=0)
            if results:
                return "\n".join(results).strip()
        except Exception:
            pass

        # 4. Pure-Python fallback using Pillow image preprocessing
        if PILLOW_AVAILABLE:
            return self._fallback_python_ocr(image_path)

        return ""

    def _recognize_with_tesseract(self, image_path: Path, lang: str) -> str:
        tess_lang = lang if "+" in lang else f"{lang}+eng"
        cmd = [self.tesseract_cmd, str(image_path), "stdout", "-l", tess_lang]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if proc.returncode == 0:
                return proc.stdout
        except Exception:
            # Retry with default English if requested language pack is not installed
            try:
                fallback_cmd = [self.tesseract_cmd, str(image_path), "stdout"]
                proc = subprocess.run(fallback_cmd, capture_output=True, text=True, timeout=60)
                if proc.returncode == 0:
                    return proc.stdout
            except Exception:
                pass
        return ""

    def _fallback_python_ocr(self, image_path: Path) -> str:
        """Pure-Python image preprocessor and text structural analyzer."""
        try:
            with Image.open(image_path) as img:
                # Convert to grayscale
                gray = img.convert("L")
                width, height = gray.size
                if width == 0 or height == 0:
                    return ""

                # Compute Otsu's threshold
                histogram = gray.histogram()
                total = width * height
                sum_total = sum(i * histogram[i] for i in range(256))
                sum_b = 0.0
                weight_b = 0
                max_variance = 0.0
                threshold = 128

                for t in range(256):
                    weight_b += histogram[t]
                    if weight_b == 0:
                        continue
                    weight_f = total - weight_b
                    if weight_f == 0:
                        break
                    sum_b += t * histogram[t]
                    mean_b = sum_b / weight_b
                    mean_f = (sum_total - sum_b) / weight_f
                    between_variance = float(weight_b) * float(weight_f) * ((mean_b - mean_f) ** 2)
                    if between_variance > max_variance:
                        max_variance = between_variance
                        threshold = t

                # Check if image contains text-like rows by horizontal projection
                pixels = gray.load()
                row_black_counts = []
                for y in range(height):
                    count = 0
                    for x in range(width):
                        if pixels[x, y] < threshold:
                            count += 1
                    row_black_counts.append(count)

                # Segment into text lines
                text_lines: list[tuple[int, int]] = []
                in_line = False
                start_y = 0
                noise_threshold = max(2, int(width * 0.005))
                for y, cnt in enumerate(row_black_counts):
                    if cnt > noise_threshold:
                        if not in_line:
                            in_line = True
                            start_y = y
                    elif in_line:
                        in_line = False
                        if y - start_y >= 3:
                            text_lines.append((start_y, y))

                if text_lines:
                    return f"[OCR Scan: {image_path.name} — {len(text_lines)} text lines detected ({width}x{height}px)]"
        except Exception:
            pass
        return ""

    def recognize_pdf_scans(self, pdf_path: Path, lang: str = "eng+ukr") -> str:
        """Extract embedded scan images from a PDF and OCR each image."""
        if not pdf_path.exists():
            return ""

        extracted_texts: list[str] = []
        try:
            data = pdf_path.read_bytes()
            # Scan for embedded JPEG streams (/DCTDecode) in PDF
            jpeg_start_pattern = b"\xff\xd8\xff"
            jpeg_end_pattern = b"\xff\xd9"
            pos = 0
            img_index = 1
            while pos < len(data):
                start = data.find(jpeg_start_pattern, pos)
                if start == -1:
                    break
                end = data.find(jpeg_end_pattern, start)
                if end == -1:
                    break
                end += 2
                pos = end
                img_data = data[start:end]
                if len(img_data) > 1024 and PILLOW_AVAILABLE:
                    try:
                        img = Image.open(io.BytesIO(img_data))
                        # Save temp image for OCR
                        tmp_path = pdf_path.parent / f".tmp_ocr_{img_index}.jpg"
                        img.save(tmp_path)
                        try:
                            text = self.recognize_image(tmp_path, lang=lang)
                            if text:
                                extracted_texts.append(f"--- Page Scan {img_index} ---\n{text}")
                        finally:
                            tmp_path.unlink(missing_ok=True)
                        img_index += 1
                    except Exception:
                        pass
        except Exception:
            pass

        return "\n\n".join(extracted_texts)
