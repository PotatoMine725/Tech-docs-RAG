"""Retrieval-only report over benchmark v1 + v2 (corpus 1 + corpus 2, ADR-0008): Markdown tables to stdout. Offline.

    python scripts/evaluation/report_corpus2.py --runs-glob '20261125-*-retrieval-*'

Every number comes from the run folders under data/evaluation/results/ through the EVAL-003b scoring code
(`eval_report_data.score_run_pairs` -> `scoring.score_record`); nothing is typed in. Spans: expected-spans-v1.json
(v1 eval) and expected-spans-v2.json (v2 eval + dev). Chunk indexes come from each run's corpus and arm chunk file.
A run is one (question set, corpus, split, arm, embedder, mode); its id must follow
<date>-<v1|v2>-<corpus>-<split>-<A|B>-retrieval-<gemini|local>-<dense|sparse|hybrid>-<sha>.
Headline: evidence_hit@5 (owner, ADR-0008). An answerable case without an ok record (a sparse query that matched no
keyword) counts as a miss and is listed in the `errors` column. F (unanswerable) cases have no evidence: their cell is
how often the retrieval gate (dense top-1 < the provider threshold) refused them.
Paired test: exact McNemar on evidence_hit@5 over the same cases, for comparisons fixed in advance (hybrid vs dense,
sparse vs dense, local vs gemini, arm B vs arm A); raw two-sided p, no multiple-comparison correction. Subgroups
below MIN_TEST_N cases are not tested. Gate: dev v1 + v2, Arm A, dense top-1, rule of retrieval-spec.md.
"""
import argparse
import fnmatch
import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from knowledge_assistant.application.evaluation.metrics.retrieval import chunk_index  # noqa: E402
from knowledge_assistant.application.evaluation.metrics.spans import spans_from_entry  # noqa: E402
from knowledge_assistant.application.evaluation.stats import mcnemar_exact  # noqa: E402
from knowledge_assistant.config import GATE_THRESHOLDS, get_chunks_dir  # noqa: E402
from scripts.evaluation.eval_report_data import load_run, score_run_pairs  # noqa: E402

RESULTS = PROJECT_ROOT / "data" / "evaluation" / "results"
QUESTIONS = PROJECT_ROOT / "data" / "evaluation" / "questions"
METRIC = "evidence_hit@5"
MIN_TEST_N = 10
MODES = ("dense", "sparse", "hybrid")
PROVIDERS = ("gemini", "local")
CATEGORIES = ("A_vi_on_vi", "B_en_on_en", "C_vi_on_en", "D_vi_on_mixed", "E_identifier_c1", "F_unanswerable")
GATE_MARGIN = 0.05


def parse_id(run_id: str) -> dict:
    parts = run_id.split("-")
    qset, corpus, split, arm, _, provider, mode = parts[1:8]
    return {"qset": qset, "corpus": corpus, "split": split, "arm": arm, "provider": provider, "mode": mode}


