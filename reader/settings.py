from typing import Optional, List, Dict

from dotenv import find_dotenv
from pydantic import computed_field
from pydantic_settings import BaseSettings
import fitz as pymupdf


class Settings(BaseSettings):
    # Debug
    DEBUG: bool = False
    DEBUG_DATA_FOLDER: Optional[str] = None

    # General
    WORKER_NUM: int = 1
    TORCH_DEVICE: str = "cpu"
    PDF_IMAGE_DPI: int = 96

    # Language
    LANGUAGE: str = "Chinese"
    TESSERACT_LANGUAGES: Dict = {
        "English": "eng",
        "Spanish": "spa",
        "Portuguese": "por",
        "French": "fra",
        "German": "deu",
        "Russian": "rus",
        "Chinese": "chi_sim",
    }
    SPELLCHECK_LANGUAGES: Dict = {
        "English": "en",
        "Spanish": "es",
        "Portuguese": "pt",
        "French": "fr",
        "German": "de",
        "Russian": "ru",
        "Chinese": None,
    }

    # Filetypes
    SUPPORTED_FILETYPES: Dict = {
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
    INVALID_CHARS: List[str] = [chr(0xFFFD), "�"]
    OCR_DPI: int = 400
    TESSDATA_PREFIX: str = ""
    TESSERACT_TIMEOUT: int = 20  # When to give up on OCR
    OCR_ALL_PAGES: bool = True  # Run OCR on every page even if text can be extracted
    OCR_PARALLEL_WORKERS: int = 10  # How many CPU workers to use for OCR
    OCR_ENGINE: str = "ocrmypdf"  # Which OCR engine to use, either "tesseract" or "ocrmypdf".  Ocrmypdf is higher quality, but slower.

    @computed_field
    @property
    def CUDA(self) -> bool:
        return "cuda" in self.TORCH_DEVICE

    class Config:
        env_file = find_dotenv("local.env")
        extra = "ignore"


settings = Settings()
