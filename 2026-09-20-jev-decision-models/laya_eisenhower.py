"""
Laya (convaiinnovations/laya, Apache 2.0) - open System One decision model.
Eisenhower matrix over incoming messages: two noul questions per item, one call.

Calibration: Platt scaling (2 params) fitted on YOUR golden labels.
Laya ships over-confident - refit on your data before trusting probabilities.

Usage:
    import laya
    agent = laya.load("convaiinnovations/laya", subfolder="multilingual")
    results = eisenhower(agent, [{"subject": ..., "body_snippet": ...}, ...])
"""
import json, math, time
from concurrent.futures import ThreadPoolExecutor

QUESTIONS = {
    "urgent": {"type": "noul",
        "instructions": ("Does this message require a reaction within the next few hours (today)? "
                         "A time-limited code, a payment, an order, or a failing service the owner "
                         "must fix today count as urgent. Newsletters and automated digests are not.")},
    "important": {"type": "noul",
        "instructions": ("Is this message materially important: does it affect income, obligations, "
                         "health, family, or key personal infrastructure? Automated CI/test "
                         "notifications from hobby projects and marketing are not.")}
}


def _logit(p):
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.log(p / (1 - p))


def fit_platt(ps, ys, iters: int = 200, lr: float = 0.1):
    """Fit Platt scaling on golden labels: returns (a, b). Needs 300+ labels for stability."""
    import numpy as np
    a, b = 1.0, 0.0
    X = np.array([_logit(p) for p in ps]); Y = np.array(ys, dtype=float)
    for _ in range(iters):
        z = a * X + b; pr = 1 / (1 + np.exp(-z))
        a -= lr * float(np.mean((pr - Y) * X)); b -= lr * float(np.mean(pr - Y))
    return a, b


def ece(ps, ys, bins: int = 10) -> float:
    """Expected Calibration Error: lower is better, 0 = perfectly calibrated."""
    tot = len(ps); e = 0.0
    for i in range(bins):
        lo, hi = i / bins, (i + 1) / bins
        sel = [(p, y) for p, y in zip(ps, ys) if lo <= max(p, 1 - p) < hi]
        if not sel: continue
        conf = sum(max(p, 1 - p) for p, _ in sel) / len(sel)
        acc = sum((p > 0.5) == bool(y) for p, y in sel) / len(sel)
        e += len(sel) / tot * abs(conf - acc)
    return e


def _cal(a: float, b: float, p: float) -> float:
    return 1 / (1 + math.exp(-(a * _logit(p) + b)))


def quadrant(u: float, i: float, thr: float = 0.7, fuzzy: float = 0.12) -> str:
    """4 Eisenhower quadrants + 5th zone 'ask a human' for mid-probability cases."""
    if abs(u - 0.5) < fuzzy or abs(i - 0.5) < fuzzy: return "ask_human"
    if u >= thr and i >= thr: return "Q1_do_now"
    if u < thr and i >= thr:  return "Q2_schedule"
    if u >= thr:              return "Q3_urgent_not_important"
    return "Q4_trash"


def eisenhower(agent, states, a: float = 1.0, b: float = 0.0,
               max_workers: int = 8, progress=False):
    """states: list of dicts (any text fields). Returns list of {u, i, quadrant}."""
    def one(m):
        r = agent.predict(m, QUESTIONS)
        u = r["answers"]["urgent"]["noul"]; i = r["answers"]["important"]["noul"]
        return {"u": _cal(a, b, u), "i": _cal(a, b, i)}
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        res = list(ex.map(one, states))
    wall = time.time() - t0
    for r in res: r["quadrant"] = quadrant(r["u"], r["i"])
    if progress: print(f"{len(states)} items in {wall:.1f}s")
    return res
