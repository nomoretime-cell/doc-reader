from reader.settings import settings

from typing import Optional
from nltk import wordpunct_tokenize
from spellchecker import SpellChecker
import re


def alphanum_ratio(text):
    text = text.replace(" ", "")
    text = text.replace("\n", "")
    alphanumeric_count = sum([1 for c in text if c.isalnum()])

    if len(text) == 0:
        return 1

    ratio = alphanumeric_count / len(text)
    return ratio


def is_string_illegal(
    text,
    spellchecker: Optional[SpellChecker],
    misspell_threshold=0.7,
    space_threshold=0.6,
    newline_threshold=0.5,
    alphanum_threshold=0.4,
):
    if len(text) == 0:
        # Assume OCR failed if we have no text
        return True

    words = wordpunct_tokenize(text)
    words = [w for w in words if w.strip()]
    alpha_words = [word for word in words if word.isalnum()]

    if spellchecker:
        misspelled = spellchecker.unknown(alpha_words)
        if len(misspelled) > len(alpha_words) * misspell_threshold:
            return True

    spaces = len(re.findall(r"\s+", text))
    alpha_chars = len(re.sub(r"\s+", "", text))
    if spaces / (alpha_chars + spaces) > space_threshold:
        return True

    newlines = len(re.findall(r"\n+", text))
    non_newlines = len(re.sub(r"\n+", "", text))
    if newlines / (newlines + non_newlines) > newline_threshold:
        return True

    if alphanum_ratio(text) < alphanum_threshold:  # Garbled text
        return True

    invalid_chars = len([c for c in text if c in settings.INVALID_CHARS])
    if invalid_chars > max(3.0, len(text) * 0.02):
        return True

    return False


def parse_font_flags(flags):
    """Make font flags human readable."""
    flags_result: list[str] = []
    if flags & 2**0:
        # 上标
        flags_result.append("superscript")
    if flags & 2**1:
        # 斜体
        flags_result.append("italic")
    if flags & 2**2:
        # 笔画粗细不同
        flags_result.append("serifed")
    else:
        # 笔划粗细相同
        flags_result.append("sans")
    if flags & 2**3:
        # 等宽字体
        flags_result.append("monospaced")
    else:
        # 比例字体
        flags_result.append("proportional")
    if flags & 2**4:
        # 粗体
        flags_result.append("bold")
    return "_".join(flags_result)
