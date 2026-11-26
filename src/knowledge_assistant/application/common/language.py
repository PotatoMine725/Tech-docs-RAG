"""Question language (ADR-0003 D9): answers and the insufficient message follow it.

Rule: "vi" if the text holds a Vietnamese-specific letter (ă â đ ê ô ơ ư, any case) or a vowel with a Vietnamese tone
mark (grave, acute, hook above, tilde, dot below), else "en". The text is NFC-normalized first, so decomposed input
(base letter + combining mark) is detected too.

Vietnamese typed without diacritics (common for students): with no Vietnamese letter, the text is still "vi" when at
least 2 of its words, and at least a quarter of them, are common Vietnamese syllables written in ASCII
(`_VI_ASCII_WORDS`: function words and question words that are not English words, e.g. "khong", "duoc", "nhung",
"la", "gi"). Code, identifiers and numbers count as words, so a mostly-English sentence stays "en".

Known limitations: a text with an accented Latin letter shared with other languages (e.g. "café": é is acute + e) is
"vi"; a very short diacritic-less Vietnamese text (one word) is "en". The corpus and questions are English or
Vietnamese only.
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


# Common Vietnamese syllables without diacritics that are not (common) English words. Kept short on purpose: a word
# here must be frequent in Vietnamese questions and rare in English text.
_VI_ASCII_WORDS = frozenset("""
    khong duoc nhung cua mot nhieu trong nguoi chung nay gi la va voi cac nhu thi bao lau nao sao tai vi
    phai co cho khi nhat duoi tren giua sau truoc cung hay hoac neu ma rang theo ve den tu lam dung cach
    gom bang loai viec nhan the hien dieu tri benh thuoc xet nghiem sinh vien hoc mon phan muc chuong dieu
    ky thuat lop phuong thuc ham bien gia tri ket qua nao kham thuc hoi thuong thay dau hieu xay ra
    """.split()) - {"the", "co", "ma", "ham", "tu", "den", "vi", "nhan", "hien", "chung"}
_WORD = re.compile(r"[A-Za-z0-9_#+.()]+")


def _ascii_vietnamese(text: str) -> bool:
    words = [w.lower().strip(".()") for w in _WORD.findall(text)]
    words = [w for w in words if w]
    hits = sum(1 for w in words if w in _VI_ASCII_WORDS)
    return hits >= 2 and hits * 4 >= len(words)


def detect_language(text: str) -> str:
    normalized = unicodedata.normalize("NFC", text)
    if _VI_PATTERN.search(normalized) or _ascii_vietnamese(normalized):
        return VIETNAMESE
    return ENGLISH


LANGUAGE_NAMES = {ENGLISH: "English", VIETNAMESE: "Vietnamese"}
