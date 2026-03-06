from pathlib import Path
from PyPDF2 import PdfReader

def extract_text_from_txt(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()

def extract_text_from_pdf(filepath: str) -> str:
    reader = PdfReader(filepath)
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)
    return "\n".join(pages_text)

def extract_text(filepath: str) -> str:
    extension = Path(filepath).suffix.lower()
    if extension == ".txt":
        return extract_text_from_txt(filepath)
    elif extension == ".pdf":
        return extract_text_from_pdf(filepath)
    else:
        raise ValueError(f"Unsupported file type: '{extension}'. Only .txt and .pdf are supported.")
