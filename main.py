# import sys
# sys.path.append("/home/yejibing/code/doc-parser/pyfunvice")
# from pyfunvice import faas, start_faas

from reader.settings import settings
from reader.extract_text import get_pages
from reader.structure.schema import DocInfo, Page, PageWrapper
from pyfunvice import app_service, start_app

import base64
import os
import uuid
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

    for page in pages:
        page.doc_info = DocInfo(filetype=filetype, page_num=len(pages))

    return pages


def encode_pdf_to_base64(pdf_path, output_base64_path):
    with open(pdf_path, "rb") as pdf_file:
        pdf_bytes = pdf_file.read()
        encoded_string = base64.b64encode(pdf_bytes).decode("utf-8")
    with open(output_base64_path, "w") as output_file:
        output_file.write(encoded_string)
    return encoded_string


def decode_base64_to_pdf(encoded_string, output_path):
    decoded_bytes = base64.b64decode(encoded_string.encode("utf-8"))
    with open(output_path, "wb") as output_file:
        output_file.write(decoded_bytes)


@app_service(path="/api/v1/parser/ppl/reader/file", body_type="form-data")
async def parser_file(file_name: str):
    pages: list[PageWrapper] = []
    pages = read_pdf(file_name)
    return pages


@app_service(path="/api/v1/parser/ppl/reader")
async def parser_file_base64(data: dict):
    pages: list[Page] = []
    pdf_local_path = f"./{str(uuid.uuid4())}-decode.pdf"
    decode_base64_to_pdf(data["file"], pdf_local_path)
    pages = read_pdf(pdf_local_path)
    os.remove(pdf_local_path)

    return pages


if __name__ == "__main__":
    start_app(workers=settings.WORKER_NUM)


def generate_encode_file():
    input_pdf_path = "./vllm.pdf"
    encode_file_path = "./vllm-encode.txt"
    encoded_string = encode_pdf_to_base64(input_pdf_path, encode_file_path)
    output_pdf_path = "./vllm-decode.pdf"
    decode_base64_to_pdf(encoded_string, output_pdf_path)
    print("Decoded PDF saved to:", output_pdf_path)
