"""Offline scenarios for learning/08 (no network, no key). Run from the worktree root:
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="src;." python learning/_tools/exercises/generation_scenarios.py
"""
from knowledge_assistant.application.citation.citations import (
    count_uncited_sentences, excerpt, extract_markers, resolve_citations, split_sentences)
from knowledge_assistant.application.generation.answer_question import parse_answer_json
from knowledge_assistant.application.generation.prompt_builder import PromptBuilder, render_passages
from knowledge_assistant.core.exceptions import GenerationError
from knowledge_assistant.core.models import RetrievedChunk
from tests.fakes import make_chunk


def hit(n, text, score=0.9):
    return RetrievedChunk(chunk=make_chunk(source_id=f"{n:02d}", text=text), score=score, rank=n)

hits = (hit(1, "A is one thing."), hit(2, "B is another thing."))

print("== C1 extract_markers")
for t in ["A is x. [1] B is y [2][1].", "Use `args[0]` here [2].", "```\nx[1]\n```\nDone [1]", "zero [0] and [3]"]:
    print(repr(t), "->", extract_markers(t))

print("== C2 resolve_citations")
for ans, cited in [("A holds [1]. B holds [2].", [1, 2]), ("A holds [1] [5].", [1]), ("No markers here.", [2]), ("A [1].", [1, 7])]:
    cleaned, cits, dropped = resolve_citations(ans, cited, hits)
    print(repr(ans), cited, "->", repr(cleaned), [c.marker for c in cits], dropped)

print("== C3 count_uncited_sentences")
for t in ["This sentence has five words. [1]", "This sentence has five words.", "Short one. This sentence has five words though [2].", "Use `a[1]` in this sentence please."]:
    print(repr(t), "->", count_uncited_sentences(t))

print("== C4 build_prompt with braces")
tpl = "LANG={answer_language}\nCTX:\n{passages}\nQ: {question}"
pb = PromptBuilder(tpl, "t")
brace_hits = (hit(1, "Use {question} and {passages} literally."),)
print(pb.build("What is {answer_language}?", "vi", brace_hits))

print("== C5 parse_answer_json")
cases = {
    "ok": '{"insufficient": false, "answer": "x [1]", "cited_passages": [1], "missing_information": ""}',
    "bad json": "not json",
    "list": "[1]",
    "missing key": '{"insufficient": false, "answer": "x"}',
    "bool as int": '{"insufficient": false, "answer": "x", "cited_passages": [true], "missing_information": ""}',
    "empty answer": '{"insufficient": false, "answer": "  ", "cited_passages": [], "missing_information": ""}',
    "insufficient ok": '{"insufficient": true, "answer": "", "cited_passages": [1], "missing_information": "nothing"}',
}
for name, text in cases.items():
    try:
        parse_answer_json(text); print(name, "-> OK")
    except GenerationError as e:
        print(name, "-> GenerationError:", str(e)[:70])

print("== C6 excerpt")
print(repr(excerpt("word " * 100, 12)), repr(excerpt("short text")))
