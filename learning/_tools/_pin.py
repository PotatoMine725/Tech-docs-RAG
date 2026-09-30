"""Read repo files at the pinned commit (git blob), never from the working tree. Offline, read-only."""
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[2]
PIN = "762b754ecb6c8aae21e005246649252c8bfd0762"
_cache = {}


def read_lines(rel):
    """Lines (split on \n, no trailing-newline artefact removed) of `rel` at PIN, or None if not tracked there."""
    if rel not in _cache:
        done = subprocess.run(["git", "show", f"{PIN}:{rel}"], cwd=ROOT, capture_output=True)
        _cache[rel] = done.stdout.decode("utf-8").split("\n") if done.returncode == 0 else None
    return _cache[rel]
