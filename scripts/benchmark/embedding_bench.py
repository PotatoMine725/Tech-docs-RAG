"""Retrieval quality, speed and memory of local ONNX embedders against the Gemini baseline. Measures only.

What changes between runs: the model (EmbeddingGemma 1 / 2) and its precision (fp32, fp16, int8, int4).
What is held fixed: arm-A chunks (`embed_text`), the eval split's 32 answerable questions, the prompts
(``title: none | text: `` for documents, ``task: search result | query: `` for queries), the token limit, and the
scoring: plain cosine top-k over all chunks, no duplicate dropping, no score gate. Gemini is scored the same way from
the embedding cache (no API call), so every row of the table is like for like. The production retriever adds dedup
and a gate, so its recorded eval numbers are not comparable to these; ``--check-recorded`` re-scores a recorded run
with this harness's metric calls to show they reproduce the saved summary.

Each (model, variant, profile) runs in its own subprocess, so peak memory is that run's alone.

Profiles:
- ``full``: all cores, ONNX Runtime default threads. Encodes every chunk; this run gives the quality numbers.
- ``lowend``: pinned to 4 efficiency cores with 4 intra-op threads, a rough stand-in for a 4-core gen-10 laptop
  CPU. Encodes a fixed subset of chunks (speed only) and the single-query latency. It cannot emulate the target's
  instruction set (INT8 speed depends on VNNI) or its memory bandwidth, so its numbers are indicative only.

    python scripts/benchmark/embedding_bench.py --models-dir D:/models/embeddinggemma
    python scripts/benchmark/embedding_bench.py --models-dir D:/models/embeddinggemma --models gemma1 \
        --variants int8 --profiles full
    python scripts/benchmark/embedding_bench.py --check-recorded   # harness self-check, no model needed
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
import platform
import sqlite3
import statistics
import struct
import subprocess
import sys
import time
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

CHUNKS = REPO_ROOT / "data/processed/chunks/arm-a.jsonl"
QUESTIONS = REPO_ROOT / "data/evaluation/questions/eval-v1.jsonl"
SPANS = REPO_ROOT / "data/evaluation/questions/expected-spans-v1.json"
GEMINI_CACHE = REPO_ROOT / "data/cache/embeddings.sqlite"
GEMINI_MODEL_ID = "gemini-embedding-001@768"
RECORDED_RUN = REPO_ROOT / "data/evaluation/results/20260928-eval-A-full-491f137/records.jsonl"
RECORDED_SUMMARY = (REPO_ROOT / "data/evaluation/results/"
                    "summary-20260928-eval-A-full-491f137-20260928-eval-B-full-491f137.json")
OUT_ROOT = REPO_ROOT / "data/experiments/embedding-bench"

DOC_PREFIX = "title: none | text: "
QUERY_PREFIX = "task: search result | query: "
VARIANTS = {"fp32": "model", "fp16": "model_fp16", "int8": "model_quantized", "int4": "model_q4"}
MODELS = ("gemma1", "gemma2")
KS = (1, 3, 5, 10)


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# --------------------------------------------------------------------------------------------- Windows process bits

class _MemCounters(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]


def memory_mb() -> dict[str, float]:
    """Working set (RAM in use) and pagefile usage (private commit), current and peak, in MB. Windows only."""
    if os.name != "nt":
        return {}
    counters = _MemCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    if not kernel32.K32GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        return {}
    mb = 1024 * 1024
    return {"working_set": counters.WorkingSetSize / mb, "peak_working_set": counters.PeakWorkingSetSize / mb,
            "private": counters.PagefileUsage / mb, "peak_private": counters.PeakPagefileUsage / mb}


def efficiency_cores() -> dict[str, list[int]]:
    """Logical processor ids by core class on Windows: {"e": [...], "p": [...]}. Empty lists when not hybrid."""
    kernel32 = ctypes.WinDLL("kernel32")
    length = wintypes.DWORD(0)
    kernel32.GetLogicalProcessorInformationEx(0, None, ctypes.byref(length))  # RelationProcessorCore = 0
    buf = ctypes.create_string_buffer(length.value)
    if not kernel32.GetLogicalProcessorInformationEx(0, buf, ctypes.byref(length)):
        raise OSError(ctypes.get_last_error())
    raw, offset, cores = buf.raw, 0, []
    while offset < length.value:
        _, size = struct.unpack_from("<II", raw, offset)
        efficiency_class = raw[offset + 9]
        group_count = struct.unpack_from("<H", raw, offset + 30)[0]
        ids = []
        for g in range(group_count):
            mask, group = struct.unpack_from("<QH", raw, offset + 32 + 16 * g)
            if group == 0:
                ids += [i for i in range(64) if mask >> i & 1]
        cores.append((efficiency_class, ids))
        offset += size
    classes = sorted({c for c, _ in cores})
    if len(classes) < 2:
        return {"e": [], "p": []}
    low = classes[0]
    return {"e": [i for c, ids in cores if c == low for i in ids],
            "p": [i for c, ids in cores if c != low for i in ids]}


def pin_to(cpu_ids: list[int]) -> None:
    kernel32 = ctypes.WinDLL("kernel32")
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    kernel32.SetProcessAffinityMask.argtypes = [wintypes.HANDLE, ctypes.c_size_t]
    mask = sum(1 << i for i in cpu_ids)
    if not kernel32.SetProcessAffinityMask(kernel32.GetCurrentProcess(), ctypes.c_size_t(mask)):
        raise OSError(f"SetProcessAffinityMask({cpu_ids}) failed")


# ------------------------------------------------------------------------------------------------------- worker

def worker(args: argparse.Namespace) -> int:
    """One (model, variant, profile): load, encode, time, write vectors and a JSON record. Run as a subprocess."""
    if args.pin:
        pin_to([int(x) for x in args.pin.split(",")])
    mem_start = memory_mb()

    import onnxruntime as ort
    from tokenizers import Tokenizer

    model_dir = Path(args.model_dir)
    onnx_path = model_dir / "onnx" / f"{VARIANTS[args.variant]}.onnx"
    out_dir = Path(args.out_dir)
    record: dict = {"model": args.model, "variant": args.variant, "profile": args.profile, "onnx": str(onnx_path),
                    "threads": args.threads, "pinned_cpus": args.pin or None, "batch_size": args.batch_size,
                    "max_tokens": args.max_tokens, "ort_version": ort.__version__,
                    "revision": (model_dir / "REVISION").read_text(encoding="utf-8").strip()
                    if (model_dir / "REVISION").exists() else None}

    t0 = time.perf_counter()
    tokenizer = Tokenizer.from_file(str(model_dir / "tokenizer.json"))
    options = ort.SessionOptions()
    options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    options.intra_op_num_threads = args.threads
    options.inter_op_num_threads = 1
    session = ort.InferenceSession(str(onnx_path), options, providers=["CPUExecutionProvider"])
    record["load_s"] = time.perf_counter() - t0
    record["mem_after_load_mb"] = memory_mb()

    inputs = {i.name: i for i in session.get_inputs()}
    outputs = [o.name for o in session.get_outputs()]
    record["onnx_inputs"] = {n: [str(i.type), [str(d) for d in i.shape]] for n, i in inputs.items()}
    record["onnx_outputs"] = outputs
    # EmbeddingGemma 2's text graph also takes the media encoders' outputs (image/video/audio_features, shape
    # [num_tokens, 512]); a text-only input feeds them empty (0 tokens), as transformers.js does for text.
    media = {n: np.zeros((0, int(i.shape[1])), dtype=np.float32) for n, i in inputs.items()
             if n.endswith("_features") and i.type == "tensor(float)" and len(i.shape) == 2}
    record["empty_media_inputs"] = sorted(media)
    unknown = set(inputs) - {"input_ids", "attention_mask"} - set(media)
    if unknown or "input_ids" not in inputs:
        raise SystemExit(f"unexpected ONNX inputs {sorted(inputs)}: only input_ids/attention_mask are fed")
    if "sentence_embedding" not in outputs:
        raise SystemExit(f"no sentence_embedding output in {outputs}: pooling/projection would have to be rebuilt")
    int_type = np.int64 if "int64" in inputs["input_ids"].type else np.int32

    def encode(texts: list[str]) -> np.ndarray:
        encs = tokenizer.encode_batch(texts)
        ids = [e.ids[: args.max_tokens] for e in encs]
        width = max(len(x) for x in ids)
        input_ids = np.zeros((len(ids), width), dtype=int_type)
        mask = np.zeros((len(ids), width), dtype=int_type)
        for row, x in enumerate(ids):
            input_ids[row, : len(x)] = x
            mask[row, : len(x)] = 1
        feed = {"input_ids": input_ids, **media}
        if "attention_mask" in inputs:
            feed["attention_mask"] = mask
        (vectors,) = session.run(["sentence_embedding"], feed)
        return np.asarray(vectors, dtype=np.float32)

    def encode_all(texts: list[str]) -> tuple[np.ndarray, float]:
        lengths = [len(e.ids) for e in tokenizer.encode_batch(texts)]
        order = sorted(range(len(texts)), key=lengths.__getitem__)  # length-sorted batches: little padding
        result = np.zeros((len(texts), 0), dtype=np.float32)
        parts: dict[int, np.ndarray] = {}
        start = time.perf_counter()
        for b in range(0, len(order), args.batch_size):
            idx = order[b: b + args.batch_size]
            for i, v in zip(idx, encode([texts[i] for i in idx])):
                parts[i] = v
        elapsed = time.perf_counter() - start
        result = np.stack([parts[i] for i in range(len(texts))])
        return result, elapsed

    chunks = read_jsonl(CHUNKS)
    questions = [q for q in read_jsonl(QUESTIONS)]
    doc_texts = [DOC_PREFIX + c["embed_text"] for c in chunks]
    if args.doc_subset:
        step = len(doc_texts) / args.doc_subset
        doc_index = [int(i * step) for i in range(args.doc_subset)]
    else:
        doc_index = list(range(len(doc_texts)))
    doc_texts = [doc_texts[i] for i in doc_index]

    token_counts = [len(e.ids) for e in tokenizer.encode_batch(doc_texts)]
    record["doc_tokens"] = {"n": len(token_counts), "median": statistics.median(token_counts),
                            "max": max(token_counts), "truncated": sum(t > args.max_tokens for t in token_counts),
                            "total": sum(token_counts)}

    encode(doc_texts[:2])  # warm-up: first run allocates and finalizes kernels
    doc_vectors, doc_seconds = encode_all(doc_texts)
    record["index"] = {"docs": len(doc_texts), "seconds": doc_seconds, "docs_per_s": len(doc_texts) / doc_seconds,
                       "tokens_per_s": sum(min(t, args.max_tokens) for t in token_counts) / doc_seconds}

    query_texts = [QUERY_PREFIX + q["question"] for q in questions]
    query_vectors, _ = encode_all(query_texts)
    latencies = []
    for _ in range(args.latency_repeats):
        for text in query_texts:
            start = time.perf_counter()
            encode([text])
            latencies.append((time.perf_counter() - start) * 1000)
    latencies.sort()
    record["query_latency_ms"] = {"n": len(latencies), "median": statistics.median(latencies),
                                  "p90": latencies[int(0.9 * (len(latencies) - 1))], "max": latencies[-1]}

    norms = np.linalg.norm(np.concatenate([doc_vectors, query_vectors]), axis=1)
    record["vector_health"] = {"dim": int(doc_vectors.shape[1]), "nan_or_inf": int((~np.isfinite(norms)).sum()),
                               "near_zero_norm": int((norms < 1e-6).sum()),
                               "norm_min": float(np.nanmin(norms)), "norm_max": float(np.nanmax(norms))}
    record["mem_start_mb"] = mem_start
    record["mem_end_mb"] = memory_mb()

    stem = f"{args.model}-{args.variant}-{args.profile}"
    np.save(out_dir / f"{stem}.docs.npy", doc_vectors)
    np.save(out_dir / f"{stem}.queries.npy", query_vectors)
    record["doc_index"] = doc_index if args.doc_subset else None
    (out_dir / f"{stem}.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(f"{stem}: load {record['load_s']:.1f}s, index {record['index']['docs_per_s']:.1f} docs/s, "
          f"query p50 {record['query_latency_ms']['median']:.0f} ms, "
          f"peak RAM {record['mem_end_mb'].get('peak_working_set', float('nan')):.0f} MB")
    return 0


# ------------------------------------------------------------------------------------------------------ scoring

def load_cases() -> tuple[list[dict], dict]:
    from knowledge_assistant.application.evaluation.metrics.spans import spans_from_entry

    questions = read_jsonl(QUESTIONS)
    entries = json.loads(SPANS.read_text(encoding="utf-8"))["cases"]
    spans = {q["id"]: spans_from_entry(entries[q["id"]]) for q in questions if q["answerable"]}
    return questions, spans


def score_rankings(rankings: dict[str, list], questions: list[dict], spans: dict) -> dict:
    """Section/source hit@k, MRR@10 (section, lenient) on the answerable cases; overall and per language."""
    from knowledge_assistant.application.evaluation.metrics.retrieval import (reciprocal_rank, section_hit_at_k,
                                                                               source_hit_at_k)
    per_case = {}
    for q in questions:
        if not q["answerable"]:
            continue
        ranked = rankings[q["id"]]
        row = {"language": q["language"], "group": q["parallel_group_id"]}
        for k in KS:
            row[f"section@{k}"] = section_hit_at_k(ranked, spans[q["id"]], k)
            row[f"source@{k}"] = source_hit_at_k(ranked, spans[q["id"]], k)
        row["mrr@10"] = reciprocal_rank(ranked, spans[q["id"]], 10)
        per_case[q["id"]] = row

    def agg(rows: list[dict]) -> dict:
        out = {"n": len(rows)}
        for key in [f"{lvl}@{k}" for lvl in ("section", "source") for k in KS]:
            out[key] = sum(r[key] for r in rows)
        out["mrr@10"] = round(sum(r["mrr@10"] for r in rows) / len(rows), 4)
        return out

    rows = list(per_case.values())
    return {"overall": agg(rows), "en": agg([r for r in rows if r["language"] == "en"]),
            "vi": agg([r for r in rows if r["language"] == "vi"]), "per_case": per_case}


def rank_by_cosine(doc_vectors: np.ndarray, query_vectors: np.ndarray, chunks: list[dict],
                   questions: list[dict], top: int = 10) -> dict[str, list]:
    from knowledge_assistant.application.evaluation.metrics.retrieval import RankedChunk

    docs = doc_vectors / np.linalg.norm(doc_vectors, axis=1, keepdims=True)
    queries = query_vectors / np.linalg.norm(query_vectors, axis=1, keepdims=True)
    sims = queries @ docs.T
    result = {}
    for qi, q in enumerate(questions):
        order = np.argsort(-sims[qi], kind="stable")[:top]
        result[q["id"]] = [RankedChunk(chunks[i]["source_id"], chunks[i]["char_start"], chunks[i]["char_end"],
                                       chunks[i]["display_text"]) for i in order]
    return result


def gemini_vectors(chunks: list[dict], questions: list[dict]) -> tuple[np.ndarray, np.ndarray]:
    """Baseline vectors from the embedding cache, keyed as the app keys them (document=embed_text, query=question)."""
    con = sqlite3.connect(GEMINI_CACHE)

    def fetch(task: str, texts: list[str]) -> np.ndarray:
        rows = []
        for text in texts:
            key = hashlib.sha256(f"{GEMINI_MODEL_ID}|{task}|{text}".encode("utf-8")).hexdigest()
            hit = con.execute("SELECT dim, vector FROM embeddings WHERE key = ?", (key,)).fetchone()
            if hit is None:
                raise SystemExit(f"Gemini cache miss for a {task} text; refusing to call the API")
            rows.append(struct.unpack(f"<{hit[0]}f", hit[1]))
        return np.asarray(rows, dtype=np.float32)

    try:
        return fetch("document", [c["embed_text"] for c in chunks]), fetch("query", [q["question"] for q in questions])
    finally:
        con.close()


def check_recorded() -> dict:
    """Re-score the recorded production eval-A retrieval with this harness's metric calls; compare to its summary."""
    from knowledge_assistant.application.evaluation.metrics.retrieval import RankedChunk

    questions, spans = load_cases()
    chunk_index = {c["chunk_id"]: (c["source_id"], c["char_start"], c["char_end"]) for c in read_jsonl(CHUNKS)}
    rankings = {r["case_id"]: [RankedChunk.from_record(x, chunk_index) for x in r["retrieved"]]
                for r in read_jsonl(RECORDED_RUN)}
    mine = score_rankings(rankings, questions, spans)["overall"]
    saved = json.loads(RECORDED_SUMMARY.read_text(encoding="utf-8"))["breakdown"]["arm"]["A"]["retrieval"]
    compare = {}
    for k in (1, 3, 5):
        for lvl in ("section", "source"):
            compare[f"{lvl}@{k}"] = {"harness": mine[f"{lvl}@{k}"] / mine["n"], "summary": saved[f"{lvl}_hit@{k}"]["value"]}
    ok = all(math.isclose(v["harness"], v["summary"]) for v in compare.values())
    return {"run": RECORDED_RUN.parent.name, "reproduces_summary": ok, "values": compare}


