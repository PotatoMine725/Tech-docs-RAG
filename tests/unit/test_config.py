import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from knowledge_assistant.config import (
    PROJECT_ROOT,
    get_chroma_path,
    get_chunks_dir,
    get_embedding_settings,
    get_logs_dir,
)

PATH_VARS = ("CHROMA_PATH", "CHUNKS_DIR", "LOGS_DIR", "EMBEDDING_CACHE_PATH")


@pytest.fixture
def no_path_env(monkeypatch):
    for name in PATH_VARS:
        monkeypatch.delenv(name, raising=False)


def default_paths() -> dict[str, str]:
    return {
        "chroma": str(get_chroma_path()),
        "cache": str(get_embedding_settings().cache_path),
        "chunks": str(get_chunks_dir()),
        "logs": str(get_logs_dir()),
    }


def test_project_root_is_the_repo_root():
    assert (PROJECT_ROOT / "pyproject.toml").is_file()
    assert (PROJECT_ROOT / "src" / "knowledge_assistant" / "config.py").is_file()


def test_default_paths_resolve_from_the_repo_root(no_path_env):
    """OD-7 (ADR-0005 D16): data/chroma/, git-ignored, rebuilt by script; never relative to the cwd."""
    assert get_chroma_path() == PROJECT_ROOT / "data" / "chroma"
    assert get_embedding_settings().cache_path == PROJECT_ROOT / "data" / "cache" / "embeddings.sqlite"
    assert get_chunks_dir() == PROJECT_ROOT / "data" / "processed" / "chunks"
    assert get_logs_dir() == PROJECT_ROOT / "data" / "logs"


def test_relative_env_values_resolve_from_the_repo_root(monkeypatch):
    monkeypatch.setenv("CHROMA_PATH", "data/chroma")  # the .env.example value
    monkeypatch.setenv("EMBEDDING_CACHE_PATH", "data/cache/other.sqlite")
    assert get_chroma_path() == PROJECT_ROOT / "data" / "chroma"
    assert get_embedding_settings().cache_path == PROJECT_ROOT / "data" / "cache" / "other.sqlite"


def test_absolute_env_values_are_kept(monkeypatch, tmp_path):
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("LOGS_DIR", str(tmp_path / "logs"))
    assert get_chroma_path() == tmp_path / "chroma"
    assert get_logs_dir() == tmp_path / "logs"


def test_a_process_started_in_another_cwd_uses_the_same_files(no_path_env, tmp_path):
    env = {k: v for k, v in os.environ.items() if k not in PATH_VARS}
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    code = (
        "import json\n"
        "from knowledge_assistant.config import get_chroma_path, get_chunks_dir, get_embedding_settings, get_logs_dir\n"
        "print(json.dumps({'chroma': str(get_chroma_path()), 'cache': str(get_embedding_settings().cache_path),"
        " 'chunks': str(get_chunks_dir()), 'logs': str(get_logs_dir())}))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True, check=True
    )
    child = json.loads(result.stdout)
    assert child == default_paths()
    assert child == {
        "chroma": str(PROJECT_ROOT / "data" / "chroma"),
        "cache": str(PROJECT_ROOT / "data" / "cache" / "embeddings.sqlite"),
        "chunks": str(PROJECT_ROOT / "data" / "processed" / "chunks"),
        "logs": str(PROJECT_ROOT / "data" / "logs"),
    }


def test_the_chunk_builder_writes_where_config_reads(no_path_env):
    script = PROJECT_ROOT / "scripts" / "ingestion" / "build_chunks.py"
    spec = importlib.util.spec_from_file_location("build_chunks_script", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert Path(module.CHUNKS_DIR) == get_chunks_dir()
