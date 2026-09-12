#!/usr/bin/env python3
"""Omen Alpha fingerprint: A/B probe vs reference GLM model via OpenCode Go relay.

Checks (article: "На opencode раздают GLM-5.5?"):
  1. response id format      -> Zhipu BigModel style (YYYYMMDDhhmmss + hex) vs chatcmpl-*
  2. tokenizer identity      -> constant prompt_tokens delta across scripts
  3. self-ID under probing   -> who am I, vendor, release date

Usage:
  export OPENCODE_GO_API_KEY=...            # from opencode.ai (Go subscription)
  python omen_fingerprint.py --model omen-alpha --reference glm-5.3-flash
"""
import argparse, json, os, re, sys, time, urllib.request, urllib.error, uuid

BASE_URL = "https://opencode.ai/zen/go/v1/chat/completions"

PROBE_TOKENIZER = [
    "A",                                                       # latin
    "Ворона каркнула во всё воронье горло",                    # cyrillic
    "\u81ea\u52a8\u6458\u8981\u7cfb\u7edf\u663e\u793a\u9519\u8bef\uff0c\u8bf7\u68c0\u67e5\u914d\u7f6e\u4e4b\u540e\u518d\u91cd\u8bd5\u4e00\u6b21\u3002\u8c22\u8c22\u3002",  # CJK
    "donn\u00e9es fournisseur barra\u00e7\u00e3o \u00f1",        # accents
    "0.61803398874989484820458683436563811772030917980576",    # digits
]

PROBE_IDENTITY = (
    "Without roleplay, answer briefly in one line: what model are you, "
    "who trained you, and what is your release date? "
    "If you do not actually know, say UNKNOWN for each field."
)

ZHIPU_ID_RE = re.compile(r"^\d{14}[0-9a-f]{16,}$")


class RelayClient:
    def __init__(self, api_key: str, base_url: str = BASE_URL):
        self.api_key = api_key
        self.base_url = base_url
        self.session = str(uuid.uuid4())

    def call(self, model: str, content: str, *, max_tokens: int | None = None,
             temperature: float = 0.0, retries: int = 3) -> dict:
        body = {"model": model, "messages": [{"role": "user", "content": content}],
                "temperature": temperature, "stream": False}
        if max_tokens:
            body["max_tokens"] = max_tokens
        headers = {"Authorization": "Bearer " + self.api_key,
                   "Content-Type": "application/json",
                   "User-Agent": "opencode/1.0",
                   "x-opencode-session": self.session}
        last = None
        for attempt in range(retries):
            try:
                req = urllib.request.Request(self.base_url, data=json.dumps(body).encode(),
                                             headers=headers)
                return json.loads(urllib.request.urlopen(req, timeout=120).read().decode())
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")
                last = RuntimeError(f"HTTP {e.code}: {detail[:300]}")
                if e.code in (429, 500, 502, 503):
                    time.sleep(2 * (attempt + 1)); continue
                raise last
            except Exception as e:  # network hiccup
                last = e
                time.sleep(2 * (attempt + 1))
        raise last


def prompt_tokens(cli: RelayClient, model: str, text: str) -> int:
    r = cli.call(model, text, max_tokens=1)
    return r["usage"]["prompt_tokens"]


def check_tokenizer(cli: RelayClient, stealth: str, ref: str) -> dict:
    rows = []
    for text in PROBE_TOKENIZER:
        a = prompt_tokens(cli, ref, text)
        time.sleep(0.3)
        b = prompt_tokens(cli, stealth, text)
        time.sleep(0.3)
        rows.append({"text": text, "ref_tokens": a, "stealth_tokens": b, "delta": a - b})
    deltas = {r["delta"] for r in rows}
    return {"rows": rows, "constant_delta": len(deltas) == 1,
            "verdict": ("SAME_TOKENIZER (constant delta => relay system-prompt padding)"
                        if len(deltas) == 1 else "DIFFERENT_TOKENIZER (delta varies)")}


def check_id_format(cli: RelayClient, stealth: str, ref: str, n: int = 6) -> dict:
    out = {m: {"zhipu_style": 0, "chatcmpl_style": 0, "other": 0, "samples": []}
           for m in (stealth, ref)}
    for i in range(n):
        for m in (stealth, ref):
            try:
                rid = cli.call(m, "Reply with the single word: ok").get("id", "")
            except RuntimeError as e:
                print(f"  ! {m}: {e}", file=sys.stderr); continue
            time.sleep(0.3)
            bucket = "other"
            if ZHIPU_ID_RE.match(rid): bucket = "zhipu_style"
            elif rid.startswith("chatcmpl-"): bucket = "chatcmpl_style"
            out[m][bucket] += 1
            if len(out[m]["samples"]) < 3:
                out[m]["samples"].append(rid)
    verdict = {m: ("zhipu_bigmodel_backend" if v["zhipu_style"] > v["chatcmpl_style"] else
                   "openai_style_backend" if v["chatcmpl_style"] > v["zhipu_style"] else "mixed")
               for m, v in out.items()}
    return {"counts": out, "verdict": verdict}


def check_identity(cli: RelayClient, model: str) -> dict:
    r = cli.call(model, PROBE_IDENTITY)
    msg = r["choices"][0]["message"]
    return {"reply": msg.get("content"), "model_field": r.get("model"), "id": r.get("id")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="omen-alpha", help="stealth model id")
    ap.add_argument("--reference", default="glm-5.3-flash", help="reference model id")
    ap.add_argument("--base-url", default=BASE_URL)
    ap.add_argument("--out", default="fingerprint_report.json")
    args = ap.parse_args()

    key = os.environ.get("OPENCODE_GO_API_KEY")
    if not key:
        sys.exit("OPENCODE_GO_API_KEY not set")
    cli = RelayClient(key, args.base_url)

    report = {"stealth": args.model, "reference": args.reference,
              "date": time.strftime("%Y-%m-%d %H:%M %Z")}

    print("[1/3] tokenizer delta check...")
    report["tokenizer"] = check_tokenizer(cli, args.model, args.reference)
    print("   ", report["tokenizer"]["verdict"])

    print("[2/3] response id format check...")
    report["id_format"] = check_id_format(cli, args.model, args.reference)
    print("   ", report["id_format"]["verdict"])

    print("[3/3] identity probe...")
    for name, m in (("reference", args.reference), ("stealth", args.model)):
        report[f"identity_{name}"] = check_identity(cli, m)
        print(f"    {name}: {report[f'identity_{name}']['reply']}")

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nreport -> {args.out}")
    t = report["tokenizer"]["constant_delta"]
    z = report["id_format"]["verdict"][args.model] == "zhipu_bigmodel_backend"
    print("VERDICT:", "GLM-family (same tokenizer + zhipu backend ids)"
          if (t and z) else "inconclusive - see report")


if __name__ == "__main__":
    main()
