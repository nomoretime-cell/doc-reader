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
    return lang, tesseract_lang, spell_lang


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


class MetaInfo:
    def __init__(self, filetype, language, page_num, toc, ocr_stats):
        self.filetype = filetype
        self.language = language
        self.page_num = page_num
        self.toc = toc
        self.ocr_stats = ocr_stats


def read_pdf(
    fname: str,
    max_pages=None,
    parallel_factor: int = 1,
    debug_mode: bool = False,
):
    # get target language & file type
    lang, tesseract_lang, spell_lang = get_language()
    filetype = get_type(fname)

    # read document
    doc: pymupdf.Document = pymupdf.Document(fname, filetype=filetype)
    if filetype != "pdf":
        doc = pymupdf.open("pdf", doc.convert_to_pdf())

    # parser document
    pages, toc, ocr_stats = get_pages(
        doc,
        tesseract_lang,
        spell_lang,
        max_pages=max_pages,
        parallel=settings.OCR_PARALLEL_WORKERS * parallel_factor,
    )

    return MetaInfo(filetype, lang, len(pages), toc, ocr_stats), pages


@faas(path="/api/v1/parser/file", body_type="form-data")
async def parser_file(file_name: str):
    pages: list[Page] = []
    meta_info: MetaInfo = None
    meta_info, pages = read_pdf(file_name)
    return {"meta_info": meta_info, "pages": pages}


if __name__ == "__main__":
    start_faas(workers=1)
