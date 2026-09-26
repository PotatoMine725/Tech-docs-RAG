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
        ("dependency injection la gi", "en"),  # Vietnamese without diacritics: documented limitation
        ("Cach dung async await trong C#", "en"),  # same limitation
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
