from pathlib import Path
import os
import sys

import chromadb
from dotenv import load_dotenv
from google import genai

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from knowledge_assistant.config import get_chroma_path


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    chroma_path = Path(get_chroma_path())
    chroma_path.mkdir(parents=True, exist_ok=True)

    client = chromadb.PersistentClient(path=str(chroma_path))
    collection = client.get_or_create_collection(name="environment_smoke_test")
    collection.upsert(
        ids=["smoke-1", "smoke-2"],
        documents=["ChromaDB stores embeddings locally.", "Gemini SDK is configured by an environment variable."],
        metadatas=[{"kind": "smoke"}, {"kind": "smoke"}],
        embeddings=[[1.0, 0.0], [0.0, 1.0]],
    )
    results = collection.query(query_embeddings=[[1.0, 0.0]], n_results=1)
    if not results["ids"] or not results["ids"][0]:
        raise RuntimeError("ChromaDB smoke query returned no results.")
    client.delete_collection(name="environment_smoke_test")

    api_key = os.environ.get("GEMINI_API_KEY")
    if api_key:
        genai.Client(api_key=api_key)
        gemini_status = "initialized from GEMINI_API_KEY"
    else:
        gemini_status = "skipped: GEMINI_API_KEY is not set"

    print(f"ChromaDB persistent path: {chroma_path}")
    print("ChromaDB collection insert/query: passed")
    print(f"Gemini SDK: {gemini_status}")


if __name__ == "__main__":
    main()