def fidelity(vectors: np.ndarray, reference: np.ndarray, q: np.ndarray, q_ref: np.ndarray) -> dict:
    """Cosine to the same model's FP32 vectors, and how much of each query's FP32 top-5 the variant keeps."""
    def unit(x):
        return x / np.linalg.norm(x, axis=1, keepdims=True)
    cos = np.sum(unit(vectors) * unit(reference), axis=1)
    top = lambda d, qq: np.argsort(-(unit(qq) @ unit(d).T), axis=1)[:, :5]
    a, b = top(vectors, q), top(reference, q_ref)
    overlap = np.mean([len(set(x) & set(y)) / 5 for x, y in zip(a, b)])
    return {"doc_cos_mean": float(np.mean(cos)), "doc_cos_min": float(np.min(cos)), "top5_overlap": float(overlap)}


def paired(per_case: dict, base: dict, key: str) -> dict:
    """Cases this model hits and the baseline misses (wins), and the reverse (losses)."""
    wins = sorted(c for c in per_case if per_case[c][key] and not base[c][key])
    losses = sorted(c for c in per_case if base[c][key] and not per_case[c][key])
    return {"wins": wins, "losses": losses}


# ------------------------------------------------------------------------------------------------ orchestrator

def summarize(out_dir: Path, records: list[dict], scores: dict, fid: dict, baseline: dict, recorded: dict,
              machine: dict) -> str:
    lines = ["# Embedding benchmark", "", f"Run folder: `{out_dir.relative_to(REPO_ROOT).as_posix()}`  ",
             f"Machine: {machine['cpu']}, {machine['logical_cpus']} logical CPUs, {machine['ram_gb']:.1f} GB RAM; "
             f"low-end profile pinned to E-cores {machine['lowend_cpus']}  ",
             f"Harness self-check (recorded {recorded['run']} re-scored = saved summary): "
             f"**{recorded['reproduces_summary']}**", "",
             "## Retrieval quality (32 answerable eval questions; 16 EN, 16 VI; raw cosine top-k, arm A)", "",
             "| Model | Section@1 | @3 | @5 | @10 | Source@5 | MRR@10 | EN @1 / @5 | VI @1 / @5 | vs Gemini @5 (win/loss) |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for name, s in scores.items():
        o, en, vi = s["overall"], s["en"], s["vi"]
        vs = "" if name == "gemini" else (f"{len(s['vs_gemini@5']['wins'])}/{len(s['vs_gemini@5']['losses'])}")
        lines.append(f"| {name} | {o['section@1']}/{o['n']} | {o['section@3']} | {o['section@5']} | {o['section@10']} "
                     f"| {o['source@5']} | {o['mrr@10']:.3f} | {en['section@1']} / {en['section@5']} "
                     f"| {vi['section@1']} / {vi['section@5']} | {vs} |")
    lines += ["", "## Speed and memory", "",
              "| Model | Profile | Load s | Index docs/s | Index tokens/s | Query p50 ms | Query p90 ms "
              "| Peak RAM MB | Peak private MB | Truncated chunks |", "|---|---|---|---|---|---|---|---|---|---|"]
    for r in records:
        m = r["mem_end_mb"]
        lines.append(f"| {r['model']}-{r['variant']} | {r['profile']} | {r['load_s']:.1f} | "
                     f"{r['index']['docs_per_s']:.1f} | {r['index']['tokens_per_s']:.0f} | "
                     f"{r['query_latency_ms']['median']:.0f} | {r['query_latency_ms']['p90']:.0f} | "
                     f"{m.get('peak_working_set', float('nan')):.0f} | {m.get('peak_private', float('nan')):.0f} | "
                     f"{r['doc_tokens']['truncated']}/{r['doc_tokens']['n']} |")
    if fid:
        lines += ["", "## Precision fidelity (against the same model's FP32)", "",
                  "| Model | Doc cosine mean | Doc cosine min | Query top-5 overlap |", "|---|---|---|---|"]
        for name, f in fid.items():
            lines.append(f"| {name} | {f['doc_cos_mean']:.4f} | {f['doc_cos_min']:.4f} | {f['top5_overlap']:.2f} |")
    bad = [f"{r['model']}-{r['variant']}-{r['profile']}" for r in records
           if r["vector_health"]["nan_or_inf"] or r["vector_health"]["near_zero_norm"]]
    lines += ["", f"Vectors with NaN/Inf or zero norm: {', '.join(bad) if bad else 'none'}", ""]
    return "\n".join(lines)


def machine_info(lowend_cpus: list[int]) -> dict:
    ram = 0.0
    if os.name == "nt":
        class _MemStatus(ctypes.Structure):
            _fields_ = [("dwLength", wintypes.DWORD), ("dwMemoryLoad", wintypes.DWORD),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("rest", ctypes.c_ulonglong * 6)]
        status = _MemStatus()
        status.dwLength = ctypes.sizeof(status)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
        ram = status.ullTotalPhys / 1024 ** 3
    cpu = platform.processor()
    try:
        cpu = subprocess.run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"],
                             capture_output=True, text=True, timeout=30).stdout.strip() or cpu
    except OSError:
        pass
    return {"cpu": cpu, "logical_cpus": os.cpu_count(), "ram_gb": ram, "lowend_cpus": lowend_cpus,
            "python": sys.version.split()[0]}


