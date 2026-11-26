import unicodedata

import pytest

from knowledge_assistant.application.common.language import detect_language


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("How do I register a scoped service?", "en"),
        ("What is a static class in C#?", "en"),
        ("Explain async and await in C#.", "en"),
        ("", "en"),
        ("Làm thế nào để đăng ký một dịch vụ?", "vi"),
        ("Lớp tĩnh trong C# là gì?", "vi"),
        ("Middleware hoạt động ra sao", "vi"),  # tone marks only on some words
        ("ĐỊNH TUYẾN TRONG ASP.NET CORE", "vi"),  # upper case
        ("dependency injection la gi", "vi"),  # Vietnamese without diacritics (common syllables)
        ("Cach dung async await trong C#", "vi"),
        ("Xet nghiem HBsAg duong tinh keo dai bao lau thi duoc coi la man tinh?", "vi"),
        ("Phuong thuc getPort() va getLocalPort() cua lop Socket khac nhau the nao?", "vi"),
        ("gi", "en"),  # one word is not enough
        ("The value of the variable is set in the constructor.", "en"),  # English words only
        ("Use la and gi as variable names in the loop.", "en"),  # 2 hits but under a quarter of the words
        ("ư", "vi"),  # a Vietnamese-only base letter alone
        ("Is café a Vietnamese word?", "vi"),  # é is shared with other languages: documented limitation
    ],
)
def test_detect_language(text, expected):
    assert detect_language(text) == expected


def test_decomposed_unicode_is_normalized_first():
    decomposed = unicodedata.normalize("NFD", "Lớp tĩnh là gì?")
    assert decomposed != unicodedata.normalize("NFC", decomposed)
    assert detect_language(decomposed) == "vi"
