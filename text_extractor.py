"""
text_extractor.py - Text extraction utilities for uploaded files.

Supports:
    .txt  – plain text files
    .pdf  – PDF files (via PyPDF2)
"""

from pathlib import Path

from PyPDF2 import PdfReader


# ---------------------------------------------------------------------------
# Extract text from a .txt file
# ---------------------------------------------------------------------------
def extract_text_from_txt(filepath: str) -> str:
    """
    Read and return the full contents of a plain text file.

    Args:
        filepath: Path to the .txt file.

    Returns:
        The file contents as a string.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Extract text from a .pdf file
# ---------------------------------------------------------------------------
def extract_text_from_pdf(filepath: str) -> str:
    """
    Extract text from all pages of a PDF file using PyPDF2.

    Args:
        filepath: Path to the .pdf file.

    Returns:
        Concatenated text from every page, separated by newlines.
    """
    reader = PdfReader(filepath)
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)
    return "\n".join(pages_text)


# ---------------------------------------------------------------------------
# Auto-detect file type and extract text
# ---------------------------------------------------------------------------
def extract_text(filepath: str) -> str:
    """
    Detect the file extension and call the appropriate extraction function.

    Args:
        filepath: Path to the uploaded file.

    Returns:
        Extracted text as a string.

    Raises:
        ValueError: If the file extension is not supported.
    """
    extension = Path(filepath).suffix.lower()

    if extension == ".txt":
        return extract_text_from_txt(filepath)
    elif extension == ".pdf":
        return extract_text_from_pdf(filepath)
    else:
        raise ValueError(f"Unsupported file type: '{extension}'. Only .txt and .pdf are supported.")
