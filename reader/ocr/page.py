import io
from typing import List, Optional

import fitz as pymupdf
import ocrmypdf
from spellchecker import SpellChecker

from reader.ocr.utils import detect_bad_ocr
from reader.schema import Block
from reader.settings import settings

ocrmypdf.configure_logging(verbosity=ocrmypdf.Verbosity.quiet)


def ocr_entire_page(
    page: pymupdf.Page, lang: str, spellchecker: Optional[SpellChecker] = None
) -> List[Block]:
    if settings.OCR_ENGINE == "tesseract":
        return ocr_entire_page_tess(page, lang, spellchecker)
    elif settings.OCR_ENGINE == "ocrmypdf":
        return ocr_entire_page_ocrmp(page, lang, spellchecker)
    else:
        raise ValueError(f"Unknown OCR engine {settings.OCR_ENGINE}")


def ocr_entire_page_tess(
    page: pymupdf.Page, lang: str, spellchecker: Optional[SpellChecker] = None
) -> List[Block]:
    try:
        full_tp = page.get_textpage_ocr(
            flags=settings.TEXT_FLAGS, dpi=settings.OCR_DPI, full=True, language=lang
        )
        blocks = page.get_text(
            "dict", sort=True, flags=settings.TEXT_FLAGS, textpage=full_tp
        )["blocks"]
        full_text = page.get_text(
            "text", sort=True, flags=settings.TEXT_FLAGS, textpage=full_tp
        )

        if len(full_text) == 0:
            return []

        # Check if OCR worked. If it didn't, return empty list
        # OCR can fail if there is a scanned blank page with some faint text impressions, for example
        if detect_bad_ocr(full_text, spellchecker):
            return []
    except RuntimeError as e:
        print(e)
        return []
    return blocks


def ocr_entire_page_ocrmp(
    page: pymupdf.Page, lang: str, spellchecker: Optional[SpellChecker] = None
) -> List[Block]:
    # Use ocrmypdf to get OCR text for the whole page
    one_page_doc = pymupdf.open()  # make temporary 1-pager
    one_page_doc.insert_pdf(
        page.parent,
        from_page=page.number,
        to_page=page.number,
        annots=False,
        links=False,
    )
    inbytes = io.BytesIO(one_page_doc.tobytes())  # transform to BytesIO object
    outbytes = io.BytesIO()  # let ocrmypdf store its result pdf here
    ocrmypdf.ocr(
        inbytes,
        outbytes,
        language=lang,
        output_type="pdf",
        redo_ocr=True,
        progress_bar=False,
        optimize=False,
        fast_web_view=1e6,
        skip_big=15,  # skip images larger than 15 megapixels
        tesseract_timeout=settings.TESSERACT_TIMEOUT,
        tesseract_non_ocr_timeout=settings.TESSERACT_TIMEOUT,
    )
    ocr_pdf = pymupdf.open("pdf", outbytes.getvalue())  # read output as fitz PDF
    blocks = ocr_pdf[0].get_text("dict", sort=True, flags=settings.TEXT_FLAGS)["blocks"]
    full_text = ocr_pdf[0].get_text("text", sort=True, flags=settings.TEXT_FLAGS)

    # Make sure the original pdf/epub/mobi bbox and the ocr pdf bbox are the same
    assert page.bound() == ocr_pdf[0].bound()

    if len(full_text) == 0:
        return []

    if detect_bad_ocr(full_text, spellchecker):
        return []

    return blocks
