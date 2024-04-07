# import sys
# sys.path.append("/home/yejibing/code/doc-parser/pyfunvice")
# from pyfunvice import faas, start_faas

from reader.settings import settings
from reader.extract_text import get_pages
from reader.structure.schema import Page
from pyfunvice import faas, start_faas

import fitz as pymupdf
import logging
import magic


def get_language() -> tuple[str, str, str]:
    lang = settings.LANGUAGE

    # tesseract language (default add "eng")
    tesseract_lang = settings.TESSERACT_LANGUAGES.get(lang, "eng")
    if "eng" not in tesseract_lang:
        tesseract_lang = f"eng+{tesseract_lang}"

    # spellchecker language
    spell_lang = settings.SPELLCHECK_LANGUAGES.get(lang, "en")
    return tesseract_lang, spell_lang


def get_type(
    fpath: str,
) -> tuple[bool, str]:
    type = magic.from_file(fpath).lower()
    if "pdf" in type:
        return "pdf"
    elif "epub" in type:
        return "epub"
    elif "mobi" in type:
        return "mobi"
    elif type in settings.SUPPORTED_FILETYPES:
        return settings.SUPPORTED_FILETYPES[type]
    else:
        logging.error(f"Found nonstandard filetype {type}")
        raise ValueError(f"input file type [{type}] is not supported.")


class DocInfo:
    def __init__(self, filetype, page_num, ocr_stats):
        self.filetype = filetype
        self.page_num = page_num
        self.ocr_stats = ocr_stats


def read_pdf(
    fname: str,
    max_pages=None,
    parallel_factor: int = 1,
    debug_mode: bool = False,
):
    # get target language & file type
    tesseract_lang, spell_lang = get_language()
    filetype = get_type(fname)

    # read document
    doc: pymupdf.Document = pymupdf.Document(fname, filetype=filetype)
    if filetype != "pdf":
        doc = pymupdf.open("pdf", doc.convert_to_pdf())

    # parser document
    pages, ocr_stats = get_pages(
        doc,
        tesseract_lang,
        spell_lang,
        max_pages=max_pages,
        parallel=settings.OCR_PARALLEL_WORKERS * parallel_factor,
    )

    return DocInfo(filetype, len(pages), ocr_stats), pages


@faas(path="/api/v1/parser/file", body_type="form-data")
async def parser_file(file_name: str):
    pages: list[Page] = []
    doc_info: DocInfo = None
    doc_info, pages = read_pdf(file_name)
    return {"doc_info": doc_info, "pages": pages}


if __name__ == "__main__":
    start_faas(workers=settings.WORKER_NUM)
