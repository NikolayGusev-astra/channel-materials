"""
TypeSafe Jev (System One) client: typed judgments instead of chat-LLM calls.

API: POST https://api.typesafe.ai/v1/systemone, Bearer auth.
Pricing (2026-09-20, docs.typesafe.ai): $0.042 / 1M input tokens, output free,
1200 req/min. Pin the model version (jev-1.13.0), calibrate thresholds per version.

Usage:
    from jev_client import jev_triage, jev_ask
    results = jev_triage([("src", "headline"), ...])
"""
import json, os, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

API_URL = "https://api.typesafe.ai/v1/systemone"
MODEL = "jev-1.13.0"
MAX_WORKERS = 10
TIMEOUT = 40
RETRY_STATUSES = {429, 529}
CONFIDENCE_GATE = 0.5


def _load_key() -> str:
    key = os.getenv("TYPESAFE_API_KEY", "")
    if key:
        return key.strip()
    p = Path(os.getenv("TYPESAFE_KEY_FILE", "typesafe-apikey.txt"))
    if p.exists():
        lines = [l.strip() for l in p.read_text(encoding="utf-8").splitlines()
                 if l.strip() and not l.strip().startswith("#")]
        if lines:
            return lines[0]
    raise RuntimeError("TYPESAFE_API_KEY not found")


def _post(payload: Dict[str, Any], key: str, retries: int = 3) -> Dict[str, Any]:
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    delay = 1.0
    last = None
    for _ in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            if e.code in RETRY_STATUSES:
                last = e; time.sleep(delay); delay *= 2; continue
            raise
        except Exception as e:
            last = e; time.sleep(delay); delay *= 2
    raise RuntimeError(f"typesafe: retries exhausted: {last}")


def jev_ask(state: Any, questions: Dict[str, Dict[str, Any]], model: str = MODEL) -> Dict[str, Any]:
    return _post({"state": state, "model": model, "questions": questions}, _load_key())


def jev_batch(items, questions, state_builder=None, max_workers: int = MAX_WORKERS):
    key = _load_key()
    def one(item):
        return _post({"state": state_builder(item) if state_builder else item,
                      "model": MODEL, "questions": questions}, key)
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        return list(ex.map(one, items))


TRIAGE_QUESTIONS = {
    "triage": {"type": "choice",
        "instructions": ("A Russian financial trading system triages news headlines before "
                         "they can affect its stock watchlist. Classify this headline for a "
                         "Russian equity (MOEX) trading context."),
        "criteria": {
            "tradable": "Could move a specific Russian stock or sector in the next days",
            "already_priced": "Market-moving topic but clearly old, no new facts",
            "noise": "No trading relevance for Russian equities"}}}


def jev_triage(headlines, confidence_gate: float = CONFIDENCE_GATE, max_workers: int = MAX_WORKERS):
    def build(item): return {"source": item[0], "headline": item[1]}
    raw = jev_batch(headlines, TRIAGE_QUESTIONS, state_builder=build, max_workers=max_workers)
    out = []
    for (src, text), resp in zip(headlines, raw):
        a = resp["answers"]["triage"]
        out.append({"source": src, "headline": text, "choice": a["choice"],
                    "confidence": a["confidence"], "probabilities": a["probabilities"],
                    "escalate": a["confidence"] < confidence_gate,
                    "input_tokens": resp.get("usage", {}).get("input_tokens", 0)})
    return out
