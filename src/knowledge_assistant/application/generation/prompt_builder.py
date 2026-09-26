"""Answer prompt (OD-10, generation-spec.md). The template is a versioned file (`config/prompts/<version>.md`); the
version string is the file name. Prompts are never inlined in code.

Placeholders are replaced by one regex pass (not `str.format`), so braces in passages or questions are copied unchanged.
"""
import re
from pathlib import Path

from knowledge_assistant.application.common.passage import passage_body
from knowledge_assistant.application.common.language import LANGUAGE_NAMES
from knowledge_assistant.core.models import HEADING_PATH_SEPARATOR, RetrievedChunk

PLACEHOLDERS = ("{answer_language}", "{passages}", "{question}")
_PLACEHOLDER = re.compile(r"\{(answer_language|passages|question)\}")

# Gemini JSON mode schema (all keys required).
ANSWER_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "insufficient": {"type": "boolean"},
        "answer": {"type": "string"},
        "cited_passages": {"type": "array", "items": {"type": "integer"}},
        "missing_information": {"type": "string"},
    },
    "required": ["insufficient", "answer", "cited_passages", "missing_information"],
}


def load_template(prompts_dir: str | Path, version: str) -> str:
    template = (Path(prompts_dir) / f"{version}.md").read_text(encoding="utf-8")
    missing = [p for p in PLACEHOLDERS if p not in template]
    if missing:
        raise ValueError(f"prompt template {version} lacks {missing}")
    return template


def render_passage(number: int, hit: RetrievedChunk) -> str:
    chunk = hit.chunk
    heading = HEADING_PATH_SEPARATOR.join(chunk.heading_path)
    return f"[{number}] {chunk.document_name} — {heading}\n{passage_body(chunk).strip()}"


def render_passages(retrieved: tuple[RetrievedChunk, ...] | list[RetrievedChunk]) -> str:
    """Passages numbered 1..k in the given (rank) order, separated by a blank line."""
    return "\n\n".join(render_passage(number, hit) for number, hit in enumerate(retrieved, start=1))


def build_prompt(template: str, question: str, language: str, retrieved: tuple[RetrievedChunk, ...]) -> str:
    """One pass over the template: inserted text is never scanned again, so a "{question}" inside a passage stays."""
    values = {
        "answer_language": LANGUAGE_NAMES[language],
        "passages": render_passages(retrieved),
        "question": question,
    }
    return _PLACEHOLDER.sub(lambda match: values[match.group(1)], template)


class PromptBuilder:
    def __init__(self, template: str, version: str) -> None:
        self.template = template
        self.version = version

    @classmethod
    def from_dir(cls, prompts_dir: str | Path, version: str) -> "PromptBuilder":
        return cls(load_template(prompts_dir, version), version)

    def build(self, question: str, language: str, retrieved: tuple[RetrievedChunk, ...]) -> str:
        return build_prompt(self.template, question, language, retrieved)
