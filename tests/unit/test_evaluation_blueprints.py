"""Offline checks for the EVAL-001 evaluation design (blueprints, evidence map, coverage matrix)."""
import importlib.util
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
QUESTIONS = ROOT / "data" / "evaluation" / "questions"
BLUEPRINTS = QUESTIONS / "blueprint.yaml"
EVIDENCE_MAP = QUESTIONS / "evidence-map.yaml"
COVERAGE_MATRIX = QUESTIONS / "coverage-matrix.yaml"
INVENTORY = ROOT / "data" / "processed" / "documents" / "section-inventory.jsonl"
MANIFEST = ROOT / "corpus" / "manifest.json"
SOURCES = ROOT / "corpus" / "sources"
MATRIX_SCRIPT = ROOT / "scripts" / "evaluation" / "build_coverage_matrix.py"

FORBIDDEN_IDS = {"14", "19", "24", "25", "27"}
ADR_0003_FAILURE_MODES = {
    "mixed_version", "near_duplicate_topk", "fixed_size_code_split", "link_list_noise",
    "tiny_doc_single_chunk", "large_doc_outranks_small", "specific_heading", "repeated_version_sections",
}
ALLOWED = {
    "split": {"eval", "dev"},
    "language": {"en", "vi"},
    "scope": {"single-source", "cross-document", "corpus-insufficient"},
    "cognitive_level": {"recall", "explain", "apply", "analyze", "compare", "diagnose"},
    "difficulty": {"easy", "medium", "hard"},
    "size_class": {"tiny", "medium", "huge", "mixed", "none"},
}
REFUSAL = "The assistant should explicitly state that the provided collection does not contain sufficient information."


def _blueprints():
    return yaml.safe_load(BLUEPRINTS.read_text(encoding="utf-8"))["blueprints"]


def _split(name):
    return [b for b in _blueprints() if b["split"] == name]


def _normalize(text):
    return re.sub(r"\s+", " ", text).strip()


def _section_texts():
    """(source_id, heading_path) -> list of (variant, normalized section text)."""
    lines = {p.name.split("-")[0]: p.read_text(encoding="utf-8").replace("\r\n", "\n").split("\n")
             for p in SOURCES.glob("*.md")}
    texts = defaultdict(list)
    for row in map(json.loads, INVENTORY.read_text(encoding="utf-8").splitlines()):
        body = "\n".join(lines[row["source_id"]][row["line_start"] - 1 : row["line_end"]])
        texts[(row["source_id"], row["heading_path"])].append((row["variant"], _normalize(body)))
    return texts


def _all_source_refs(b):
    refs = list(b["source_ids"]) + list(b.get("near_miss_sources", []))
    refs += [s["source_id"] for s in b["expected_sources"] + b["acceptable_alternate_sources"]]
    refs += [e["source_id"] for e in b["ground_truth"]["evidence"]]
    return refs


