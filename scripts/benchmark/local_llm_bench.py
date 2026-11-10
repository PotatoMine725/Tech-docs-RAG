"""Speed and memory benchmark for a local GGUF model under llama.cpp. Measures only; decides nothing.

Standard library only, so it runs on a target machine without the project's virtual environment.

Two measurements per (model, GPU-layers) configuration:

1. ``llama-bench``: raw prompt-processing and generation speed in tokens per second.
2. One streamed answer through ``llama-server`` per prompt size: time to first token, prompt and generation
   tokens per second as the server reports them, and the server's peak memory.

The answer in (2) is a speed probe, not a quality check: the prompt is filler text cut to an exact token count,
and the model is forced to write exactly ``--gen-tokens`` tokens so that runs are comparable. Retrieval is not
included because the local pipeline does not exist yet.

Example (CPU against integrated GPU, with a Vulkan build of llama.cpp)::

    python scripts/benchmark/local_llm_bench.py --llama-dir C:/llama --model C:/models/qwen3-1.7b-q4_k_m.gguf \
        --threads 4 --ngl 0 99 --prompt-tokens 800 2500 --label gen10-8gb

Run with ``--dry-run`` first to print the exact ``llama-bench`` and ``llama-server`` commands and check them
against the installed llama.cpp version.

Numbers from a machine that is not the target are relative only (prompt A against B, model A against B).
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import socket
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

FILLER = (
    "A binary search tree keeps every key in its left subtree smaller than the node and every key in its right "
    "subtree larger, so a lookup discards half of the remaining keys at each step when the tree is balanced. "
    "Cây tìm kiếm nhị phân lưu các khóa nhỏ hơn ở nhánh trái và các khóa lớn hơn ở nhánh phải, vì vậy mỗi bước "
    "tìm kiếm loại bỏ một nửa số khóa còn lại khi cây cân bằng. "
)
HEAD = (
    "You are a study assistant. Answer the QUESTION using only the numbered CONTEXT passages. "
    "Cite passages as [n].\n\nCONTEXT:\n[1] "
)
TAIL = "\n\nQUESTION: Explain how a lookup works and why balance matters.\n\nANSWER: "


def exe(llama_dir: Path, name: str, must_exist: bool = True) -> Path:
    path = llama_dir / (name + (".exe" if os.name == "nt" else ""))
    if must_exist and not path.is_file():
        raise SystemExit(f"not found: {path}")
    return path


def bench_command(args: argparse.Namespace, model: Path, ngl: int) -> list[str]:
    return [
        str(exe(args.llama_dir, "llama-bench", not args.dry_run)), "-m", str(model), "-t", str(args.threads),
        "-ngl", str(ngl), "-p", ",".join(str(size) for size in args.prompt_tokens),
        "-n", str(args.gen_tokens), "-r", "3", "-o", "json",
    ]


def server_context(args: argparse.Namespace) -> int:
    return max(4096, max(args.prompt_tokens) + args.gen_tokens + 64)


def server_command(args: argparse.Namespace, model: Path, ngl: int, mmap: bool, port: int | str) -> list[str]:
    command = [
        str(exe(args.llama_dir, "llama-server", not args.dry_run)), "-m", str(model), "-t", str(args.threads),
        "-ngl", str(ngl), "-c", str(server_context(args)), "-np", "1", "--host", "127.0.0.1", "--port", str(port),
    ]
    return command if mmap else [*command, "--no-mmap"]


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def post_json(url: str, payload: dict, timeout: float = 600.0) -> dict:
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def total_ram_bytes() -> int | None:
    try:
        if os.name == "nt":

            class MemoryStatus(ctypes.Structure):
                _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong)] + [
                    (name, ctypes.c_ulonglong)
                    for name in ("total", "avail", "total_page", "avail_page", "total_virt", "avail_virt", "ext")
                ]

            status = MemoryStatus()
            status.dwLength = ctypes.sizeof(status)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return int(status.total)
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) * 1024
    except (OSError, AttributeError, ValueError):
        pass
    return None


def peak_memory_bytes(process: subprocess.Popen) -> int | None:
    """Peak resident memory of a running child process. Memory on an integrated GPU is not counted."""
    try:
        if os.name == "nt":
            from ctypes import wintypes

            class Counters(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                    (name, ctypes.c_size_t)
                    for name in (
                        "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage",
                        "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage",
                    )
                ]

            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            get_info = ctypes.windll.kernel32.K32GetProcessMemoryInfo
            get_info.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
            get_info.restype = wintypes.BOOL
            if get_info(int(process._handle), ctypes.byref(counters), counters.cb):  # noqa: SLF001
                return int(counters.PeakWorkingSetSize)
            return None
        for line in Path(f"/proc/{process.pid}/status").read_text().splitlines():
            if line.startswith("VmHWM:"):
                return int(line.split()[1]) * 1024
    except (OSError, AttributeError, ValueError):
        pass
    return None


def run_llama_bench(command: list[str]) -> dict:
    done = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    result: dict = {"command": command, "returncode": done.returncode}
    try:
        result["rows"] = json.loads(done.stdout[done.stdout.index("[") :])
    except ValueError:
        result["stdout"] = done.stdout[-4000:]
        result["stderr"] = done.stderr[-4000:]
    return result


def build_prompt(base_url: str, target_tokens: int, filler: str, nonce: str) -> str:
    """Filler cut so that the whole prompt is ``target_tokens`` long by the model's own tokenizer.

    ``nonce`` is put at the very start so that no two requests share a prefix: together with
    ``cache_prompt: false`` this guarantees the server processes the whole prompt every time.
    """
    head = f"Request {nonce}. " + HEAD
    fixed = len(post_json(f"{base_url}/tokenize", {"content": head + TAIL})["tokens"])
    want = max(target_tokens - fixed, 1)
    text = filler
    tokens = post_json(f"{base_url}/tokenize", {"content": text})["tokens"]
    while len(tokens) < want:
        text += filler
        tokens = post_json(f"{base_url}/tokenize", {"content": text})["tokens"]
    body = post_json(f"{base_url}/detokenize", {"tokens": tokens[:want]})["content"]
    return head + body + TAIL


def parse_sse_line(line: bytes) -> dict | None:
    text = line.decode("utf-8", errors="replace").strip()
    if not text.startswith("data:"):
        return None
    payload = text[len("data:") :].strip()
    if not payload or payload == "[DONE]":
        return None
    try:
        return json.loads(payload)
    except ValueError:
        return None


def stream_answer(base_url: str, prompt: str, gen_tokens: int) -> dict:
    payload = {
        "prompt": prompt, "n_predict": gen_tokens, "stream": True, "cache_prompt": False,
        "temperature": 0.0, "seed": 1, "ignore_eos": True,
    }
    request = urllib.request.Request(
        f"{base_url}/completion", data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    first_token_s = None
    timings: dict = {}
    with urllib.request.urlopen(request, timeout=1800.0) as response:
        for line in response:
            event = parse_sse_line(line)
            if event is None:
                continue
            if first_token_s is None and event.get("content"):
                first_token_s = time.perf_counter() - started
            if event.get("stop"):
                timings = event.get("timings") or {}
    return {
        "time_to_first_token_s": first_token_s,
        "total_s": time.perf_counter() - started,
        "prompt_tokens": timings.get("prompt_n"),
        "prompt_tokens_per_s": timings.get("prompt_per_second"),
        "generated_tokens": timings.get("predicted_n"),
        "generated_tokens_per_s": timings.get("predicted_per_second"),
    }


def wait_until_ready(base_url: str, process: subprocess.Popen | None, timeout_s: float) -> float:
    started = time.perf_counter()
    while time.perf_counter() - started < timeout_s:
        if process is not None and process.poll() is not None:
            raise RuntimeError(f"llama-server exited with code {process.returncode} while loading")
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=5.0) as response:
                if response.status == 200:
                    return time.perf_counter() - started
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.5)
    raise RuntimeError(f"llama-server not ready after {timeout_s:.0f} s")


def run_answers(base_url: str, args: argparse.Namespace, filler: str) -> dict:
    """One unmeasured warm-up, then ``--repeats`` measured runs per prompt size; medians over the measured runs."""
    counter = iter(range(1, 10_000))

    def one(size: int) -> dict:
        prompt = build_prompt(base_url, size, filler, f"{time.time_ns()}-{next(counter):04d}")
        return stream_answer(base_url, prompt, args.gen_tokens)

    warmup = one(min(args.prompt_tokens))
    rows = []
    for size in args.prompt_tokens:
        runs = [one(size) for _ in range(args.repeats)]
        row: dict = {"target_prompt_tokens": size, "runs": runs}
        for key in ("time_to_first_token_s", "prompt_tokens_per_s", "generated_tokens_per_s"):
            values = [run[key] for run in runs if run[key] is not None]
            row[f"median_{key}"] = statistics.median(values) if values else None
        rows.append(row)
    return {"warmup": warmup, "answers": rows}


def run_server_config(args: argparse.Namespace, model: Path, ngl: int, mmap: bool, filler: str) -> dict:
    port = free_port()
    base_url = f"http://127.0.0.1:{port}"
    command = server_command(args, model, ngl, mmap, port)
    log_path = args.out.with_suffix(f".server-{model.stem}-ngl{ngl}-{'mmap' if mmap else 'nommap'}.log")
    result: dict = {"command": command, "context": server_context(args)}
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            result["load_s"] = wait_until_ready(base_url, process, args.load_timeout)
            result.update(run_answers(base_url, args, filler))
            result["peak_memory_bytes"] = peak_memory_bytes(process)
        except (RuntimeError, urllib.error.URLError, OSError, KeyError) as error:
            result["error"] = f"{type(error).__name__}: {error} (see {log_path})"
        finally:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
    return result


def print_summary(report: dict) -> None:
    print(
        f"\n{'model':<34}{'ngl':>4}{'mmap':>6}{'prompt':>8}{'TTFT s':>9}{'prompt t/s':>12}{'gen t/s':>9}{'peak MB':>9}"
        f"\n(medians of {report['settings']['repeats']} measured runs after one warm-up)"
    )
    for config in report["configs"]:
        server = config.get("server") or {}
        mmap = {True: "on", False: "off", None: "n/a"}[config.get("mmap")]
        if "error" in server:
            print(f"{config['model'][:33]:<34}{config['ngl']:>4}{mmap:>6}  ERROR {server['error']}")
            continue
        peak = server.get("peak_memory_bytes")
        for row in server.get("answers", []):
            cells = [
                row["median_time_to_first_token_s"], row["median_prompt_tokens_per_s"],
                row["median_generated_tokens_per_s"], None if peak is None else peak / 2**20,
            ]
            shown = ["n/a" if cell is None else f"{cell:.1f}" for cell in cells]
            print(
                f"{config['model'][:33]:<34}{config['ngl']:>4}{mmap:>6}{row['target_prompt_tokens']:>8}"
                f"{shown[0]:>9}{shown[1]:>12}{shown[2]:>9}{shown[3]:>9}"
            )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--llama-dir", type=Path, help="folder holding llama-bench and llama-server")
    parser.add_argument("--model", type=Path, nargs="+", help="one or more GGUF files")
    parser.add_argument("--server-url", help="use an already running llama-server; skips llama-bench and memory")
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--ngl", type=int, nargs="+", default=[0], help="GPU layers per configuration; 0 = CPU only")
    parser.add_argument("--prompt-tokens", type=int, nargs="+", default=[800, 2500])
    parser.add_argument("--gen-tokens", type=int, default=200)
    parser.add_argument("--repeats", type=int, default=3, help="measured runs per prompt size, after one warm-up")
    parser.add_argument(
        "--mmap", choices=("on", "off", "both"), default="both",
        help="memory-map the model (llama.cpp default) or load it fully with --no-mmap. A mapped model may be "
        "under-counted in peak memory, so the 'off' run gives the real RAM figure. Default: both",
    )
    parser.add_argument("--dry-run", action="store_true", help="print the llama.cpp commands and run nothing")
    parser.add_argument("--context-file", type=Path, help="UTF-8 text used as prompt filler instead of the built-in")
    parser.add_argument("--skip-llama-bench", action="store_true")
    parser.add_argument("--load-timeout", type=float, default=300.0)
    parser.add_argument("--label", default="unlabelled", help="machine name recorded in the report")
    parser.add_argument("--out", type=Path, help="report path; default local-llm-bench-<label>.json")
    args = parser.parse_args(argv)
    if not args.server_url and not (args.llama_dir and args.model):
        parser.error("give --llama-dir and --model, or --server-url")
    args.out = args.out or Path(f"local-llm-bench-{args.label}.json")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mmap_modes = {"on": [True], "off": [False], "both": [True, False]}[args.mmap]
    if args.dry_run:
        if args.server_url:
            raise SystemExit("--dry-run prints llama.cpp commands; it has nothing to print with --server-url")
        for model in args.model:
            for ngl in args.ngl:
                if not args.skip_llama_bench:
                    print(subprocess.list2cmdline(bench_command(args, model, ngl)))
                for mmap in mmap_modes:
                    print(subprocess.list2cmdline(server_command(args, model, ngl, mmap, "<free port>")))
        return 0
    filler = args.context_file.read_text(encoding="utf-8") if args.context_file else FILLER
    report: dict = {
        "label": args.label,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "machine": {
            "platform": platform.platform(), "processor": platform.processor(),
            "logical_cpus": os.cpu_count(), "total_ram_bytes": total_ram_bytes(),
        },
        "settings": {
            "threads": args.threads, "prompt_tokens": args.prompt_tokens,
            "gen_tokens": args.gen_tokens, "repeats": args.repeats, "warmup_runs": 1, "cache_prompt": False,
        },
        "configs": [],
    }
    if args.server_url:
        base_url = args.server_url.rstrip("/")
        wait_until_ready(base_url, None, args.load_timeout)
        server = {**run_answers(base_url, args, filler), "peak_memory_bytes": None}
        report["configs"].append({"model": base_url, "ngl": -1, "mmap": None, "server": server})
    else:
        for model in args.model:
            if not model.is_file():
                raise SystemExit(f"not found: {model}")
            for ngl in args.ngl:
                for index, mmap in enumerate(mmap_modes):
                    print(f"== {model.name}  ngl={ngl}  mmap={'on' if mmap else 'off'}", flush=True)
                    config: dict = {
                        "model": model.name, "model_bytes": model.stat().st_size, "ngl": ngl, "mmap": mmap,
                    }
                    if index == 0 and not args.skip_llama_bench:
                        config["llama_bench"] = run_llama_bench(bench_command(args, model, ngl))
                    config["server"] = run_server_config(args, model, ngl, mmap, filler)
                    report["configs"].append(config)
                    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print_summary(report)
    print(f"\nreport: {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
