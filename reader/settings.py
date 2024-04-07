from dotenv import find_dotenv
from pydantic_settings import BaseSettings
import fitz as pymupdf


class Settings(BaseSettings):
    # Debug
    DEBUG: bool = False

    # Core Settings
    WORKER_NUM: int = 1
    OCR_ALL_PAGES: bool = True
    OCR_PARALLEL_WORKERS: int = 10
    TESSDATA_PREFIX: str = ""

    # PDF Image
    PDF_IMAGE_DPI: int = 96

    # Language
    LANGUAGE: str = "Chinese"
    TESSERACT_LANGUAGES: dict = {
        "English": "eng",
        "Spanish": "spa",
        "Portuguese": "por",
        "French": "fra",
        "German": "deu",
        "Russian": "rus",
        "Chinese": "chi_sim",
    }
    SPELLCHECK_LANGUAGES: dict = {
        "English": "en",
        "Spanish": "es",
        "Portuguese": "pt",
        "French": "fr",
        "German": "de",
        "Russian": "ru",
        "Chinese": None,
    }

    # Filetypes
    SUPPORTED_FILETYPES: dict = {
        "application/pdf": "pdf",
        "application/epub+zip": "epub",
        "application/x-mobipocket-ebook": "mobi",
        "application/vnd.ms-xpsdocument": "xps",
        "application/x-fictionbook+xml": "fb2",
    }

    # PyMuPDF
    TEXT_FLAGS: int = (
        pymupdf.TEXTFLAGS_DICT
        & ~pymupdf.TEXT_PRESERVE_LIGATURES
        & ~pymupdf.TEXT_PRESERVE_IMAGES
    )

    # OCR
    INVALID_CHARS: list[str] = [chr(0xFFFD), "�"]
    OCR_DPI: int = 400
    TESSERACT_TIMEOUT: int = 20
    OCR_ENGINE: str = "ocrmypdf"  # "tesseract" or "ocrmypdf"

    class Config:
        env_file = find_dotenv("local.env")
        extra = "ignore"


settings = Settings()
