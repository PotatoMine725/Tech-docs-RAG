"""Domain models. Fields marked TBD are intentionally undecided (see docs/architecture/data-model.md)."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    source_id: str
    name: str


@dataclass(frozen=True)
class ParsedDocument:
    document: Document


@dataclass(frozen=True)
class DocumentChunk:
    source_id: str


@dataclass(frozen=True)
class Citation:
    source_id: str
    document_name: str
    location_type: str  # e.g. page | section | heading | paragraph | line | url (extensible)
    location: str
    excerpt: str


@dataclass(frozen=True)
class Question:
    text: str


@dataclass(frozen=True)
class EvaluationCase:
    question: Question


@dataclass(frozen=True)
class EvaluationResult:
    case: EvaluationCase


@dataclass(frozen=True)
class Experiment:
    name: str
