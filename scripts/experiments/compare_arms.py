"""EXP-001: compare Arm A and Arm B on the committed evaluation runs, classify failures, write the experiment files.

    python scripts/experiments/compare_arms.py --run-a RUN_ID --run-b RUN_ID [--data-root DIR] [--report PATH]

Reads, per arm, `data/evaluation/results/<run>/{run.json,records.jsonl,summary.json}` (numbers come from scoring.py's
per-record rows, nothing is re-scored), `data/evaluation/questions/expected-spans-v1.json`, and from `--data-root`
(default: this checkout; the files are git-ignored, so a worktree points it at the main checkout)
`data/processed/chunks/arm-{a,b}.jsonl` and `data/processed/documents/normalized.jsonl`. Each chunk file's SHA-256 must
equal the hash its `summary.json` recorded; otherwise the script refuses. Optional manual input:
`data/experiments/exp-001/failure-overrides.json` ({"CASE:ARM": {"stage": ..., "reason": ...}}).

Writes `data/experiments/exp-001/`: comparison.json, tables.md, per_case_diff.csv, discordant-chunks.json,
discordant-chunks.md, failures.csv, chunk-stats.json. With --report, replaces every `<!-- AUTO:name -->` ...
`<!-- /AUTO:name -->` block of that Markdown file with the matching table. Deterministic, offline: 0 Gemini requests.
"""
import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))

from knowledge_assistant.application.evaluation.experiment import (  # noqa: E402
    DESCRIPTIVE,
    LANGUAGE,
    STAGES,
    chunk_facts,
    classify_failure,
    compare_all,
    discordant_cases,
    failure_mode_signals,
    is_failure,
    language_tag,
)
from knowledge_assistant.application.evaluation.metrics.retrieval import chunk_index  # noqa: E402
from knowledge_assistant.application.evaluation.metrics.spans import spans_from_entry  # noqa: E402
from knowledge_assistant.application.evaluation.records import latest_records  # noqa: E402
from knowledge_assistant.application.ingestion.build_chunks import load_normalized_documents  # noqa: E402
from knowledge_assistant.infrastructure.chunking.markdown_structure import fenced_ranges  # noqa: E402
from knowledge_assistant.infrastructure.chunking.stats import cuts_code_fence, percentile  # noqa: E402

RESULTS = PROJECT_ROOT / "data" / "evaluation" / "results"
SPANS = PROJECT_ROOT / "data" / "evaluation" / "questions" / "expected-spans-v1.json"
OUT = PROJECT_ROOT / "data" / "experiments" / "exp-001"
TINY_DOCS = ("09", "22", "29")
HELD_CONSTANT = ("embedding_model", "embedding_dim", "top_k", "overfetch", "threshold", "prompt_version",
                 "prompt_sha256", "answer_model", "allow_fallback", "mode", "split", "freeze_tag", "question_files")
SLICES = (("overall", lambda row: True), ("en", lambda row: row["language"] == "en"),
          ("vi", lambda row: row["language"] == "vi"), ("parallel", lambda row: row["parallel_group_id"] is not None))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_arm(run_id: str, data_root: Path) -> dict:
    folder = RESULTS / run_id
    run = json.loads((folder / "run.json").read_text(encoding="utf-8"))
    summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    records = {key[0]: record for key, record in latest_records(read_jsonl(folder / "records.jsonl")).items()}
    chunk_file = data_root / "data" / "processed" / "chunks" / summary["inputs"]["chunk_file"]["name"]
    actual = sha256(chunk_file)
    if actual != summary["inputs"]["chunk_file"]["sha256"]:
        raise SystemExit(f"{chunk_file}: SHA-256 {actual} differs from summary.json's "
                         f"{summary['inputs']['chunk_file']['sha256']}: not the index these runs used")
    if sha256(folder / "records.jsonl") != summary["inputs"]["records.jsonl"]:
        raise SystemExit(f"{run_id}: records.jsonl changed since summary.json was computed")
    chunks = read_jsonl(chunk_file)
    return {"run_id": run_id, "arm": run["config"]["arm"], "run": run, "summary": summary, "records": records,
            "rows": {row["case_id"]: row for row in summary["rows"]}, "chunks": chunks,
            "chunk_file": {"name": chunk_file.name, "sha256": actual}}


# --- chunk statistics -----------------------------------------------------------------------------------------

def fence_cut_ids(chunks: list[dict], fences: dict[str, list[tuple[int, int]]]) -> set[str]:
    class _Span:  # cuts_code_fence reads char_start / char_end only
        def __init__(self, chunk):
            self.char_start, self.char_end = chunk["char_start"], chunk["char_end"]
    return {chunk["chunk_id"] for chunk in chunks if cuts_code_fence(_Span(chunk), fences[chunk["source_id"]])}