def orchestrate(args: argparse.Namespace) -> int:
    recorded = check_recorded()
    print(f"harness self-check: reproduces recorded summary = {recorded['reproduces_summary']}")
    if args.check_recorded:
        print(json.dumps(recorded, indent=1))
        return 0 if recorded["reproduces_summary"] else 1
    if not args.models_dir:
        raise SystemExit("--models-dir is required unless --check-recorded")

    cores = efficiency_cores() if os.name == "nt" else {"e": [], "p": []}
    lowend_cpus = (cores["e"] or list(range(os.cpu_count() or 4)))[: args.lowend_threads]
    out_dir = OUT_ROOT / datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True)
    machine = machine_info(lowend_cpus)

    records = []
    for model in args.models:
        for variant in args.variants:
            for profile in args.profiles:
                cmd = [args.worker_python or sys.executable, str(Path(__file__).resolve()), "--worker", "--model", model,
                       "--variant", variant, "--profile", profile, "--model-dir", str(Path(args.models_dir) / model),
                       "--out-dir", str(out_dir), "--batch-size", str(args.batch_size),
                       "--max-tokens", str(args.max_tokens), "--latency-repeats", str(args.latency_repeats)]
                if profile == "lowend":
                    cmd += ["--threads", str(args.lowend_threads), "--pin", ",".join(map(str, lowend_cpus)),
                            "--doc-subset", str(args.lowend_docs)]
                else:
                    cmd += ["--threads", "0"]
                print(f"--> {model} {variant} {profile}", flush=True)
                proc = subprocess.run(cmd)
                stem = out_dir / f"{model}-{variant}-{profile}.json"
                if proc.returncode != 0 or not stem.exists():
                    print(f"    FAILED (exit {proc.returncode}); continuing", flush=True)
                    (out_dir / f"{model}-{variant}-{profile}.failed").write_text(str(proc.returncode))
                    continue
                records.append(json.loads(stem.read_text(encoding="utf-8")))

    chunks, (questions, spans) = read_jsonl(CHUNKS), load_cases()
    g_docs, g_queries = gemini_vectors(chunks, questions)
    scores = {"gemini": score_rankings(rank_by_cosine(g_docs, g_queries, chunks, questions), questions, spans)}
    fid = {}
    vectors = {}
    for r in records:
        if r["profile"] != "full":
            continue
        stem = f"{r['model']}-{r['variant']}-full"
        d, q = np.load(out_dir / f"{stem}.docs.npy"), np.load(out_dir / f"{stem}.queries.npy")
        vectors[(r["model"], r["variant"])] = (d, q)
        if not (np.isfinite(d).all() and np.isfinite(q).all()):
            continue
        scores[f"{r['model']}-{r['variant']}"] = score_rankings(rank_by_cosine(d, q, chunks, questions),
                                                                questions, spans)
    for (model, variant), (d, q) in vectors.items():
        ref = vectors.get((model, "fp32"))
        if ref is not None and variant != "fp32" and np.isfinite(d).all():
            fid[f"{model}-{variant}"] = fidelity(d, ref[0], q, ref[1])
    for name, s in scores.items():
        if name != "gemini":
            s["vs_gemini@5"] = paired(s["per_case"], scores["gemini"]["per_case"], "section@5")
            s["vs_gemini@1"] = paired(s["per_case"], scores["gemini"]["per_case"], "section@1")

    results = {"machine": machine, "settings": {k: v for k, v in vars(args).items()},
               "fixed": {"chunks": CHUNKS.relative_to(REPO_ROOT).as_posix(), "doc_prefix": DOC_PREFIX,
                         "query_prefix": QUERY_PREFIX, "scoring": "raw cosine top-10, no dedup, no gate"},
               "recorded_check": recorded, "runs": records, "scores": scores, "fidelity": fid}
    (out_dir / "results.json").write_text(json.dumps(results, indent=1, default=str), encoding="utf-8")
    summary = summarize(out_dir, records, scores, fid, scores["gemini"], recorded, machine)
    (out_dir / "summary.md").write_text(summary, encoding="utf-8")
    for f in out_dir.glob("*.npy"):  # vectors are large and reproducible; keep only the JSON/Markdown results
        if not args.keep_vectors:
            f.unlink()
    print(summary)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models-dir", help="folder holding gemma1/ and gemma2/ (download_embedding_models.py)")
    parser.add_argument("--models", nargs="+", choices=MODELS, default=list(MODELS))
    parser.add_argument("--variants", nargs="+", choices=list(VARIANTS), default=list(VARIANTS))
    parser.add_argument("--profiles", nargs="+", choices=["full", "lowend"], default=["full", "lowend"])
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-tokens", type=int, default=2048, help="same limit for every model (v1 context)")
    parser.add_argument("--latency-repeats", type=int, default=3)
    parser.add_argument("--lowend-threads", type=int, default=4)
    parser.add_argument("--lowend-docs", type=int, default=200, help="chunks encoded in the low-end speed run")
    parser.add_argument("--keep-vectors", action="store_true")
    parser.add_argument("--worker-python", help="interpreter for the model runs (needs onnxruntime, tokenizers, "
                        "numpy), e.g. a separate venv with a newer onnxruntime; scoring stays in this interpreter")
    parser.add_argument("--check-recorded", action="store_true", help="only run the harness self-check")
    # worker-only
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--model", help=argparse.SUPPRESS)
    parser.add_argument("--variant", help=argparse.SUPPRESS)
    parser.add_argument("--profile", help=argparse.SUPPRESS)
    parser.add_argument("--model-dir", help=argparse.SUPPRESS)
    parser.add_argument("--out-dir", help=argparse.SUPPRESS)
    parser.add_argument("--threads", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument("--pin", help=argparse.SUPPRESS)
    parser.add_argument("--doc-subset", type=int, default=0, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    return worker(args) if args.worker else orchestrate(args)


if __name__ == "__main__":
    sys.exit(main())
