"""Offline exercise for file 09: watch GeminiLLM retry / fall back with scripted failures. No network, no API key.

Run from the worktree root:
    set PYTHONPATH=src;.        (PowerShell: $env:PYTHONPATH = "src;.")
    .venv\Scripts\python.exe learning/_tools/exercises/llm_retry_scenarios.py

It builds a fake client whose `generate_content` raises the scripted errors in order (from tests/fakes.py), fixes the
jitter at 0.5 s, replaces `sleep` with a recorder, and prints: models called, seconds "slept", and the outcome.
"""
import os
from dataclasses import replace
from types import SimpleNamespace

for name in list(os.environ):  # make the run independent of the caller's environment (values are never printed)
    if name.startswith(("ANSWER", "FALLBACK", "ALLOW")):
        del os.environ[name]

from knowledge_assistant.config import get_answer_settings  # noqa: E402
from knowledge_assistant.core.interfaces.llm import LLMRequest  # noqa: E402
from knowledge_assistant.infrastructure.llm.gemini.gemini_llm import GeminiLLM  # noqa: E402
from tests.fakes import api_error  # noqa: E402

DAILY = "GenerateRequestsPerDayPerProjectPerModel-FreeTier"


class NoThrottle:
    def acquire(self, tokens, requests=1):
        return 0.0


class Models:
    def __init__(self, script):
        self.script, self.calls = list(script), []

    def generate_content(self, *, model, contents, config):
        self.calls.append(model)
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return SimpleNamespace(
            text=item,
            candidates=[SimpleNamespace(finish_reason=SimpleNamespace(name="STOP"))],
            usage_metadata=SimpleNamespace(prompt_token_count=10, candidates_token_count=5, thoughts_token_count=None),
        )


def run(label, script, allow_fallback=True):
    models, slept = Models(script), []
    settings = replace(get_answer_settings(), allow_fallback=allow_fallback)
    llm = GeminiLLM(
        settings, client=SimpleNamespace(models=models), sleep=slept.append, jitter=lambda: 0.5,
        clock=lambda: 0.0, throttles={settings.model: NoThrottle(), settings.fallback_model: NoThrottle()},
    )
    try:
        response = llm.generate(LLMRequest("question"))
        outcome = (response.model_used, f"retries={response.retry_count}", f"fallback={response.fallback_used}")
    except Exception as error:  # noqa: BLE001 - this is a demo script
        outcome = (type(error).__name__, getattr(error, "kind", None))
    print(f"{label:<44} calls={models.calls} slept={slept} -> {outcome}")


if __name__ == "__main__":
    run("A) 503, 503, then success", [api_error(503), api_error(503), '{"ok": 1}'])
    run("B) 503 x3, fallback succeeds", [api_error(503)] * 3 + ['{"ok": 1}'])
    run("C) 503 x3, fallback also 503", [api_error(503)] * 4)
    run("D) daily-quota 429, fallback succeeds", [api_error(429, quota_id=DAILY), '{"ok": 1}'])
    run("E) 400 bad request", [api_error(400)])
    run("F) 503 x3, fallback OFF (evaluation mode)", [api_error(503)] * 3, allow_fallback=False)
    run("G) 429 (per-minute) x3, fallback succeeds", [api_error(429)] * 3 + ['{"ok": 1}'])
