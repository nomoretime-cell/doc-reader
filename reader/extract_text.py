from reader.ocr.page import ocr_page
from reader.ocr.utils import is_string_illegal, parse_font_flags
from reader.settings import settings
from reader.structure.schema import ImageInfo, Span, Line, Block, Page
from reader.structure.bbox import correct_rotation

import base64
import fitz as pymupdf
import io
from typing import Tuple, Optional, Union
from spellchecker import SpellChecker
from PIL import Image
from math import isclose
from concurrent.futures import ThreadPoolExecutor


def get_doc_text(doc) -> str:
    full_text = ""
    for page in doc:
        full_text += page.get_text("text", sort=True, flags=settings.TEXT_FLAGS)
        full_text += "\n"
    return full_text


def sort_rotated_text(blocks, tolerance=1.25) -> list[Block]:
    vertical_groups = {}
    for block in blocks:
        group_key = round(block.bbox[1] / tolerance) * tolerance
        if group_key not in vertical_groups:
            vertical_groups[group_key] = []
        vertical_groups[group_key].append(block)

    # Sort each group horizontally and flatten the groups into a single list
    sorted_page_blocks = []
    for _, group in sorted(vertical_groups.items()):
        sorted_group = sorted(group, key=lambda x: x.bbox[0])
        sorted_page_blocks.extend(sorted_group)

    return sorted_page_blocks


def get_inbuilt_image(doc: pymupdf.Document, pnum: int):
    page: pymupdf.Page = doc.load_page(pnum)
    try:
        image_list = page.get_images()
        for image_index, img in enumerate(image_list, start=1):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]
            image_name = f"page{pnum + 1}_image{image_index}.{image_ext}"
            with open(image_name, "wb") as image_file:
                image_file.write(image_bytes)
    except Exception as e:
        print(e)


def get_blocks(
    doc: pymupdf.Document,
    pnum: int,
    tess_lang: str,
    spellchecker: Optional[SpellChecker] = None,
    ocr=False,
) -> list[Block]:
    page: pymupdf.Page = doc.load_page(pnum)

    if ocr:
        blocks = ocr_page(page, tess_lang, spellchecker)
    else:
        blocks = page.get_text("dict", sort=True, flags=settings.TEXT_FLAGS)["blocks"]

    return_blocks = []
    span_id = 0
    for block_idx, block in enumerate(blocks):
        block_lines = []
        for line_idx, line in enumerate(block["lines"]):
            spans = []
            for i, s in enumerate(line["spans"]):
                block_text = s["text"]
                bbox = s["bbox"]
                span_obj = Span(
                    text=block_text,
                    bbox=correct_rotation(bbox, page),
                    span_id=f"{pnum}_{block_idx}_{line_idx}_{span_id}",
                    font=f"{s['font']}_{parse_font_flags(s['flags'])}",  # Add font flags to end of font
                    color=s["color"],
                    ascender=s["ascender"],
                    descender=s["descender"],
                    flags=s["flags"],
                    origin=s["origin"],
                    size=round(s["size"]),
                )
                spans.append(span_obj)
                span_id += 1
            line_obj = Line(
                spans=spans,
                bbox=correct_rotation(line["bbox"], page),
            )

            if line_obj.area > 0:
                block_lines.append(line_obj)
        block_obj = Block(
            lines=block_lines, bbox=correct_rotation(block["bbox"], page), pnum=pnum
        )

        if len(block_lines) > 0:
            return_blocks.append(block_obj)

    if page.rotation > 0:
        return_blocks = sort_rotated_text(return_blocks)
    return return_blocks


