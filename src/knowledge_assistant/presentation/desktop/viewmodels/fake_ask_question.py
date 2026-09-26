"""Offline stand-in for the real ask-question use case (GUI-001-pre). No network, no index.

Trigger words in the question pick the scenario (case-insensitive):
  quota -> quota error      503 / unavailable -> service error     noindex -> missing-index error
  insufficient -> insufficient answer     related -> insufficient + one related-only citation
  slow -> 3 s delay (proves the window stays responsive)
Anything else answers. Vietnamese is detected from diacritics and the reply is in that language.
"""
from __future__ import annotations

import re
import time
from typing import Callable

from .contracts import AnswerResult, AskQuestionError, Citation

_VI_CHARS = re.compile(r"[àáảãạăâđêôơưèéẻẽẹìíỉĩịòóỏõọùúủũụỳýỷỹỵ]", re.IGNORECASE)

_EXCERPT_1 = (
    "Dependency injection (DI) is a technique in which an object receives the other objects it depends on, "
    "rather than creating them itself."
)
_EXCERPT_2 = "Register services in the container at startup, then resolve them through constructors."
_EXCERPT_REL = "Middleware components form a request pipeline; each one can run logic before and after the next."


def _cite(marker: int, excerpt: str, name: str, loc: str, related: bool = False) -> Citation:
    slug = name.lower().replace(" ", "-")
    return Citation(marker, name, loc, excerpt, f"https://example.invalid/docs/{slug}", related)


class FakeAskQuestion:
    def __init__(self, sleep: Callable[[float], None] = time.sleep, slow_seconds: float = 3.0,
                 default_seconds: float = 0.5) -> None:
        self._sleep = sleep
        self._slow = slow_seconds
        self._default = default_seconds

    def ask(self, question: str, arm: str) -> AnswerResult:
        q = question.lower()
        self._sleep(self._slow if "slow" in q else self._default)
        if "quota" in q:
            raise AskQuestionError("quota", "429 RESOURCE_EXHAUSTED: quota exceeded")
        if "503" in q or "unavailable" in q:
            raise AskQuestionError("unavailable", "503 UNAVAILABLE: model overloaded")
        if "noindex" in q:
            raise AskQuestionError("no_index", "collection 'arm_a' not found")

        vi = bool(_VI_CHARS.search(question))
        lang = "vi" if vi else "en"
        latency = {"embed_query": 120.0, "retrieve": 35.0, "generate": 900.0, "total": 1055.0}
        model = "fake-model"

        if "insufficient" in q or "related" in q:
            related = ()
            if "related" in q:
                related = (_cite(1, _EXCERPT_REL, "ASP.NET Core Middleware", "Middleware > Pipeline", True),)
            if vi:
                answer = "Bộ tài liệu hiện có không chứa đủ thông tin để trả lời câu hỏi này."
                missing = "Tài liệu không đề cập đến chủ đề này."
            else:
                answer = "The document collection does not contain enough information to answer this question."
                missing = "The documents do not cover this topic."
            return AnswerResult(question, lang, answer, True, "llm", missing, related, latency, model)

        if vi:
            answer = (f"[Nhánh {arm}] Dependency injection là kỹ thuật trong đó một đối tượng nhận các phụ thuộc "
                      "từ bên ngoài thay vì tự tạo chúng [1]. Đăng ký dịch vụ trong container khi khởi động [2].")
        else:
            answer = (f"[Arm {arm}] Dependency injection lets an object receive its dependencies instead of "
                      "creating them itself [1]. Register services in the container at startup [2].")
        cites = (
            _cite(1, _EXCERPT_1, "Dependency Injection Guide", "Overview > What is DI"),
            _cite(2, _EXCERPT_2, "Dependency Injection Guide", "Usage > Registering services"),
        )
        return AnswerResult(question, lang, answer, False, None, None, cites, latency, model)
