"""Offline scenarios for learning/04 (no network, no key; temp files only, outside the repo). Run from the worktree root:
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="src;." python learning/_tools/exercises/persistence_scenarios.py
"""
import json
import struct
import tempfile
from pathlib import Path

from knowledge_assistant.application.evaluation.records import latest_records
from knowledge_assistant.core.exceptions import EmbeddingError, EvaluationError
from knowledge_assistant.core.interfaces.embedding import EmbeddingTask
from knowledge_assistant.infrastructure.persistence.embedding_cache import CachingEmbedder, cache_key, _from_blob, _to_blob
from knowledge_assistant.infrastructure.persistence.jsonl_record_store import JsonlRecordStore
from tests.fakes import FakeEmbedder

tmp = Path(tempfile.mkdtemp(prefix="ka-learning-"))

print("== P1 append-only + read")
store = JsonlRecordStore(tmp / "run1", redact=lambda s: s.replace("SECRETKEY", "[redacted]"))
store.append_record({"case_id": "c1", "arm": "A", "mode": "full", "status": "error"})
store.append_record({"case_id": "c1", "arm": "A", "mode": "full", "status": "ok", "note": "has SECRETKEY inside"})
raw = (tmp / "run1" / "records.jsonl").read_bytes()
print(raw.count(b"\n"), b"SECRETKEY" in raw, b"[redacted]" in raw)
print([r["status"] for r in store.read_records()], {k: v["status"] for k, v in latest_records(store.read_records()).items()})

print("== P2 torn tail is ignored on read, cut off on next append")
path = tmp / "run1" / "records.jsonl"
with path.open("ab") as h:
    h.write(b'{"case_id": "c2", "arm": "A", "mo')   # a crash mid-write
print("read ignores torn tail:", len(store.read_records()))
store.append_record({"case_id": "c2", "arm": "A", "mode": "full", "status": "ok"})
print("after append:", len(store.read_records()), path.read_bytes().count(b"\n"))

print("== P3 a complete but invalid line is corruption")
with path.open("ab") as h:
    h.write(b"not json\n")
try:
    store.read_records()
except EvaluationError as e:
    print("EvaluationError:", str(e)[-45:])

print("== P4 NaN is refused before any write")
before = len(path.read_bytes())
try:
    store.append_record({"case_id": "c3", "score": float("nan")})
except ValueError as e:
    print("ValueError:", str(e)[:40], "| file unchanged:", len(path.read_bytes()) == before)

print("== P5 manifest is replaced atomically (no .tmp left)")
store.write_manifest({"run_id": "r1", "config": {"a": 1}})
store.write_manifest({"run_id": "r1", "config": {"a": 2}})
print(store.read_manifest(), sorted(p.name for p in (tmp / "run1").iterdir() if p.name.startswith("run.json")))

print("== C1 cache_key depends on model, task, text")
k = cache_key("m@8", EmbeddingTask.DOCUMENT, "hello")
print(len(k), k == cache_key("m@8", EmbeddingTask.DOCUMENT, "hello"), k == cache_key("m@8", EmbeddingTask.QUERY, "hello"),
      k == cache_key("m@9", EmbeddingTask.DOCUMENT, "hello"), k == cache_key("m@8", EmbeddingTask.DOCUMENT, "hello "))

print("== C2 float32 BLOB round trip")
v = [0.1, -0.5, 1 / 3]
blob = _to_blob(v)
print(len(blob), _from_blob(blob, 3), struct.unpack("<3f", blob) == tuple(_from_blob(blob, 3)))

print("== C3 cache: duplicates sent once, second run all hits")
inner = FakeEmbedder(batch_size=2)
with CachingEmbedder(inner, tmp / "cache.sqlite") as cache:
    out = cache.embed(["a", "b", "a", "c", "d"], EmbeddingTask.DOCUMENT)
    print(len(out), cache.stats(), [len(c[0]) for c in inner.calls])
    out2 = cache.embed(["a", "b", "a", "c", "d"], EmbeddingTask.DOCUMENT)
    print(cache.stats(), len(inner.calls))
    cache.embed(["a"], EmbeddingTask.QUERY)
    print("same text, other task is a miss:", cache.stats()["misses"])

print("== C4 crash mid-run keeps every paid call; rerun sends only the rest")
class Flaky(FakeEmbedder):
    def __init__(self):
        super().__init__(batch_size=2); self.fail_on_call = 2
    def embed(self, texts, task):
        if len(self.calls) + 1 == self.fail_on_call:
            raise RuntimeError("quota")
        return super().embed(texts, task)
flaky = Flaky()
texts = ["t1", "t2", "t3", "t4", "t5"]
with CachingEmbedder(flaky, tmp / "cache2.sqlite") as cache:
    try:
        cache.embed(texts, EmbeddingTask.DOCUMENT)
    except RuntimeError as e:
        print("stopped:", e, "| stored after 1st call:", cache.stats()["misses"])
flaky.fail_on_call = 99
with CachingEmbedder(flaky, tmp / "cache2.sqlite") as cache:
    cache.embed(texts, EmbeddingTask.DOCUMENT)
    print("rerun:", cache.stats()["hits"], "hits,", cache.stats()["misses"], "misses; texts sent in 2nd run:", [c[0] for c in flaky.calls][1:])

print("== C5 bad plan_calls is rejected")
class Bad(FakeEmbedder):
    def plan_calls(self, texts):
        return [texts[:1]]
try:
    with CachingEmbedder(Bad(), tmp / "cache3.sqlite") as cache:
        cache.embed(["x", "y"], EmbeddingTask.DOCUMENT)
except EmbeddingError as e:
    print("EmbeddingError:", e)
print("determinism: same text, same vector:", FakeEmbedder().vector("x") == FakeEmbedder().vector("x"))
