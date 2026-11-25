"""Reranker benchmark, retrieval only (no LLM; plan §7.1 step 4b, ADR-0009). Measures; changes no default.

Three steps, each writing into one output folder (default data/experiments/rerank-bench/<stamp>/, git-ignored):

1. ``candidates``: for every question set and embedder, the production retriever (``composition.create_retriever``,
   RERANK_PROVIDER=none) returns its best 20 unique passages (TOP_K=20) in the embedder's best mode, Arm A. The
   query embeddings come from the on-disk cache; a Gemini query that is not cached is never sent: that set is
   skipped and reported TBD. The dense top-1 cosine (the current gate input) is kept per case.
2. ``run``: each (reranker, variant, profile) runs in its own subprocess, so peak memory is its own. The worker
   reranks every case's candidates with the production code (``retrieve.rerank_chunks`` over
   ``OnnxCrossEncoderReranker``) and records the new order, the scores and the time of each ``rerank`` call.
   Profiles as in the embedding benchmark: ``full`` (all cores, every case: the quality numbers) and ``lowend``
   (pinned to 4 efficiency cores, 4 intra-op threads, the first ``--lowend-cases`` cases of the v2 corpus-2 eval set:
   latency and RAM only; indicative, it cannot emulate the target's instruction set or memory bandwidth).
3. ``report``: the top 5 of each order become records in the evaluation schema and are scored by
   ``scoring.score_record`` (evidence_hit@1/@5, section MRR@5); paired exact McNemar against ``none`` (the
   production retriever, TOP_K=5, recorded with the candidates). Gate table: reranker top-1 on dev v1 + v2, Arm A, rule of
   retrieval-spec.md (lowest answerable - 0.05), on the sigmoid scale.

    python scripts/benchmark/reranker_bench.py candidates --out DIR
    python scripts/benchmark/reranker_bench.py run --out DIR --models-root E:/models/rerankers
    python scripts/benchmark/reranker_bench.py report --out DIR > report.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

QUESTIONS = REPO_ROOT / "data/evaluation/questions"
OUT_ROOT = REPO_ROOT / "data/experiments/rerank-bench"
CANDIDATES = 20
TOP_K = 5
ARM = "A"
# (question set, corpus, split, question file). v2 has a corpus-1 part (category E/F) and a corpus-2 part.
SETS = [("v1", "corpus1", "eval", "eval-v1.jsonl"), ("v1", "corpus1", "dev", "dev-v1.jsonl"),
        ("v2", "corpus1", "eval", "eval-v2.jsonl"), ("v2", "corpus2", "eval", "eval-v2.jsonl"),
        ("v2", "corpus2", "dev", "dev-v2.jsonl"), ("v2", "corpus1", "dev", "dev-v2.jsonl")]
# Best current mode per embedder (docs/reports/2026-11-25-corpus2-retrieval-eval.md): local hybrid A, Gemini dense A.
EMBEDDERS = {"local": ("embeddinggemma", "hybrid"), "gemini": ("gemini", "dense")}
RERANKERS = {  # name -> folder under --models-root
    "mmarco": "mmarco-mminilmv2-l12",
    "gte": "gte-multilingual-reranker-base",
    "bge": "bge-reranker-v2-m3",
}
VARIANTS = ("int8", "fp32")
CATEGORIES = ("A_vi_on_vi", "B_en_on_en", "C_vi_on_en", "D_vi_on_mixed", "E_identifier_c1")
MIN_TEST_N = 10
GATE_MARGIN = 0.05
BUDGET_MB, BUDGET_MS = 512, 1000


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def set_name(qset: str, corpus: str, split: str) -> str:
    return f"{qset}-{corpus}-{split}"


def cases_of(qset: str, corpus: str, split: str, file: str) -> list[dict]:
    return [c for c in read_jsonl(QUESTIONS / file) if c.get("corpus", "corpus1") == corpus and c["split"] == split]


# ------------------------------------------------------------------------------------------------- 1. candidates

def candidates(args: argparse.Namespace) -> int:
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv())
    from knowledge_assistant.composition import create_retriever, open_embedder, open_vector_store
    from knowledge_assistant.core.interfaces.embedding import EmbeddingTask
    from scripts.evaluation.run_eval import verify_against_tag

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    files = {name: (QUESTIONS / name).read_bytes() for name in ("eval-v2.jsonl", "dev-v2.jsonl")}
    verify_against_tag(REPO_ROOT, "eval-freeze-v2.1", files)  # raises unless the v2 files equal the frozen ones
    meta = {"git_commit": subprocess.run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"], capture_output=True,
                                         text=True).stdout.strip(),
            "question_files": {n: hashlib.sha256((QUESTIONS / n).read_bytes()).hexdigest()
                               for n in ("eval-v1.jsonl", "dev-v1.jsonl", "eval-v2.jsonl", "dev-v2.jsonl")},
            "git_dirty": bool(subprocess.run(["git", "-C", str(REPO_ROOT), "status", "--porcelain", "--untracked-files=no"],
                                             capture_output=True, text=True).stdout.strip()),
            "candidates": CANDIDATES, "arm": ARM, "skipped": {}, "sets": {}}
    for embedder_name in args.embedders:
        provider, mode = EMBEDDERS[embedder_name]
        os.environ.update(EMBEDDING_PROVIDER=provider, RETRIEVAL_MODE=mode, TOP_K=str(CANDIDATES),
                          RERANK_PROVIDER="none")
        rows = []
        for qset, corpus, split, file in SETS:
            cases = cases_of(qset, corpus, split, file)
            if not cases:
                continue
            name = set_name(qset, corpus, split)
            os.environ["CORPUS"] = corpus
            with open_embedder(max_attempts=1) as embedder:
                missing = embedder.missing([c["question"] for c in cases], EmbeddingTask.QUERY)
                if provider == "gemini" and missing:
                    meta["skipped"][f"{embedder_name}/{name}"] = f"{len(missing)} uncached Gemini queries (quota): TBD"
                    print(f"skip {embedder_name} {name}: {len(missing)} uncached Gemini queries", flush=True)
                    continue
                try:
                    store = open_vector_store(ARM)
                    retriever = create_retriever(ARM, embedder, store)
                    os.environ["TOP_K"] = str(TOP_K)
                    production = create_retriever(ARM, embedder, store)  # the `none` baseline, as recorded runs
                    os.environ["TOP_K"] = "10"
                    ten = create_retriever(ARM, embedder, store)  # the 10-candidate list (own fetch depth)
                    os.environ["TOP_K"] = str(CANDIDATES)
                except Exception as error:  # a missing index for this corpus/embedder is reported, not fatal
                    meta["skipped"][f"{embedder_name}/{name}"] = f"{type(error).__name__}: {error}"
                    print(f"skip {embedder_name} {name}: {error}", flush=True)
                    continue
                for case in cases:
                    result = retriever.retrieve(case["question"])
                    base = production.retrieve(case["question"])
                    short = ten.retrieve(case["question"])
                    rows.append({"embedder": embedder_name, "mode": mode, "set": name, "case_id": case["id"],
                                 "gate_score": result.gate_score,
                                 "chunk_ids": [h.chunk.chunk_id for h in result.chunks],
                                 "scores": [h.score for h in result.chunks],
                                 "duplicate_chunk_ids": [list(h.duplicate_chunk_ids) for h in result.chunks],
                                 "base_chunk_ids": [h.chunk.chunk_id for h in base.chunks],
                                 "base_scores": [h.score for h in base.chunks],
                                 "base_duplicate_chunk_ids": [list(h.duplicate_chunk_ids) for h in base.chunks],
                                 "c10_chunk_ids": [h.chunk.chunk_id for h in short.chunks],
                                 "c10_scores": [h.score for h in short.chunks],
                                 "c10_duplicate_chunk_ids": [list(h.duplicate_chunk_ids) for h in short.chunks]})
                meta["sets"][f"{embedder_name}/{name}"] = len(cases)
                print(f"{embedder_name} {mode} {name}: {len(cases)} cases", flush=True)
        write_jsonl(out / f"candidates-{embedder_name}.jsonl", rows)
    (out / "candidates-meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    return 0


def load_candidates(out: Path) -> list[dict]:
    rows = []
    for path in sorted(out.glob("candidates-*.jsonl")):
        rows += read_jsonl(path)
    return rows


def chunk_lookup(corpus: str):
    from knowledge_assistant.application.ingestion.build_chunks import load_chunks
    from knowledge_assistant.config import get_chunks_dir

    return {c.chunk_id: c for c in load_chunks(get_chunks_dir(corpus) / f"arm-{ARM.lower()}.jsonl")}


def corpus_of(set_label: str) -> str:
    return set_label.split("-")[1]


# ------------------------------------------------------------------------------------------------------ 2. worker

def stem_of(name: str, variant: str, tokens: int, count: int, batch: int, profile: str) -> str:
    return f"rerank-{name}-{variant}-p{tokens}-c{count}-b{batch}-{profile}"


def label_of(worker_record: dict) -> str:
    """Quality label: batch size and profile do not change the order."""
    w = worker_record
    return f"{w['reranker']}-{w['variant']}-p{w['max_passage_tokens']}-c{w['candidates']}"


def worker(args: argparse.Namespace) -> int:
    from scripts.benchmark.embedding_bench import memory_mb, pin_to

    if args.pin:
        pin_to([int(i) for i in args.pin.split(",")])
    from knowledge_assistant.application.retrieval.retrieve import rerank_chunks
    from knowledge_assistant.config import RerankSettings
    from knowledge_assistant.core.models import RetrievedChunk
    from knowledge_assistant.infrastructure.rerank.onnx_cross_encoder import OnnxCrossEncoderReranker, onnx_file

    out = Path(args.out)
    rows = load_candidates(out)
    if args.profile == "lowend":
        lowend = sorted({r["case_id"] for r in rows if r["set"] == "v2-corpus2-eval"})[: args.lowend_cases]
        rows = [r for r in rows if r["set"] == "v2-corpus2-eval" and r["embedder"] == "local" and r["case_id"] in lowend]
    lookups = {corpus: chunk_lookup(corpus) for corpus in {corpus_of(r["set"]) for r in rows}}
    questions = {}
    for _, _, _, file in SETS:
        questions.update({c["id"]: c["question"] for c in read_jsonl(QUESTIONS / file)})
    settings = RerankSettings(model_dir=Path(args.model_dir), variant=args.variant, candidates=args.candidates,
                              max_passage_tokens=args.max_passage_tokens, batch_size=args.batch_size,
                              threads=args.threads)
    reranker = OnnxCrossEncoderReranker(settings)
    mem_before = memory_mb()
    started = time.perf_counter()
    reranker.score("warm-up", ["load"])  # loads the model; its time is the load time, not a question's
    load_s = time.perf_counter() - started
    mem_loaded = memory_mb()
    results = []
    for row in rows:
        lookup = lookups[corpus_of(row["set"])]
        prefix = "" if args.candidates == CANDIDATES else "c10_"
        hits = [RetrievedChunk(chunk=lookup[cid], rank=i, score=s, duplicate_chunk_ids=tuple(d))
                for i, (cid, s, d) in enumerate(zip(row[f"{prefix}chunk_ids"], row[f"{prefix}scores"],
                                                    row[f"{prefix}duplicate_chunk_ids"]), 1)]
        t0 = time.perf_counter()
        ranked = rerank_chunks(reranker, questions[row["case_id"]], hits, len(hits))
        ms = (time.perf_counter() - t0) * 1000.0
        results.append({"embedder": row["embedder"], "set": row["set"], "case_id": row["case_id"], "ms": ms,
                        "chunk_ids": [h.chunk.chunk_id for h in ranked], "scores": [h.score for h in ranked]})
    record = {"reranker": args.name, "variant": args.variant, "profile": args.profile, "model_id": reranker.model_id,
              "onnx_file": onnx_file(Path(args.model_dir), args.variant).name,
              "onnx_mb": onnx_file(Path(args.model_dir), args.variant).stat().st_size / 2 ** 20
              + sum(p.stat().st_size for p in (Path(args.model_dir) / "onnx").glob("*.onnx_data")) / 2 ** 20
              * (args.variant == "fp32"),
              "threads": args.threads, "pinned_cpus": args.pin or None, "cases": len(results), "load_s": load_s,
              "mem_before_mb": mem_before, "mem_loaded_mb": mem_loaded, "mem_end_mb": memory_mb(),
              "max_passage_tokens": args.max_passage_tokens, "positions": reranker.positions,
              "candidates": args.candidates, "batch_size": args.batch_size, "results": results}
    stem = stem_of(args.name, args.variant, args.max_passage_tokens, args.candidates, args.batch_size, args.profile)
    (out / f"{stem}.json").write_text(json.dumps(record), encoding="utf-8")
    lat = [r["ms"] for r in results]
    print(f"    {stem}: {len(results)} cases, load {load_s:.1f}s, median {statistics.median(lat):.0f} ms, "
          f"peak RAM {record['mem_end_mb'].get('peak_working_set', float('nan')):.0f} MB", flush=True)
    return 0


def run(args: argparse.Namespace) -> int:
    from scripts.benchmark.embedding_bench import efficiency_cores, machine_info

    out = Path(args.out)
    cores = efficiency_cores() if os.name == "nt" else {"e": [], "p": []}
    lowend_cpus = (cores["e"] or list(range(os.cpu_count() or 4)))[: args.lowend_threads]
    (out / "machine.json").write_text(json.dumps(machine_info(lowend_cpus), indent=1), encoding="utf-8")
    grid = [(n, v, p, c, b, profile) for profile in args.profiles for n in args.rerankers for v in args.variants
            for p in args.passage_tokens for c in args.candidates for b in args.batch_sizes]
    for name, variant, tokens, count, batch, profile in grid:
        stem = out / f"{stem_of(name, variant, tokens, count, batch, profile)}.json"
        if stem.exists():
            continue
        cmd = [sys.executable, str(Path(__file__).resolve()), "worker", "--out", str(out), "--name", name,
               "--variant", variant, "--profile", profile, "--max-passage-tokens", str(tokens),
               "--candidates", str(count), "--batch-size", str(batch),
               "--model-dir", str(Path(args.models_root) / RERANKERS[name])]
        if profile == "lowend":
            cmd += ["--threads", str(args.lowend_threads), "--pin", ",".join(map(str, lowend_cpus)),
                    "--lowend-cases", str(args.lowend_cases)]
        else:
            cmd += ["--threads", "0"]
        print(f"--> {stem.stem}", flush=True)
        proc = subprocess.run(cmd)
        if proc.returncode != 0:
            print(f"    FAILED (exit {proc.returncode}); continuing", flush=True)
    return 0


# ------------------------------------------------------------------------------------------------------ 3. report

def scored_rows(out: Path) -> tuple[list[dict], list[dict]]:
    """One row per (embedder, set, reranker config, case) with the scores of its top 5; plus the worker records."""
    from knowledge_assistant.application.evaluation.metrics.retrieval import chunk_index
    from knowledge_assistant.application.evaluation.records import assemble, chunk_entry
    from knowledge_assistant.application.evaluation.scoring import score_record
    from knowledge_assistant.config import get_chunks_dir
    from knowledge_assistant.core.models import RetrievedChunk
    from scripts.evaluation.report_corpus2 import load_spans

    cases = {}
    for _, _, _, file in SETS:
        cases.update({c["id"]: c for c in read_jsonl(QUESTIONS / file)})
    spans = load_spans()
    lookups, indexes = {}, {}
    for corpus in ("corpus1", "corpus2"):
        lookups[corpus] = chunk_lookup(corpus)
        indexes[corpus] = chunk_index(read_jsonl(get_chunks_dir(corpus) / f"arm-{ARM.lower()}.jsonl"))
    cands = load_candidates(out)
    workers = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(out.glob("rerank-*-full.json"))]
    # `none` = the production retriever (TOP_K=5): in hybrid mode its top 5 can differ from the top 5 of the 20
    # candidates, because RRF fuses longer lists when more is fetched.
    orders = [("none", {(r["embedder"], r["set"], r["case_id"]): (r["base_chunk_ids"], r["base_scores"])
                        for r in cands})]
    for w in workers:
        orders.append((label_of(w),
                       {(r["embedder"], r["set"], r["case_id"]): (r["chunk_ids"], r["scores"]) for r in w["results"]}))
    gate = {(r["embedder"], r["set"], r["case_id"]): r["gate_score"] for r in cands}
    dups = {(r["embedder"], r["set"], r["case_id"], cid): d for r in cands
            for cid, d in [*zip(r["chunk_ids"], r["duplicate_chunk_ids"]),
                           *zip(r["base_chunk_ids"], r["base_duplicate_chunk_ids"]),
                           *zip(r["c10_chunk_ids"], r["c10_duplicate_chunk_ids"])]}
    rows = []
    for config, order in orders:
        for key, (chunk_ids, scores) in order.items():
            embedder, set_label, case_id = key
            corpus, case = corpus_of(set_label), cases[case_id]
            hits = [RetrievedChunk(chunk=lookups[corpus][cid], rank=i, score=s,
                                   duplicate_chunk_ids=tuple(dups[(embedder, set_label, case_id, cid)]))
                    for i, (cid, s) in enumerate(zip(chunk_ids[:TOP_K], scores[:TOP_K]), 1)]
            record = assemble("rerank-bench", case, ARM, "retrieval", case["split"], "ok", "", "",
                              {"retrieved": [chunk_entry(h) for h in hits], "top1_score": gate[key]})
            scored = case["answerable"] and case_id in spans  # dev v1 has no spans: it only feeds the gate table
            scores_row = (score_record(record, spans, indexes[corpus], {}, "none")["retrieval"] or {}) if scored else {}
            rows.append({"embedder": embedder, "set": set_label, "config": config, "case_id": case_id,
                         "qset": set_label.split("-")[0], "corpus": corpus, "split": case["split"],
                         "answerable": case["answerable"], "category": case.get("category", "v1"),
                         "language": case["language"],
                         "typing": case.get("typing", "en" if case["language"] == "en" else "diacritics"),
                         "e1": scores_row.get("evidence_hit@1"), "e5": scores_row.get("evidence_hit@5"),
                         "mrr": scores_row.get("mrr"), "rerank_top1": scores[0] if config != "none" else None,
                         "dense_top1": gate[key]})
    return rows, [json.loads(p.read_text(encoding="utf-8")) for p in sorted(out.glob("rerank-*.json"))]


def _rate(values: list) -> str:
    values = [v for v in values if v is not None]
    return f"{sum(values)}/{len(values)} ({sum(values) / len(values):.3f})" if values else "–"


def _mean(values: list) -> str:
    values = [v for v in values if v is not None]
    return f"{sum(values) / len(values):.3f}" if values else "–"


def _configs(rows: list[dict]) -> list[str]:
    def key(label: str):
        name, variant, tokens, count = label.split("-")
        return list(RERANKERS).index(name), VARIANTS.index(variant), int(tokens[1:]), int(count[1:])

    names = sorted({r["config"] for r in rows} - {"none"}, key=key)
    return ["none"] + names


def report(args: argparse.Namespace) -> int:
    from knowledge_assistant.application.evaluation.stats import mcnemar_exact

    out = Path(args.out)
    rows, workers = scored_rows(out)
    meta = json.loads((out / "candidates-meta.json").read_text(encoding="utf-8"))
    machine = json.loads((out / "machine.json").read_text(encoding="utf-8"))
    print(f"Candidates: commit {meta['git_commit'][:7]}, top {meta['candidates']} unique passages, Arm {ARM}. "
          f"Skipped: {meta['skipped'] or 'none'}. Machine: {machine['cpu']}, low-end CPUs {machine['lowend_cpus']}.")
    configs = _configs(rows)
    answerable = [r for r in rows if r["answerable"]]
    pools = [("v1 eval (corpus 1)", lambda r: r["set"] == "v1-corpus1-eval"),
             ("v2 eval corpus 2 (A-D)", lambda r: r["set"] == "v2-corpus2-eval"),
             ("v2 eval corpus 1 (E)", lambda r: r["set"] == "v2-corpus1-eval")]
    for embedder in ("local", "gemini"):
        mine = [r for r in answerable if r["embedder"] == embedder]
        if not mine:
            continue
        mode = EMBEDDERS[embedder][1]
        print(f"\n### {embedder} ({mode}, Arm {ARM}): answerable eval, top 5 after reranking {CANDIDATES} candidates\n")
        print("| pool | reranker | n | evidence_hit@1 | evidence_hit@5 | MRR@5 (section) | vs none @5: b / c / p "
              "| vs none @1: b / c / p |")
        print("|---|---|---:|---:|---:|---:|---|---|")
        for label, keep in pools:
            pool = [r for r in mine if keep(r)]
            if not pool:
                continue
            base = {r["case_id"]: r for r in pool if r["config"] == "none"}
            for config in configs:
                sub = [r for r in pool if r["config"] == config]
                if not sub:
                    continue
                tests = []
                for metric in ("e5", "e1"):
                    if config == "none":
                        tests.append("–")
                        continue
                    ids = sorted(r["case_id"] for r in sub)
                    mine_m = {r["case_id"]: r[metric] for r in sub}
                    res = mcnemar_exact([base[i][metric] for i in ids], [mine_m[i] for i in ids])
                    tests.append(f"{res.b} / {res.c} / {res.p_value:.3f}")
                print(f"| {label} | {config} | {len(sub)} | {_rate([r['e1'] for r in sub])} | "
                      f"{_rate([r['e5'] for r in sub])} | {_mean([r['mrr'] for r in sub])} | {tests[0]} | {tests[1]} |")
        v2 = [r for r in mine if r["qset"] == "v2" and r["split"] == "eval"]
        if v2:
            for field, values, title in (("category", CATEGORIES, "per category"),
                                         ("language", ("vi", "en"), "per question language"),
                                         ("typing", ("diacritics", "no_diacritics", "en"), "per typing")):
                sizes = {v: len({r["case_id"] for r in v2 if r[field] == v}) for v in values}
                print(f"\n{embedder}, v2 eval answerable {title}, evidence_hit@5 (n: "
                      + ", ".join(f"{v} {n}" for v, n in sizes.items()) + ")\n")
                print("| reranker | " + " | ".join(values) + " |")
                print("|---|" + "---:|" * len(values))
                for config in configs:
                    cells = [_rate([r["e5"] for r in v2 if r["config"] == config and r[field] == v]) for v in values]
                    print(f"| {config} | " + " | ".join(cells) + " |")
    cost(workers)
    gate_tables(rows, configs)
    return 0


def cost(workers: list[dict]) -> None:
    print(f"\n### Cost per reranker (budget: added RAM <= {BUDGET_MB} MB, added latency <= {BUDGET_MS} ms per question "
          "on the low-end profile)\n")
    print("| config | batch | ONNX MB | low-end cases | load s | median ms / question | p95 ms | max ms | "
          "RAM before load MB | peak RAM MB | added RAM MB | full-profile median ms | budget |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    full = {label_of(w): w for w in workers if w["profile"] == "full"}
    for w in sorted((w for w in workers if w["profile"] == "lowend"), key=lambda w: (label_of(w), w["batch_size"])):
        lat = sorted(r["ms"] for r in w["results"])
        p95 = lat[min(len(lat) - 1, round(0.95 * (len(lat) - 1)))]
        before = w["mem_before_mb"].get("working_set", float("nan"))
        peak = w["mem_end_mb"].get("peak_working_set", float("nan"))
        added, median = peak - before, statistics.median(lat)
        f = full.get(label_of(w))
        fmed = f"{statistics.median(r['ms'] for r in f['results']):.0f}" if f else "–"
        over = [x for x, bad in (("RAM", added > BUDGET_MB), ("latency", median > BUDGET_MS)) if bad]
        print(f"| {label_of(w)} | {w['batch_size']} | {w['onnx_mb']:.0f} | {w['cases']} | {w['load_s']:.1f} | "
              f"{median:.0f} | {p95:.0f} | {lat[-1]:.0f} | {before:.0f} | {peak:.0f} | {added:.0f} | {fmed} | "
              f"{'**over: ' + ', '.join(over) + '**' if over else 'within'} |")


def gate_tables(rows: list[dict], configs: list[str]) -> None:
    print("\n### Gate calibration: reranker top-1 (sigmoid) on dev v1 + v2, Arm A; rule of retrieval-spec.md "
          f"(lowest answerable - {GATE_MARGIN}). The {GATE_MARGIN} margin was set on the cosine scale; on the "
          "sigmoid scale it is **DECISION REQUIRED**.\n")
    dev = [r for r in rows if r["split"] == "dev"]
    for embedder in ("local", "gemini"):
        mine = [r for r in dev if r["embedder"] == embedder and r["config"] != "none"]
        if not mine:
            continue
        print(f"\n**{embedder}** ({EMBEDDERS[embedder][1]})\n")
        print("| reranker | pool | answerable n | unanswerable n | lowest answerable | highest unanswerable | "
              "rule value | overlap | eval unanswerable refused at rule value | eval answerable refused |")
        print("|---|---|---:|---:|---:|---:|---:|---|---|---|")
        for config in configs[1:]:
            sub = [r for r in mine if r["config"] == config]
            for label, pool in (("corpus1", [r for r in sub if r["corpus"] == "corpus1"]),
                                ("corpus2", [r for r in sub if r["corpus"] == "corpus2"]), ("pooled", sub)):
                ans = [r["rerank_top1"] for r in pool if r["answerable"]]
                una = [r["rerank_top1"] for r in pool if not r["answerable"]]
                if not ans:
                    continue
                low, high = min(ans), (max(una) if una else None)
                value = low - GATE_MARGIN
                overlap = "–" if high is None else ("**yes: DECISION REQUIRED**" if high >= low else "no")
                info = ""
                if label == "pooled":
                    ev = [r for r in rows if r["embedder"] == embedder and r["config"] == config and r["split"] == "eval"]
                    un = [r for r in ev if not r["answerable"]]
                    an = [r for r in ev if r["answerable"]]
                    info = (f"{sum(r['rerank_top1'] < value for r in un)}/{len(un)} | "
                            f"{sum(r['rerank_top1'] < value for r in an)}/{len(an)}")
                else:
                    info = "| "
                shown = f"{value:.4f}" if value > 0 else "no usable threshold (<= 0)"
                print(f"| {config} | {label} | {len(ans)} | {len(una)} | {low:.4f} | "
                      f"{'–' if high is None else f'{high:.4f}'} | {shown} | {overlap} | {info} |")
        print(f"\nPer case ({embedder}, dev):\n")
        print("| case | set | answerable | dense top-1 | " + " | ".join(configs[1:]) + " |")
        print("|---|---|---|---:|" + "---:|" * (len(configs) - 1))
        ids = sorted({(r["set"], r["case_id"]) for r in mine})
        for set_label, case_id in ids:
            per = {r["config"]: r for r in mine if r["case_id"] == case_id and r["set"] == set_label}
            first = next(iter(per.values()))
            cells = [f"{per[c]['rerank_top1']:.4f}" if c in per else "–" for c in configs[1:]]
            print(f"| {case_id} | {set_label} | {'yes' if first['answerable'] else 'no'} | {first['dense_top1']:.4f} | "
                  + " | ".join(cells) + " |")


# -------------------------------------------------------------------------------------------------------- main

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("candidates")
    p.add_argument("--out", default=str(OUT_ROOT / datetime.now().strftime("%Y%m%d-%H%M%S")))
    p.add_argument("--embedders", nargs="+", choices=list(EMBEDDERS), default=list(EMBEDDERS))
    p = sub.add_parser("run")
    p.add_argument("--out", required=True)
    p.add_argument("--models-root", required=True)
    p.add_argument("--rerankers", nargs="+", choices=list(RERANKERS), default=list(RERANKERS))
    p.add_argument("--variants", nargs="+", choices=VARIANTS, default=list(VARIANTS))
    p.add_argument("--profiles", nargs="+", choices=["full", "lowend"], default=["full", "lowend"])
    p.add_argument("--lowend-threads", type=int, default=4)
    p.add_argument("--lowend-cases", type=int, default=30)
    p.add_argument("--passage-tokens", nargs="+", type=int, default=[256])
    p.add_argument("--candidates", nargs="+", type=int, choices=[10, CANDIDATES], default=[CANDIDATES])
    p.add_argument("--batch-sizes", nargs="+", type=int, default=[CANDIDATES])
    p = sub.add_parser("worker")
    p.add_argument("--candidates", type=int, choices=[10, CANDIDATES], default=CANDIDATES)
    p.add_argument("--batch-size", type=int, default=CANDIDATES)
    for name in ("--out", "--name", "--variant", "--profile", "--model-dir"):
        p.add_argument(name, required=True)
    p.add_argument("--threads", type=int, default=0)
    p.add_argument("--pin", default="")
    p.add_argument("--lowend-cases", type=int, default=30)
    p.add_argument("--max-passage-tokens", type=int, default=256)
    p = sub.add_parser("report")
    p.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    return {"candidates": candidates, "run": run, "worker": worker, "report": report}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
