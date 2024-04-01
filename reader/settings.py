from typing import Optional, List, Dict

from dotenv import find_dotenv
from pydantic import computed_field
from pydantic_settings import BaseSettings
import fitz as pymupdf


class Settings(BaseSettings):
    # General
    WORKER_NUM: int = 1
    TORCH_DEVICE: str = "cpu"
    INFERENCE_RAM: int = 40  # How much VRAM each GPU has (in GB).
    VRAM_PER_TASK: float = 2.5  # How much VRAM to allocate per task (in GB).  Peak marker VRAM usage is around 3GB, but avg across workers is lower.
    DEFAULT_LANG: str = "Chinese"  # Default language we assume files to be in, should be one of the keys in TESSERACT_LANGUAGES

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
    TESSERACT_LANGUAGES: Dict = {
        "English": "eng",
        "Spanish": "spa",
        "Portuguese": "por",
        "French": "fra",
        "German": "deu",
        "Russian": "rus",
        "Chinese": "chi_sim",
    }
    TESSERACT_TIMEOUT: int = 20  # When to give up on OCR
    SPELLCHECK_LANGUAGES: Dict = {
        "English": "en",
        "Spanish": "es",
        "Portuguese": "pt",
        "French": "fr",
        "German": "de",
        "Russian": "ru",
        "Chinese": None,
    }
    OCR_ALL_PAGES: bool = False  # Run OCR on every page even if text can be extracted
    OCR_PARALLEL_WORKERS: int = 2  # How many CPU workers to use for OCR
    OCR_ENGINE: str = "ocrmypdf"  # Which OCR engine to use, either "tesseract" or "ocrmypdf".  Ocrmypdf is higher quality, but slower.

    # Debug
    DEBUG: bool = False  # Enable debug logging
    DEBUG_DATA_FOLDER: Optional[str] = None

    @computed_field
    @property
    def CUDA(self) -> bool:
        return "cuda" in self.TORCH_DEVICE

    class Config:
        env_file = find_dotenv("local.env")
        extra = "ignore"


settings = Settings()
