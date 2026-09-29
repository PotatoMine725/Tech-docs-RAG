"""Question language (ADR-0003 D9): answers and the insufficient message follow it.

Rule: "vi" if the text holds a Vietnamese-specific letter (ă â đ ê ô ơ ư, any case) or a vowel with a Vietnamese tone
mark (grave, acute, hook above, tilde, dot below), else "en". The text is NFC-normalized first, so decomposed input
(base letter + combining mark) is detected too.

Known limitations: Vietnamese typed without diacritics is "en"; a text with an accented Latin letter shared with other
languages (e.g. "café": é is acute + e) is "vi". The corpus and questions are English or Vietnamese only.
"""
import re
import unicodedata

VIETNAMESE = "vi"
ENGLISH = "en"

# Base letters specific to Vietnamese, plus every tone-marked vowel (a ă â e ê i o ô ơ u ư y x 5 tones).
_VI_LETTERS = (
    "ăâđêôơư"
    "àáảãạằắẳẵặầấẩẫậ"
    "èéẻẽẹềếểễệ"
    "ìíỉĩị"
    "òóỏõọồốổỗộờớởỡợ"
    "ùúủũụừứửữự"
    "ỳýỷỹỵ"
)
_VI_PATTERN = re.compile(f"[{_VI_LETTERS}{_VI_LETTERS.upper()}]")


def detect_language(text: str) -> str:
    return VIETNAMESE if _VI_PATTERN.search(unicodedata.normalize("NFC", text)) else ENGLISH


LANGUAGE_NAMES = {ENGLISH: "English", VIETNAMESE: "Vietnamese"}
