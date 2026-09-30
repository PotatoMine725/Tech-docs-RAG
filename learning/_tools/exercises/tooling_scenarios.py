"""Offline scenarios for learning/02 (no network, no key; uses a temp file, never the repo's real .env).
Run from the worktree root:  PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="src;." python learning/_tools/exercises/tooling_scenarios.py
"""
import importlib.metadata
import os
import sys
import tempfile
from pathlib import Path

import knowledge_assistant
from knowledge_assistant.config import PROJECT_ROOT, resolve_project_path

print("== T1 which copy of the package is imported?")
print("imported from the current checkout:", Path(knowledge_assistant.__file__).resolve().is_relative_to(Path.cwd().resolve()), "| sys.path[1:3]:", [Path(p).name for p in sys.path[1:3]])

print("== T2 resolve_project_path (relative is anchored at the repo root, not the cwd)")
os.chdir(tempfile.gettempdir())
print(resolve_project_path("data/chroma") == PROJECT_ROOT / "data" / "chroma", resolve_project_path(Path("/abs/x")).is_absolute())

print("== T3 os.getenv default vs environment value")
os.environ.pop("KA_DEMO", None)
print(os.getenv("KA_DEMO", "fallback"), bool(os.getenv("KA_DEMO") or None))
os.environ["KA_DEMO"] = "from-env"
print(os.getenv("KA_DEMO", "fallback"))

print("== T4 python-dotenv: a real environment variable beats the file (override=False default)")
from dotenv import load_dotenv, dotenv_values
demo = Path(tempfile.mkdtemp(prefix="ka-dotenv-")) / "demo.env"
demo.write_text("KA_DEMO=from-file\nKA_ONLY_IN_FILE=hello\n", encoding="utf-8")
print(dotenv_values(demo))
load_dotenv(demo)
print(os.getenv("KA_DEMO"), os.getenv("KA_ONLY_IN_FILE"))
load_dotenv(demo, override=True)
print(os.getenv("KA_DEMO"))

print("== T5 installed distribution metadata (from the venv; not from .env)")
print(importlib.metadata.version("knowledge-assistant"), importlib.metadata.requires("knowledge-assistant")[:3])
