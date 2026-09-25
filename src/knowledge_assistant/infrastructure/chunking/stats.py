"""Descriptive per-arm chunk statistics (ADR-0003 D8): counts, size distribution, code-fence cuts, duplicates."""
import math
from collections.abc import Sequence

from knowledge_assistant.core.models import DocumentChunk, ParsedDocument
from knowledge_assistant.infrastructure.chunking.chunk_builder import ChunkingResult
from knowledge_assistant.infrastructure.chunking.markdown_structure import fenced_ranges


def cuts_code_fence(chunk: DocumentChunk, fences: Sequence[tuple[int, int]]) -> bool:
    """True when the chunk contains part, but not all, of a fenced code block."""
    for fence_start, fence_end in fences:
        overlaps = fence_start < chunk.char_end and chunk.char_start < fence_end
        contained = chunk.char_start <= fence_start and fence_end <= chunk.char_end
        if overlaps and not contained:
            return True
    return False


def percentile(sorted_values: Sequence[int], fraction: float) -> int:
    """Nearest-rank percentile of an ascending, non-empty sequence."""
    rank = max(1, math.ceil(fraction * len(sorted_values)))
    return sorted_values[rank - 1]


def chunk_stats(
    documents: Sequence[ParsedDocument], results: Sequence[ChunkingResult], chunker_config: str, small_chunk_chars: int
) -> dict:
    per_document: dict[str, int] = {}
    duplicates: dict[str, int] = {}
    sizes: list[int] = []
    cutting = heading_only = 0
    for document, result in zip(documents, results, strict=True):
        fences = fenced_ranges(document.text)
        per_document[document.source_id] = len(result.chunks)
        duplicates[document.source_id] = result.duplicates_dropped
        for chunk in result.chunks:
            sizes.append(len(chunk.display_text))
            cutting += cuts_code_fence(chunk, fences)
            heading_only += "\n" not in chunk.display_text and chunk.display_text.startswith("#")
    sizes.sort()
    total = len(sizes)
    return {
        "chunker_config": chunker_config,
        "documents": len(documents),
        "chunks_total": total,
        "chunks_per_document": per_document,
        "size_chars": {
            "min": sizes[0],
            "p50": percentile(sizes, 0.5),
            "p90": percentile(sizes, 0.9),
            "max": sizes[-1],
            "percentile_method": "nearest-rank",
        },
        "chunks_cutting_code_fence": cutting,
        "pct_chunks_cutting_code_fence": round(100 * cutting / total, 2),
        "documents_with_one_chunk": sorted(source for source, count in per_document.items() if count == 1),
        "duplicates_dropped": sum(duplicates.values()),
        "duplicates_dropped_per_document": {source: count for source, count in duplicates.items() if count},
        "chunks_under_small_chunk_chars": sum(size < small_chunk_chars for size in sizes),
        "small_chunk_chars": small_chunk_chars,
        "heading_only_chunks": heading_only,
    }