def _load_matrix_builder():
    spec = importlib.util.spec_from_file_location("build_coverage_matrix", MATRIX_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_eval_set_follows_the_od4_mix():
    eval_set = _split("eval")
    assert len(eval_set) == 36
    assert Counter(b["scope"] for b in eval_set) == {"single-source": 28, "cross-document": 4, "corpus-insufficient": 4}
    assert Counter(b["language"] for b in eval_set) == {"en": 18, "vi": 18}
    answerable = [b for b in eval_set if b["scope"] != "corpus-insufficient"]
    assert len(answerable) - 2 >= 30  # two answerable cases may be dropped in EVAL-002


def test_dev_set_is_small_bilingual_and_disjoint_from_eval():
    dev, eval_set = _split("dev"), _split("eval")
    assert len(dev) == 6
    assert Counter(b["language"] for b in dev) == {"en": 3, "vi": 3}
    assert all(b["parallel_group_id"] is None for b in dev)
    eval_targets = {(s["source_id"], s["heading_path"]) for b in eval_set for s in b["expected_sources"]}
    dev_targets = {(s["source_id"], s["heading_path"]) for b in dev for s in b["expected_sources"]}
    assert not eval_targets & dev_targets


def test_ids_are_unique_and_prefixed_by_split():
    ids = [b["id"] for b in _blueprints()]
    assert len(ids) == len(set(ids))
    for b in _blueprints():
        prefix = "BP-EVAL-" if b["split"] == "eval" else "BP-DEV-"
        assert b["id"].startswith(prefix), b["id"]


def test_fields_use_allowed_values():
    for b in _blueprints():
        for field, allowed in ALLOWED.items():
            assert b[field] in allowed, (b["id"], field, b[field])
        mode = b["evaluation_target"]["failure_mode"]
        assert mode in ADR_0003_FAILURE_MODES | {"none"}, (b["id"], mode)


def test_parallel_groups_pair_one_en_and_one_vi_with_the_same_ground_truth():
    groups = defaultdict(list)
    for b in _split("eval"):
        if b["parallel_group_id"]:
            groups[b["parallel_group_id"]].append(b)
    assert 6 <= len(groups) <= 8
    shared = ["expected_sources", "acceptable_alternate_sources", "ground_truth",
              "answer_acceptance_criteria", "citation_acceptance_criteria"]
    for group_id, cases in groups.items():
        assert sorted(c["language"] for c in cases) == ["en", "vi"], group_id
        en, vi = sorted(cases, key=lambda c: c["language"])
        for field in shared:
            assert en[field] == vi[field], (group_id, field)


def test_only_accepted_documents_are_referenced():
    accepted = {d["source_id"] for d in json.loads(MANIFEST.read_text(encoding="utf-8"))["documents"]}
    for b in _blueprints():
        for source_id in _all_source_refs(b):
            assert source_id in accepted and source_id not in FORBIDDEN_IDS, (b["id"], source_id)


def test_heading_paths_exist_in_the_section_inventory():
    texts = _section_texts()
    for b in _blueprints():
        refs = b["expected_sources"] + b["acceptable_alternate_sources"] + b["ground_truth"]["evidence"]
        for ref in refs:
            assert (ref["source_id"], ref["heading_path"]) in texts, (b["id"], ref["heading_path"])


def test_evidence_quotes_are_verbatim_inside_their_section():
    texts = _section_texts()
    for b in _blueprints():
        variant_of = {s["source_id"]: s.get("evidence_variant") for s in b["expected_sources"]}
        for ev in b["ground_truth"]["evidence"]:
            assert len(ev["quote"]) <= 300, (b["id"], ev["quote"][:40])
            quote = _normalize(ev["quote"])
            variants = [v for v, text in texts[(ev["source_id"], ev["heading_path"])] if quote in text]
            assert variants, (b["id"], ev["quote"][:60])
            wanted = variant_of.get(ev["source_id"])
            if wanted is not None and ev["heading_path"] in {s["heading_path"] for s in b["expected_sources"]}:
                assert wanted in variants, (b["id"], "evidence not in variant", wanted)


def test_answerable_cases_have_ground_truth_and_criteria():
    for b in _blueprints():
        if b["scope"] == "corpus-insufficient":
            continue
        assert b["expected_sources"], b["id"]
        assert any(p["required"] for p in b["ground_truth"]["answer_points"]), b["id"]
        evidence_sources = {e["source_id"] for e in b["ground_truth"]["evidence"]}
        assert {s["source_id"] for s in b["expected_sources"]} <= evidence_sources, b["id"]
        assert b["answer_acceptance_criteria"]["must_not_claim"], b["id"]
        assert b["citation_acceptance_criteria"], b["id"]
        if b["scope"] == "cross-document":
            assert len({s["source_id"] for s in b["expected_sources"]}) >= 2, b["id"]


def test_insufficient_cases_expect_a_refusal_and_have_an_absence_proof():
    proofs = {p["id"]: p for p in yaml.safe_load(EVIDENCE_MAP.read_text(encoding="utf-8"))["absence_proofs"]}
    for b in _blueprints():
        if b["scope"] != "corpus-insufficient":
            continue
        assert not b["expected_sources"] and not b["ground_truth"]["answer_points"], b["id"]
        assert b["evaluation_target"]["expected_behavior"] == REFUSAL, b["id"]
        assert proofs[b["absence_proof"]]["blueprint"] == b["id"]


def test_absence_proof_terms_have_no_hits_in_the_accepted_sources():
    texts = {p.name.split("-")[0]: p.read_text(encoding="utf-8").lower() for p in SOURCES.glob("*.md")}
    sections = _section_texts()
    for proof in yaml.safe_load(EVIDENCE_MAP.read_text(encoding="utf-8"))["absence_proofs"]:
        for term in proof["zero_hit_terms"]:
            hits = [sid for sid, text in texts.items() if term.lower() in text]
            assert not hits, (proof["id"], term, hits)
        for allowed in proof.get("allowed_hits", []):
            term = allowed["term"].lower()
            total = sum(text.count(term) for text in texts.values())
            in_section = sum(text.lower().count(term) for _, text in sections[(allowed["source_id"], allowed["heading_path"])])
            assert total == in_section > 0, (proof["id"], allowed["term"], total, in_section)


def test_design_covers_failure_modes_levels_and_key_documents():
    eval_set = _split("eval")
    assert {b["evaluation_target"]["failure_mode"] for b in eval_set} >= ADR_0003_FAILURE_MODES
    assert {b["cognitive_level"] for b in eval_set} == ALLOWED["cognitive_level"]
    assert {b["difficulty"] for b in eval_set} == ALLOWED["difficulty"]
    expected = {s["source_id"] for b in eval_set for s in b["expected_sources"]}
    assert {"13", "17", "23"} <= expected  # version-heavy docs (ADR-0003)
    assert {"22", "29", "18"} <= expected  # tiny docs with answerable content


def test_coverage_matrix_file_matches_the_blueprints():
    builder = _load_matrix_builder()
    assert yaml.safe_load(COVERAGE_MATRIX.read_text(encoding="utf-8")) == builder.build_matrix(_blueprints())
