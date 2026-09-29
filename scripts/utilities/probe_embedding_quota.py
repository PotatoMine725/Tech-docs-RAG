"""V-1 probe (RAG-001a): send ONE batched embedding request with 3 texts.

The owner reads the AI Studio request count for the embedding model before and after,
so ADR-0005 can record whether 1 batched request counts as 1 or N requests.
Live call. Run once, on purpose:  .venv/Scripts/python.exe scripts/utilities/probe_embedding_quota.py
The raw result is saved to data/cache/probe-v1.json (git-ignored) so the call is never repeated.
"""

import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from knowledge_assistant.config import get_embedding_settings, get_gemini_api_key  # noqa: E402

# One prose, one code-heavy, one short chunk from Arm A.
PROBE_CHUNK_IDS = ["01:header-1600:0000", "01:header-1600:0011", "08:header-1600:0000"]
CHUNKS_FILE = PROJECT_ROOT / "data" / "processed" / "chunks" / "arm-a.jsonl"
OUT_FILE = PROJECT_ROOT / "data" / "cache" / "probe-v1.json"


def main() -> int:
    if OUT_FILE.exists():
        print(f"{OUT_FILE.relative_to(PROJECT_ROOT)} exists: probe already ran; not calling the API again.")
        return 1
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = get_gemini_api_key()
    if not api_key:
        print("GEMINI_API_KEY is not set.")
        return 2
    settings = get_embedding_settings()

    rows = {}
    with CHUNKS_FILE.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            if row["chunk_id"] in PROBE_CHUNK_IDS:
                rows[row["chunk_id"]] = row
    texts = [rows[cid]["embed_text"] for cid in PROBE_CHUNK_IDS]

    client = genai.Client(
        api_key=api_key, http_options=types.HttpOptions(timeout=int(settings.timeout_s * 1000))
    )
    sent_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    response = client.models.embed_content(
        model=settings.model,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT", output_dimensionality=settings.dim
        ),
    )

    result = {
        "sent_at_utc": sent_at,
        "model": settings.model,
        "output_dimensionality": settings.dim,
        "texts_in_request": len(texts),
        "http_requests_made": 1,
        "metadata": response.metadata.model_dump(mode="json") if response.metadata else None,
        "items": [],
    }
    for cid, text, emb in zip(PROBE_CHUNK_IDS, texts, response.embeddings or []):
        values = emb.values or []
        result["items"].append(
            {
                "chunk_id": cid,
                "chars": len(text),
                "chars_div_4": len(text) // 4,
                "dim": len(values),
                "l2_norm": math.sqrt(sum(v * v for v in values)),
                "statistics": emb.statistics.model_dump(mode="json") if emb.statistics else None,
                "values": values,
            }
        )
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(f"sent_at_utc={sent_at} model={settings.model} texts={len(texts)} http_requests=1")
    print(f"embeddings returned: {len(result['items'])}; metadata: {result['metadata']}")
    for item in result["items"]:
        print(
            f"  {item['chunk_id']}: chars={item['chars']} chars/4={item['chars_div_4']} "
            f"dim={item['dim']} l2_norm={item['l2_norm']:.4f} statistics={item['statistics']}"
        )
    print(f"saved {OUT_FILE.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