def chunk_stats(chunks: list[dict], cut_ids: set[str]) -> dict:
    sizes = sorted(len(chunk["display_text"]) for chunk in chunks)
    per_doc = {}
    for chunk in chunks:
        per_doc[chunk["source_id"]] = per_doc.get(chunk["source_id"], 0) + 1
    return {"chunks_total": len(chunks), "size_p50": percentile(sizes, 0.5), "size_p90": percentile(sizes, 0.9),
            "size_min": sizes[0], "size_max": sizes[-1], "chunks_cutting_code_fence": len(cut_ids),
            "pct_chunks_cutting_code_fence": round(100 * len(cut_ids) / len(chunks), 2),
            "tiny_doc_chunks": {source: per_doc.get(source, 0) for source in TINY_DOCS},
            "chunks_per_document": dict(sorted(per_doc.items()))}


# --- formatting -----------------------------------------------------------------------------------------------

def num(value, digits=3) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def pval(value) -> str:
    return "—" if value is None else ("<0.001" if value < 0.001 else f"{value:.3f}")


def table(rows: list[dict]) -> str:
    lines = ["| Metric | Arm A | Arm B | Δ (B−A) | 95 % CI of Δ | paired test | p | n |",
             "|---|---|---|---|---|---|---|---|"]
    for row in rows:
        digits = 1 if row["metric"].startswith(("latency", "tokens")) else 3
        if row["kind"] == DESCRIPTIVE:
            lines.append(f"| {row['metric']} (median) | {num(row['a'], 1)} | {num(row['b'], 1)} | — | — | "
                         f"not tested: {row['note']} | — | {row['n']} |")
            continue
        ci = "—" if row["ci"] is None else f"[{num(row['ci'][0], digits)}, {num(row['ci'][1], digits)}]"
        if row["test"] == "mcnemar_exact":
            test = f"McNemar b={row['mcnemar_b']} c={row['mcnemar_c']}"
        elif row["test"] == "wilcoxon_exact":
            test = f"Wilcoxon (n≠0 = {row['wilcoxon_n']})"
        else:
            test = "—"
        a, b = num(row["a"], digits), num(row["b"], digits)
        if row["metric"].startswith("latency"):
            a += f" (p50 {num(row['a_p50'], 1)} / p95 {num(row['a_p95'], 1)})"
            b += f" (p50 {num(row['b_p50'], 1)} / p95 {num(row['b_p95'], 1)})"
        lines.append(f"| {row['metric']} | {a} | {b} | {num(row['delta'], digits)} | {ci} | {test} | "
                     f"{pval(row['p'])} | {row['n']} |")
    return "\n".join(lines)


def cases(entry: dict, key: str) -> str:
    if key not in entry:
        return "—"
    return " / ".join(", ".join(case.removeprefix("Q-EVAL-") for case in side) or "none" for side in entry[key])


