"""Offline mutation demo for learning/14: copy src/tests to a scratch folder OUTSIDE the repo, break one line on
purpose, run the relevant tests there and report whether they notice. Never edits the repo.

    PYTHONDONTWRITEBYTECODE=1 python learning/_tools/exercises/mutation_demo.py <scratch-dir>
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
scratch = Path(sys.argv[1]) / "mutation-work"

MUTANTS = [
    ("M0 control (no change)", "src/knowledge_assistant/infrastructure/persistence/embedding_cache.py", None, None,
     ["tests/unit/infrastructure/test_embedding_cache.py"]),
    ("M1 cache key ignores the task", "src/knowledge_assistant/infrastructure/persistence/embedding_cache.py",
     'f"{model_id}|{task.value}|{text}"', 'f"{model_id}|{text}"',
     ["tests/unit/infrastructure/test_embedding_cache.py"]),
    ("M2 torn tail is no longer truncated", "src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py",
     r'handle.truncate(handle.read().rfind(b"\n") + 1)', "pass",
     ["tests/unit/infrastructure/test_jsonl_record_store.py"]),
    ("M3 fsync removed (no test can see it)", "src/knowledge_assistant/infrastructure/persistence/jsonl_record_store.py",
     "            os.fsync(handle.fileno())\n", "", ["tests/unit/infrastructure/test_jsonl_record_store.py"]),
]

for label, rel, old, new, tests in MUTANTS:
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True)
    for name in ("src", "tests"):
        shutil.copytree(REPO / name, scratch / name, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(REPO / "pyproject.toml", scratch / "pyproject.toml")
    if old is not None:
        target = scratch / rel
        text = target.read_text(encoding="utf-8")
        if text.count(old) < 1:
            print(label, "-> MUTATION DID NOT APPLY (pattern not found)")
            continue
        target.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", OPENBLAS_NUM_THREADS="1", PYTHONPATH=f"{scratch / 'src'};{scratch}")
    out = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-rf", *tests], cwd=scratch, env=env,
                         capture_output=True, text=True)
    failed = [l.split(" - ")[0] for l in out.stdout.splitlines() if l.startswith("FAILED")]
    print(label, "->", out.stdout.strip().splitlines()[-1], failed)
shutil.rmtree(scratch)
