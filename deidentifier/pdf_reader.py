import io
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import fitz  # PyMuPDF
import pytesseract
from PIL import Image
from pypdf import PdfReader


@dataclass
class PDFExtractionResult:
    text: str
    method: str
    pages: int


def configure_tesseract_windows() -> None:
    """
    Tries to configure the Tesseract executable on Windows.

    If Tesseract is already in PATH, this function does nothing.
    """

    if shutil.which("tesseract"):
        return

    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]

    for path in possible_paths:
        if Path(path).exists():
            pytesseract.pytesseract.tesseract_cmd = path
            return


def has_tesseract() -> bool:
    if shutil.which("tesseract"):
        return True

    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]

    return any(Path(path).exists() for path in possible_paths)


def extract_text_with_pypdf(pdf_path: Union[str, Path]) -> PDFExtractionResult:
    """
    Extracts text from a normal PDF with selectable text.
    This is faster and more accurate than OCR when the PDF contains text.
    """

    pdf_path = Path(pdf_path)
    reader = PdfReader(str(pdf_path))

    extracted_pages = []

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        extracted_pages.append(f"\n--- Page {page_number} ---\n{page_text.strip()}")

    text = "\n".join(extracted_pages).strip()

    return PDFExtractionResult(
        text=text,
        method="pypdf",
        pages=len(reader.pages),
    )


def extract_text_with_ocr(
    pdf_path: Union[str, Path],
    language: str = "eng",
    zoom: float = 2.0,
) -> PDFExtractionResult:
    """
    Extracts text from a scanned PDF using OCR.

    PyMuPDF renders each page as an image, and pytesseract reads the text
    from that image.
    """

    configure_tesseract_windows()

    if not has_tesseract():
        raise RuntimeError(
            "Tesseract is not installed or not available in PATH. "
            "Install Tesseract to use OCR extraction."
        )

    pdf_path = Path(pdf_path)
    document = fitz.open(str(pdf_path))

    extracted_pages = []

    for page_index in range(len(document)):
        page = document.load_page(page_index)

        matrix = fitz.Matrix(zoom, zoom)
        pixmap = page.get_pixmap(matrix=matrix, alpha=False)

        image_bytes = pixmap.tobytes("png")
        image = Image.open(io.BytesIO(image_bytes))

        page_text = pytesseract.image_to_string(image, lang=language)

        extracted_pages.append(
            f"\n--- Page {page_index + 1} ---\n{page_text.strip()}"
        )

    document.close()

    text = "\n".join(extracted_pages).strip()

    return PDFExtractionResult(
        text=text,
        method="ocr",
        pages=len(extracted_pages),
    )


def extract_text_from_pdf(
    pdf_path: Union[str, Path],
    force_ocr: bool = False,
    min_text_chars: int = 80,
    language: str = "eng",
) -> PDFExtractionResult:
    """
    Main PDF text extraction function.

    Strategy:
    1. If force_ocr is False, first try normal text extraction with pypdf.
    2. If the extracted text is too short, assume the PDF may be scanned.
    3. Fall back to OCR.
    """

    if not force_ocr:
        result = extract_text_with_pypdf(pdf_path)

        if len(result.text.strip()) >= min_text_chars:
            return result

        if not has_tesseract():
            result.method = "pypdf (ocr unavailable)"
            return result

    return extract_text_with_ocr(
        pdf_path=pdf_path,
        language=language,
    )