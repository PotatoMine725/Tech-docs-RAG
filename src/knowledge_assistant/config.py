import os


def get_chroma_path() -> str:
    return os.getenv("CHROMA_PATH", r"D:\ChromaDB")


def get_gemini_api_key() -> str | None:
    """Read the key from the environment only; never log or print it."""
    return os.getenv("GEMINI_API_KEY") or None
