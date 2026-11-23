"""Download the EmbeddingGemma ONNX builds that `embedding_bench.py` measures. Text model files only.

Run it only after the owner has chosen the target folder: ``--models-dir`` has no default on purpose, and the folder
must be outside the repository (model files are never committed).

Each model goes to ``<models-dir>/<name>/`` with the Hugging Face layout (``onnx/model*.onnx`` plus its
``.onnx_data`` file, ``tokenizer.json``, config files). For EmbeddingGemma 2 only the text model is fetched: the
``vision_encoder*`` and ``audio_encoder*`` files are never matched.

    python scripts/benchmark/download_embedding_models.py --models-dir D:/models/embeddinggemma --dry-run
    python scripts/benchmark/download_embedding_models.py --models-dir D:/models/embeddinggemma
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

MODELS = {
    "gemma1": "onnx-community/embeddinggemma-300m-ONNX",
    "gemma2": "onnx-community/embeddinggemma-2-ONNX",
}
# Variant label -> ONNX file stem (onnx-community naming).
VARIANTS = {
    "fp32": "model",
    "fp16": "model_fp16",
    "int8": "model_quantized",  # dynamic INT8
    "int4": "model_q4",  # INT4 weights (MatMulNBits), FP32 activations
}
SHARED_FILES = ["config.json", "tokenizer.json", "tokenizer_config.json", "special_tokens_map.json",
                "added_tokens.json", "config_sentence_transformers.json"]


def patterns(variants: list[str]) -> list[str]:
    files = list(SHARED_FILES)
    for variant in variants:
        stem = VARIANTS[variant]
        files += [f"onnx/{stem}.onnx", f"onnx/{stem}.onnx_data"]
    return files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models-dir", required=True, type=Path)
    parser.add_argument("--models", nargs="+", choices=sorted(MODELS), default=sorted(MODELS))
    parser.add_argument("--variants", nargs="+", choices=list(VARIANTS), default=list(VARIANTS))
    parser.add_argument("--dry-run", action="store_true", help="list the matching files and sizes, download nothing")
    args = parser.parse_args(argv)

    models_dir = args.models_dir.resolve()
    if models_dir == REPO_ROOT or REPO_ROOT in models_dir.parents:
        parser.error(f"--models-dir must be outside the repository ({REPO_ROOT})")

    from huggingface_hub import HfApi, snapshot_download

    wanted = patterns(args.variants)
    api = HfApi()
    for name in args.models:
        repo = MODELS[name]
        info = api.model_info(repo, files_metadata=True)
        matched = [s for s in info.siblings if s.rfilename in wanted]
        total = sum(s.size or 0 for s in matched)
        print(f"{name}: {repo} @ {info.sha[:12]} -> {models_dir / name} ({len(matched)} files, {total / 1e9:.2f} GB)")
        for s in matched:
            print(f"    {s.rfilename:40s} {(s.size or 0) / 1e6:9.1f} MB")
        if args.dry_run:
            continue
        snapshot_download(repo, revision=info.sha, allow_patterns=wanted, local_dir=models_dir / name)
        (models_dir / name / "REVISION").write_text(f"{repo}@{info.sha}\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
