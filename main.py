# import sys
# sys.path.append("/home/yejibing/code/doc-parser/pyfunvice")
# from pyfunvice import faas, start_faas

import fitz as pymupdf
import logging
import magic
from pyfunvice import faas, start_faas
from typing import Optional

from reader.settings import settings
from reader.extract_text import get_pages


def get_filetype(
    fpath: str,
) -> tuple[bool, str]:
    mimetype = magic.from_file(fpath).lower()

    # Get extensions from mimetype
    # The mimetype is not always consistent, so use in to check the most common formats
    if "pdf" in mimetype:
        return True, "pdf"
    elif "epub" in mimetype:
        return True, "epub"
    elif "mobi" in mimetype:
        return True, "mobi"
    elif mimetype in settings.SUPPORTED_FILETYPES:
        return True, settings.SUPPORTED_FILETYPES[mimetype]
    else:
        logging.error(f"Found nonstandard filetype {mimetype}")
        return False, "other"


def get_language(metadata: Optional[dict] = None) -> tuple[str, str, str]:
    lang = settings.DEFAULT_LANG
    if metadata:
        lang = metadata.get("language", settings.DEFAULT_LANG)

    # Use tesseract language if available
    tess_lang = settings.TESSERACT_LANGUAGES.get(lang, "eng")
    spell_lang = settings.SPELLCHECK_LANGUAGES.get(lang, None)
    if "eng" not in tess_lang:
        tess_lang = f"eng+{tess_lang}"
    return lang, tess_lang, spell_lang


def read_pdf(
    fname: str,
    max_pages=None,
    metadata: Optional[dict] = None,
    parallel_factor: int = 10,
    debug_mode: bool = False,
):
    # get language setting
    lang, tess_lang, spell_lang = get_language(metadata)
    out_meta = {"language": lang}

    # get file type
    is_support, filetype = get_filetype(fname)
    if not is_support:
        return "", out_meta
    out_meta["filetype"] = filetype

    # read file
    doc: pymupdf.Document = pymupdf.Document(fname, filetype=filetype)
    # convert other file types to PDF
    # support document formats: PDF XPS EPUB MOBI FB2 CBZ SVG TXT
    if filetype != "pdf":
        doc = pymupdf.open("pdf", doc.convert_to_pdf())

    # get pages
    pages, toc, ocr_stats = get_pages(
        doc,
        tess_lang,
        spell_lang,
        max_pages=max_pages,
        parallel=settings.OCR_PARALLEL_WORKERS * parallel_factor,
    )

    out_meta["toc"] = toc
    out_meta["pages"] = len(pages)
    out_meta["ocr_stats"] = ocr_stats
    return pages, out_meta


@faas(path="/api/v1/parser/file", body_type="form-data")
async def upload_file(file_name: str):
    pages, out_meta = read_pdf(file_name)
    return {"meta_data": out_meta, "pages": pages}


if __name__ == "__main__":
    start_faas(workers=1)