def load_cases() -> dict[str, dict]:
    cases = {}
    for name in ("eval-v1", "dev-v1", "eval-v2", "dev-v2"):
        for line in (QUESTIONS / f"{name}.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                case = json.loads(line)
                case.setdefault("corpus", "corpus1")
                case.setdefault("category", "v1")
                case.setdefault("typing", "en" if case["language"] == "en" else "diacritics")
                cases[case["id"]] = case
    return cases


def load_spans() -> dict:
    spans = {}
    for name in ("expected-spans-v1.json", "expected-spans-v2.json"):
        data = json.loads((QUESTIONS / name).read_text(encoding="utf-8"))
        spans.update({cid: spans_from_entry(e) for cid, e in data["cases"].items() if e["answerable"]})
    return spans


def chunk_indexes() -> dict:
    indexes = {}
    for corpus in ("corpus1", "corpus2"):
        for arm in "AB":
            path = get_chunks_dir(corpus) / f"arm-{arm.lower()}.jsonl"
            with path.open(encoding="utf-8") as handle:
                indexes[(corpus, arm)] = chunk_index([json.loads(line) for line in handle if line.strip()])
    return indexes


def collect(run_ids: list[str]) -> list[dict]:
    """One row per (run, case): identity, case metadata, hit (evidence_hit@5 or None), section/source hits, gate."""
    cases, spans, indexes = load_cases(), load_spans(), chunk_indexes()
    rows = []
    for run_id in run_ids:
        meta = parse_id(run_id)
        run = load_run(run_id)
        config = run["manifest"]["config"]
        assert config.get("corpus", "corpus1") == meta["corpus"] and config["retrieval_mode"] == meta["mode"], run_id
        index = indexes[(meta["corpus"], meta["arm"])]
        for record, scored in score_run_pairs(run, spans, index):
            case = cases[record["case_id"]]
            retrieval = scored.get("retrieval") or {}
            ok = record["status"] == "ok"
            rows.append({**meta, "run_id": run_id, "case_id": record["case_id"], "ok": ok,
                         "answerable": record["answerable"], "category": case["category"],
                         "language": case["language"], "typing": case["typing"],
                         "threshold": config["threshold"],
                         "evidence": (retrieval.get(METRIC, 0) if ok else 0) if record["answerable"] else None,
                         "section": retrieval.get("section_hit@5") if ok else 0,
                         "source": retrieval.get("source_hit@5") if ok else 0,
                         "mrr": retrieval.get("mrr") if ok else 0,
                         "has_spans": bool(retrieval) or not ok,
                         "top1": record.get("top1_score") if ok else None,
                         "gate_fired": bool(record.get("gate_fired")) if ok else None})
    return rows


def config_key(row) -> tuple:
    return row["provider"], row["mode"], row["arm"]


def rate(values: list) -> str:
    values = [v for v in values if v is not None]
    return f"{sum(values)}/{len(values)} ({sum(values) / len(values):.3f})" if values else "–"


def headline(rows: list[dict], title: str) -> None:
    print(f"\n### {title}\n")
    print("| embedder | mode | arm | answerable n | errors | evidence_hit@5 | section_hit@5 | source_hit@5 | MRR@5 |")
    print("|---|---|---|---:|---:|---:|---:|---:|---:|")
    groups = defaultdict(list)
    for row in rows:
        groups[config_key(row)].append(row)
    for key in sorted(groups, key=lambda k: (PROVIDERS.index(k[0]), MODES.index(k[1]), k[2])):
        ans = [r for r in groups[key] if r["answerable"]]
        spanned = [r for r in ans if r["has_spans"]]
        mrr = [r["mrr"] for r in spanned if r["mrr"] is not None]
        mrr_cell = f"{sum(mrr) / len(mrr):.3f}" if mrr else "–"
        print(f"| {key[0]} | {key[1]} | {key[2]} | {len(ans)} | {sum(not r['ok'] for r in ans)} | "
              f"{rate([r['evidence'] for r in ans])} | {rate([r['section'] for r in spanned])} | "
              f"{rate([r['source'] for r in spanned])} | {mrr_cell} |")


def breakdown(rows: list[dict], field: str, values: tuple, title: str) -> None:
    print(f"\n### {title}\n")
    print("| embedder | mode | arm | " + " | ".join(values) + " |")
    print("|---|---|---|" + "---:|" * len(values))
    groups = defaultdict(list)
    for row in rows:
        groups[config_key(row)].append(row)
    sizes = {v: len({r["case_id"] for r in rows if r[field] == v}) for v in values}
    for key in sorted(groups, key=lambda k: (PROVIDERS.index(k[0]), MODES.index(k[1]), k[2])):
        cells = []
        for value in values:
            sub = [r for r in groups[key] if r[field] == value]
            if value == "F_unanswerable":
                fired = [int(r["gate_fired"]) for r in sub if r["gate_fired"] is not None]
                cells.append(f"gate {sum(fired)}/{len(fired)}" if fired else "–")
            else:
                cells.append(rate([r["evidence"] for r in sub if r["answerable"]]))
        print(f"| {key[0]} | {key[1]} | {key[2]} | " + " | ".join(cells) + " |")
    print("\nn (cases): " + ", ".join(f"{v} {n}" for v, n in sizes.items()))


def paired(rows: list[dict], title: str) -> None:
    by_config = defaultdict(dict)
    for row in rows:
        if row["answerable"]:
            by_config[config_key(row)][row["case_id"]] = row["evidence"]
    comparisons = []
    for arm in "AB":
        for provider in PROVIDERS:
            for mode in ("hybrid", "sparse"):
                comparisons.append(((provider, "dense", arm), (provider, mode, arm)))
        for mode in MODES:
            comparisons.append((("gemini", mode, arm), ("local", mode, arm)))
    for provider in PROVIDERS:
        for mode in MODES:
            comparisons.append(((provider, mode, "A"), (provider, mode, "B")))
    print(f"\n### {title}: exact McNemar on {METRIC} (b = only the first wins, c = only the second)\n")
    print("| first | second | n | first | second | b | c | p |")
    print("|---|---|---:|---:|---:|---:|---:|---:|")
    for first, second in comparisons:
        if first not in by_config or second not in by_config:
            continue
        ids = sorted(set(by_config[first]) & set(by_config[second]))
        a, b = [by_config[first][i] for i in ids], [by_config[second][i] for i in ids]
        if len(ids) < MIN_TEST_N:
            print(f"| {'/'.join(first)} | {'/'.join(second)} | {len(ids)} | | | | | n too small |")
            continue
        result = mcnemar_exact(a, b)
        print(f"| {'/'.join(first)} | {'/'.join(second)} | {len(ids)} | {sum(a)} | {sum(b)} | {result.b} | "
              f"{result.c} | {result.p_value:.3f} |")


def gate(rows: list[dict]) -> None:
    print("\n### Gate re-check: dev v1 + dev v2, Arm A, dense top-1 (retrieval-spec.md rule)\n")
    for provider in PROVIDERS:
        dev = [r for r in rows if r["split"] == "dev" and r["arm"] == "A" and r["mode"] == "dense"
               and r["provider"] == provider and r["ok"]]
        if not dev:
            continue
        current = dev[0]["threshold"]
        print(f"\n**{provider}** (current default {current}; GATE_THRESHOLDS unchanged)\n")
        print("| case | set | corpus | language | answerable | top-1 | gate at current default |")
        print("|---|---|---|---|---|---:|---|")
        for r in sorted(dev, key=lambda r: (r["corpus"], not r["answerable"], r["top1"])):
            print(f"| {r['case_id']} | {r['qset']} | {r['corpus']} | {r['language']} | "
                  f"{'yes' if r['answerable'] else 'no'} | {r['top1']:.4f} | {'refused' if r['gate_fired'] else 'pass'} |")
        print("\n| pool | answerable n | lowest answerable | highest unanswerable | rule value (lowest − 0.05) | overlap |")
        print("|---|---:|---:|---:|---:|---|")
        for label, pool in (("corpus1", [r for r in dev if r["corpus"] == "corpus1"]),
                            ("corpus2", [r for r in dev if r["corpus"] == "corpus2"]), ("pooled", dev)):
            ans = [r["top1"] for r in pool if r["answerable"]]
            una = [r["top1"] for r in pool if not r["answerable"]]
            if not ans:
                continue
            low, high = min(ans), max(una) if una else None
            overlap = "–" if high is None else ("**yes: DECISION REQUIRED**" if high >= low else "no")
            print(f"| {label} | {len(ans)} | {low:.4f} | {'–' if high is None else f'{high:.4f}'} | "
                  f"{low - GATE_MARGIN:.4f} | {overlap} |")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs-glob", required=True)
    args = parser.parse_args()
    run_ids = sorted(p.name for p in RESULTS.iterdir() if p.is_dir() and fnmatch.fnmatch(p.name, args.runs_glob))
    rows = collect(run_ids)
    print(f"{len(run_ids)} runs, {len(rows)} records. Thresholds in use: {dict(GATE_THRESHOLDS)}")
    v1 = [r for r in rows if r["qset"] == "v1" and r["split"] == "eval"]
    v2 = [r for r in rows if r["qset"] == "v2" and r["split"] == "eval"]
    if v1:
        headline(v1, "v1 eval (corpus 1, 32 answerable)")
        paired(v1, "v1 eval")
    if v2:
        c2 = [r for r in v2 if r["corpus"] == "corpus2"]
        headline(c2, "v2 eval, corpus 2 (A-D)")
        headline([r for r in v2 if r["corpus"] == "corpus1"], "v2 eval, corpus 1 (E identifier)")
        breakdown(v2, "category", CATEGORIES, "v2 eval per category (evidence_hit@5; F = gate refusals)")
        answerable = [r for r in v2 if r["answerable"]]
        breakdown(answerable, "language", ("vi", "en"), "v2 eval answerable per question language")
        breakdown(answerable, "typing", ("diacritics", "no_diacritics", "en"), "v2 eval answerable per typing")
        paired(c2, "v2 eval corpus 2 (answerable)")
        paired(v2, "v2 eval all answerable (corpus 1 + 2 pooled per config)")
        for category in CATEGORIES[:5]:
            paired([r for r in v2 if r["category"] == category], f"v2 eval {category}")
    gate(rows)
    eval_gate(rows)
    return 0


def eval_gate(rows: list[dict]) -> None:
    """Information only (never used for tuning): how often the current default gate refuses eval cases. The gate
    reads the dense top-1 in every mode, so the dense runs stand for all three."""
    print("\n### Eval split, current default gate (information only; dense top-1, every mode alike)\n")
    print("| embedder | arm | set / corpus | answerable refused | unanswerable refused |")
    print("|---|---|---|---:|---:|")
    groups = defaultdict(list)
    for r in rows:
        if r["split"] == "eval" and r["mode"] == "dense" and r["ok"]:
            groups[(r["provider"], r["arm"], f"{r['qset']} / {r['corpus']}")].append(r)
    for key in sorted(groups):
        sub = groups[key]
        ans = [int(r["gate_fired"]) for r in sub if r["answerable"]]
        una = [int(r["gate_fired"]) for r in sub if not r["answerable"]]
        print(f"| {key[0]} | {key[1]} | {key[2]} | {sum(ans)}/{len(ans)} | " + (f"{sum(una)}/{len(una)}" if una else "–") + " |")


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
