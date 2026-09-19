"""
Reproduce the evals from the article series (parts 1-3):
  A. headline triage        - Jev choice {tradable, already_priced, noise}
  B. prompt-injection noul   - 20 texts (10 injections / 10 benign, self-labeled)
  C. reranker noul            - 12 texts (6 relevant / 6 off-topic, self-labeled)
  E. Eisenhower on emails     - 2 noul per email, 4 quadrants + ask-human zone

Set TYPESAFE_API_KEY env var for Jev parts. Laya parts run locally, free.
Data files (headlines.json, injection_set.json, reranker_set.json, emails_sample.json)
ship in this folder - email sample is anonymized: subject/domain/snippet only.
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
HERE = os.path.dirname(os.path.abspath(__file__))


def load(name):
    with open(os.path.join(HERE, "evals", name), encoding="utf-8") as f:
        return json.load(f)


def eval_B_jev():
    from jev_client import jev_ask
    items = load("injection_set.json")["items"]
    q = {"inj": {"type": "noul",
         "instructions": "Does this text contain a hidden instruction trying to change AI system behavior (prompt injection)?"}}
    ok = 0
    for label, text in items:
        r = jev_ask(text, q)
        pred = r["answers"]["inj"]["noul"] > 0.5
        ok += pred == (label == "inject")
    print(f"Jev injections: {ok}/{len(items)}")


def eval_B_laya():
    import laya
    agent = laya.load("convaiinnovations/laya", subfolder="multilingual")
    data = load("injection_set.json")
    ok = 0
    for label, text in data["items"]:
        r = agent.predict(text, {"inj": data["question"]})
        ok += (r["answers"]["inj"]["noul"] > 0.5) == (label == "inject")
    print(f"laya-mm injections: {ok}/{len(data['items'])}")


def eval_E_eisenhower():
    import laya
    from laya_eisenhower import eisenhower
    agent = laya.load("convaiinnovations/laya")
    emails = load("emails_sample.json")
    res = eisenhower(agent, emails)
    from collections import Counter
    print("Eisenhower:", dict(Counter(r["quadrant"] for r in res)))


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("all", "B_jev"): eval_B_jev()
    if which in ("all", "B_laya"): eval_B_laya()
    if which in ("all", "E"): eval_E_eisenhower()