def get_page_image(
    mupdf_page: pymupdf.Page, bbox: list[float], width: float, height: float
):
    # pt: 表述 字体大小，页面元素，行间距，行高等
    # dpi（dots per inch）: 在数字图像上下文指的是 像素(图像的大小取决于 dpi)
    # 1pt = 1/72 inch (pt可以理解成物理尺寸)
    # image width = inch width * dpi
    # image height = inch height * dpi

    # bbox = [0.0, 0.0, 612.0, 792.0]  612 is 612pt, 792 is 792pt
    # image width = 816 = 612pt/72(pt/inch) * 96 dpi
    # image height = 1056 = 792pt/72(pt/inch) * 96 dpi
    pixmap = mupdf_page.get_pixmap(dpi=settings.PDF_IMAGE_DPI, annots=False, clip=bbox)
    png_image = Image.open(io.BytesIO(pixmap.pil_tobytes(format="PNG")))
    image = png_image.convert("RGB")
    image_width, image_height = image.size

    assert isclose(image_width / width, image_height / height, abs_tol=2e-2)

    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    return ImageInfo(
        content_base64=image_base64,
        height=image.height,
        width=image.width,
        pt_bbox=bbox,
        pt_width=width,
        pt_height=height,
    )


def get_page(
    doc: pymupdf.Document,
    pnum: int,
    tess_lang: str,
    spell_lang: Optional[str],
    if_no_text: bool,
):
    # get specific spellchecker
    spellchecker = SpellChecker(language=spell_lang) if spell_lang else None

    # get page info though pdf utils
    page = Page(
        blocks=get_blocks(doc, pnum, tess_lang, spellchecker, ocr=False),
        pnum=pnum,
        bbox=doc[pnum].bound(),
    )

    # get ocr conditions
    ocr_conditions = [
        (
            # 'scanned document'
            if_no_text
            or (
                # 'digital document' but text occur error
                len(page.prelim_text) > 0
                and is_string_illegal(page.prelim_text, spellchecker)
            )
        ),
    ]

    # reocr current page (get page info failed)
    ocr_pages = 0
    ocr_success = 0
    ocr_failed = 0
    if all(ocr_conditions) or settings.OCR_ALL_PAGES:
        blocks = get_blocks(doc, pnum, tess_lang, spellchecker, ocr=True)
        page = Page(
            blocks=blocks,
            pnum=pnum,
            bbox=doc[pnum].bound(),
            rotation=page.rotation,
        )
        ocr_pages = 1
        if len(blocks) == 0:
            ocr_failed = 1
        else:
            ocr_success = 1

    # get page image
    page.image_info = get_page_image(
        doc.load_page(pnum), page.bbox, page.width, page.height
    )

    return page, {
        "ocr_pages": ocr_pages,
        "ocr_failed": ocr_failed,
        "ocr_success": ocr_success,
    }


def get_pages(
    doc: pymupdf.Document,
    tess_lang: str,
    spell_lang: Optional[str],
    max_pages: Optional[int] = None,
    parallel: int = settings.OCR_PARALLEL_WORKERS,
) -> Tuple[list[Page], list[Union[int, str, int]], dict]:
    pages: list[Page] = []
    ocr_pages = 0
    ocr_failed = 0
    ocr_success = 0

    # get num of pages to read
    page_num_to_read = min(max_pages, len(doc)) if max_pages else len(doc)
    # is digital pdf or scanned pdf
    if_no_text = len(get_doc_text(doc).strip()) == 0

    # process pages
    with ThreadPoolExecutor(
        max_workers=parallel, thread_name_prefix="GetPagesThread"
    ) as pool:
        pages_args = [
            (doc, pnum, tess_lang, spell_lang, if_no_text)
            for pnum in range(page_num_to_read)
        ]
        if parallel == 1:
            func = map
        else:
            func = pool.map
        pages_result = func(lambda args: get_page(*args), pages_args)

        for page_result in pages_result:
            page, ocr_stats = page_result
            pages.append(page)
            ocr_pages += ocr_stats["ocr_pages"]
            ocr_failed += ocr_stats["ocr_failed"]
            ocr_success += ocr_stats["ocr_success"]

    return (
        pages,
        doc.get_toc(),
        {"ocr_pages": ocr_pages, "ocr_failed": ocr_failed, "ocr_success": ocr_success},
    )


def get_specific_page(
    doc: pymupdf.Document,
    tess_lang: str,
    spell_lang: Optional[str],
) -> Page:
    if len(doc) <= 0 or tess_lang is None or tess_lang == "":
        return None
    if_no_text = len(get_doc_text(doc).strip()) == 0
    pages = get_page(doc, len(doc) // 2, tess_lang, spell_lang, if_no_text)
    if len(pages) > 0:
        return pages[0]
    else:
        return None