def csv_text(header: list[str], rows: list[list]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def fill_report(path: Path, blocks: dict[str, str]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    filled = []
    for name, body in blocks.items():
        pattern = re.compile(rf"(<!-- AUTO:{re.escape(name)} -->\n).*?(<!-- /AUTO:{re.escape(name)} -->)", re.S)
        if pattern.search(text):
            text = pattern.sub(lambda m: m.group(1) + body.rstrip("\n") + "\n" + m.group(2), text)
            filled.append(name)
    write(path, text)
    return filled


# --- main -----------------------------------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--run-a", required=True)
    parser.add_argument("--run-b", required=True)
    parser.add_argument("--data-root", type=Path, default=PROJECT_ROOT)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    a, b = load_arm(args.run_a, args.data_root), load_arm(args.run_b, args.data_root)
    if (a["arm"], b["arm"]) != ("A", "B"):
        raise SystemExit(f"--run-a must be arm A and --run-b arm B, got {a['arm']} and {b['arm']}")
    config_a, config_b = a["run"]["config"], b["run"]["config"]
    differing = [key for key in HELD_CONSTANT if config_a.get(key) != config_b.get(key)]
    if differing:
        raise SystemExit(f"runs differ on held-constant settings: {differing}")
    if not sha256(SPANS) == a["summary"]["inputs"]["expected-spans-v1.json"] == b["summary"]["inputs"]["expected-spans-v1.json"]:
        raise SystemExit("expected-spans-v1.json differs from the one the summaries used")
    case_ids = sorted(a["rows"])
    if case_ids != sorted(b["rows"]):
        raise SystemExit("the two runs do not cover the same cases")
    spans_file = json.loads(SPANS.read_text(encoding="utf-8"))["cases"]
    spans = {case_id: spans_from_entry(entry) if entry["answerable"] else None for case_id, entry in spans_file.items()}
    documents = load_normalized_documents(args.data_root / "data" / "processed" / "documents" / "normalized.jsonl")
    fences = {document.source_id: fenced_ranges(document.text) for document in documents}
    threshold = config_a["threshold"]

    arms = {"A": a, "B": b}
    for arm in arms.values():
        arm["cut_ids"] = fence_cut_ids(arm["chunks"], fences)
        arm["index"] = chunk_index(arm["chunks"])
        arm["facts"] = {case_id: chunk_facts(record, spans.get(case_id), arm["cut_ids"], arm["index"])
                        for case_id, record in arm["records"].items()}
    stats = {name: chunk_stats(arm["chunks"], arm["cut_ids"]) for name, arm in arms.items()}

    # 1. comparison tables per slice
    slices = {}
    for name, keep in SLICES:
        ids = [case_id for case_id in case_ids if keep(a["rows"][case_id])]
        slices[name] = compare_all(ids, a["rows"], b["rows"], a["records"], b["records"])
    by_metric = {row["metric"]: row for row in slices["overall"]}
    strict_lenient = []
    for lenient, strict in [(f"{level}_hit@{k}", f"{level}_hit@{k}:strict") for level in ("source", "section")
                            for k in (1, 3, 5)] + [("mrr", "mrr:strict"), ("lenient_accuracy", "accuracy")]:
        row_l, row_s = by_metric[lenient], by_metric[strict]
        entry = {"lenient": lenient, "strict": strict, "a": [row_l["a"], row_s["a"]], "b": [row_l["b"], row_s["b"]],
                 "delta": [row_l["delta"], row_s["delta"]], "p": [row_l["p"], row_s["p"]]}
        if "a_only" in row_l:
            entry["a_only"], entry["b_only"] = [row_l["a_only"], row_s["a_only"]], [row_l["b_only"], row_s["b_only"]]
        entry["differs"] = entry["a"][0] != entry["a"][1] or entry["b"][0] != entry["b"][1]
        strict_lenient.append(entry)

    # per-case diff (section hit@5 and first-hit rank, answerable cases)
    diff_rows, a_only, b_only, both_miss = [], [], [], []
    for case_id in case_ids:
        row_a, row_b = a["rows"][case_id], b["rows"][case_id]
        tags = row_a["failure_mode"] or ""
        ranks = []
        hits = []
        for arm_name in "AB":
            row = arms[arm_name]["rows"][case_id]
            hit = None if row["retrieval"] is None else row["retrieval"]["section_hit@5"]
            first = next((fact.rank for fact in arms[arm_name]["facts"][case_id][:5] if fact.hits_section), None)
            hits.append(hit)
            ranks.append(first)
        if hits[0] == 1 and hits[1] == 0:
            a_only.append(case_id)
        elif hits[0] == 0 and hits[1] == 1:
            b_only.append(case_id)
        elif hits == [0, 0]:
            both_miss.append(case_id)
        diff_rows.append([case_id, row_a["language"], row_a["size_class"], row_a["difficulty"], tags,
                          num(hits[0]), num(hits[1]), num(ranks[0]), num(ranks[1]),
                          (row_a["answer"] or {}).get("result") or "unlabelled",
                          (row_b["answer"] or {}).get("result") or "unlabelled"])

    # discordant cases with chunk-level evidence
    discordant = discordant_cases(case_ids, a["rows"], b["rows"], a["records"], b["records"])
    unlabelled = sorted(f"{row['case_id']}:{arm['arm']}" for arm in arms.values() for row in arm["rows"].values()
                        if row["answer"] is not None and row["answer"]["result"] is None)
    discordant_chunks = {}
    for case_id, reasons in discordant.items():
        slots = {slot: sorted({f"#{s['source_id']} {s['heading_path']} ({s['role']})" for s in entries})
                 for slot, entries in spans_file[case_id]["slots"].items()}
        discordant_chunks[case_id] = {"reasons": reasons, "slots": slots, **{
            arm_name: {"result": (arm["rows"][case_id]["answer"] or {}).get("result"),
                       "top1_score": arm["records"][case_id]["top1_score"],
                       "gate_fired": arm["records"][case_id]["gate_fired"],
                       "cited": [c["chunk_id"] for c in arm["records"][case_id]["citations"]],
                       "chunks": [fact.__dict__ for fact in arm["facts"][case_id]]}
            for arm_name, arm in arms.items()}}

    # 2. failures
    overrides_path = OUT / "failure-overrides.json"
    overrides = json.loads(overrides_path.read_text(encoding="utf-8")) if overrides_path.exists() else {}
    failures = []
    for arm_name, arm in arms.items():
        failed = {case_id for case_id, row in arm["rows"].items() if is_failure(row)}
        for case_id in case_ids:
            failure = classify_failure(arm["rows"][case_id], arm["records"][case_id], arm["facts"][case_id], threshold)
            if failure is None:
                continue
            secondary = list(failure.secondary)
            if language_tag(case_id, arm["rows"], failed):
                secondary.append(LANGUAGE)
            override = overrides.get(f"{case_id}:{arm_name}", {})
            failures.append({"case_id": case_id, "arm": arm_name, "language": arm["rows"][case_id]["language"],
                             "failure_mode_tag": arm["rows"][case_id]["failure_mode"] or "",
                             "result": failure.result, "rule_stage": failure.stage, "rule": failure.rule,
                             "secondary": ";".join(secondary), "stage": override.get("stage", failure.stage),
                             "override_reason": override.get("reason", "")})
    unknown = set(overrides) - {f"{f['case_id']}:{f['arm']}" for f in failures}
    if unknown:
        raise SystemExit(f"overrides for records that are not failures: {sorted(unknown)}")
    counts = {stage: {arm: sum(1 for f in failures if f["arm"] == arm and f["stage"] == stage) for arm in "AB"}
              for stage in STAGES}

    # citation defects on correct answers (stage 6 cannot fire under the trigger; listed separately)
    citation_defects = []
    for arm_name, arm in arms.items():
        for case_id in case_ids:
            row = arm["rows"][case_id]
            citation = row["citation"] or {}
            if (row["answer"] or {}).get("result") == "correct" and citation.get("answered") and row["answerable"] and (
                    citation.get("section_precision") != 1.0 or citation.get("support_rate") not in (1.0, None)):
                citation_defects.append({"case_id": case_id, "arm": arm_name,
                                         "section_precision": citation.get("section_precision"),
                                         "support_rate": citation.get("support_rate"),
                                         "auto_class": citation.get("auto_class"),
                                         "judge_class": citation.get("judge_class")})

    OUT.mkdir(parents=True, exist_ok=True)
    comparison = {
        "inputs": {name: {"run_id": arm["run_id"], "records.jsonl": arm["summary"]["inputs"]["records.jsonl"],
                          "judgements.jsonl": arm["summary"]["inputs"]["judgements.jsonl"],
                          "summary.json": sha256(RESULTS / arm["run_id"] / "summary.json"),
                          "chunk_file": arm["chunk_file"]} for name, arm in arms.items()},
        "expected-spans-v1.json": sha256(SPANS),
        "held_constant": {key: config_a.get(key) for key in HELD_CONSTANT},
        "arm_config": {"A": {"chunker_config": a["chunks"][0]["chunker_config"]},
                       "B": {"chunker_config": b["chunks"][0]["chunker_config"]}},
        "unlabelled": unlabelled,
        "slices": slices,
        "strict_lenient": strict_lenient,
        "section_hit@5": {"a_only_hits": a_only, "b_only_hits": b_only, "both_miss": both_miss},
        "discordant": discordant,
        "failure_counts": counts,
        "citation_defects_on_correct_answers": citation_defects,
        "chunk_stats": stats,
        "failure_mode_signals": {name: {case_id: failure_mode_signals(record)
                                        for case_id, record in arm["records"].items()} for name, arm in arms.items()},
    }
    write(OUT / "comparison.json", json.dumps(comparison, indent=1, ensure_ascii=False) + "\n")
    write(OUT / "chunk-stats.json", json.dumps(stats, indent=1) + "\n")
    write(OUT / "per_case_diff.csv", csv_text(
        ["case_id", "language", "size_class", "difficulty", "failure_mode_tag", "a_section_hit@5", "b_section_hit@5",
         "a_first_hit_rank", "b_first_hit_rank", "a_result", "b_result"], diff_rows))
    write(OUT / "failures.csv", csv_text(
        ["case_id", "arm", "language", "failure_mode_tag", "result", "rule_stage", "rule", "secondary", "stage",
         "override_reason"], [list(f.values()) for f in failures]))
    write(OUT / "discordant-chunks.json", json.dumps(discordant_chunks, indent=1, ensure_ascii=False) + "\n")

    md = []
    for case_id, entry in discordant_chunks.items():
        md.append(f"## {case_id}\n\nDiffers: {'; '.join(entry['reasons'])}\n")
        md += [f"- slot {slot}: {'; '.join(sections)}" for slot, sections in entry["slots"].items()] + [""]
        for arm_name in "AB":
            side = entry[arm_name]
            md.append(f"**Arm {arm_name}**: result `{side['result']}`, top-1 {side['top1_score']:.4f}, gate "
                      f"{'fired' if side['gate_fired'] else 'passed'}, cited {side['cited'] or '—'}\n")
            md.append("| rank | chunk | heading path | score | slots hit | evidence quotes | points covered | cuts fence | first 200 chars |")
            md.append("|---|---|---|---|---|---|---|---|---|")
            for fact in side["chunks"][:3]:
                head = fact["head"].replace("\n", " ").replace("|", "\\|")
                md.append(f"| {fact['rank']} | `{fact['chunk_id']}` | {fact['heading_path']} | {fact['score']:.4f} | "
                          f"{','.join(fact['slots_hit']) or num(fact['hits_section'])} | {fact['evidence_quotes_contained']}/"
                          f"{fact['evidence_quotes_total']} | {','.join(fact['points_covered']) or '—'} | {fact['cuts_code_fence']} | "
                          f"{head} |")
            first = next((f for f in side["chunks"] if f["hits_section"]), None)
            if first is not None and first["rank"] > 3:
                md.append(f"\nFirst section-hitting chunk: rank {first['rank']} `{first['chunk_id']}`.")
            md.append("")
    write(OUT / "discordant-chunks.md", "# EXP-001 discordant cases: top-3 chunks per arm\n\n"
          "Generated by `scripts/experiments/compare_arms.py`; full top-5 in `discordant-chunks.json`.\n\n"
          + "\n".join(md))

    blocks = {f"results-{name}": table(rows) for name, rows in slices.items()}
    blocks["chunk-stats"] = "\n".join([
        "| Chunk statistic | Arm A | Arm B |", "|---|---|---|",
        *[f"| {label} | {stats['A'][key]} | {stats['B'][key]} |" for label, key in (
            ("chunks", "chunks_total"), ("size p50 (chars)", "size_p50"), ("size p90 (chars)", "size_p90"),
            ("chunks cutting a code fence", "chunks_cutting_code_fence"),
            ("% chunks cutting a code fence", "pct_chunks_cutting_code_fence"))],
        *[f"| chunks of tiny doc #{source} | {stats['A']['tiny_doc_chunks'][source]} | "
          f"{stats['B']['tiny_doc_chunks'][source]} |" for source in TINY_DOCS]])
    blocks["failure-counts"] = "\n".join(["| Stage | Arm A | Arm B |", "|---|---|---|",
                                          *[f"| {stage} | {counts[stage]['A']} | {counts[stage]['B']} |"
                                            for stage in STAGES],
                                          f"| **total** | {sum(c['A'] for c in counts.values())} | "
                                          f"{sum(c['B'] for c in counts.values())} |"])
    blocks["failures"] = "\n".join(["| Case | Arm | Lang | Result | Stage | Rule | Secondary |",
                                    "|---|---|---|---|---|---|---|",
                                    *[f"| {f['case_id']} | {f['arm']} | {f['language']} | {f['result']} | "
                                      f"{f['stage']}{' (override)' if f['override_reason'] else ''} | {f['rule']} | "
                                      f"{f['secondary'] or '—'} |" for f in failures]])
    blocks["strict-lenient"] = "\n".join([
        "| Lenient / strict | A (len / str) | B (len / str) | Δ (len / str) | p (len / str) | A-only cases (len / str) "
        "| B-only cases (len / str) |", "|---|---|---|---|---|---|---|",
        *[f"| {e['lenient']} / {e['strict']} | {num(e['a'][0])} / {num(e['a'][1])} | {num(e['b'][0])} / "
          f"{num(e['b'][1])} | {num(e['delta'][0])} / {num(e['delta'][1])} | {pval(e['p'][0])} / {pval(e['p'][1])} | "
          f"{cases(e, 'a_only')} | {cases(e, 'b_only')} |" for e in strict_lenient if e["differs"]]])
    write(OUT / "tables.md", "# EXP-001 tables (generated by compare_arms.py)\n\n" + "\n\n".join(
        f"## {name}\n\n{body}" for name, body in blocks.items()) + "\n")
    if args.report:
        print("report blocks filled:", ", ".join(fill_report(args.report, blocks)) or "none")
    print(f"discordant cases: {len(discordant)}; failures A {sum(c['A'] for c in counts.values())}, "
          f"B {sum(c['B'] for c in counts.values())}; unlabelled {unlabelled}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
