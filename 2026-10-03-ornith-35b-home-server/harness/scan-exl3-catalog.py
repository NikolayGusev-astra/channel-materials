# -*- coding: utf-8 -*-
# Сканер EXL3-каталога HuggingFace: кодбук / архитектура / параметры для живых релизов.
# Использование: python scan-exl3-catalog.py [--min-downloads 100] [--top 250] [--out scan.json]
# Зависимости: curl в PATH. Результат: JSON {repo: {codebook, bits, arch, moe, total_params, downloads}}
import subprocess, json, os, argparse, re
from concurrent.futures import ThreadPoolExecutor, as_completed

def hf(url):
    r = subprocess.run(["curl", "-sL", "--max-time", "30", url], capture_output=True, text=True, timeout=40)
    return json.loads(r.stdout)

def fetch_qc(repo):
    try:
        r = subprocess.run(["curl", "-sL", "--max-time", "20",
                            f"https://huggingface.co/{repo}/resolve/main/quantization_config.json",
                            "-r", "0-4000"], capture_output=True, text=True, timeout=30)
        raw = r.stdout
        cb = re.search(r'"codebook"\s*:\s*"([^"]+)"', raw)
        bits = re.search(r'"bits"\s*:\s*([\d.]+)', raw)
        ver = re.search(r'"version"\s*:\s*"([^"]+)"', raw)
        return repo, {"codebook": cb.group(1) if cb else None,
                      "bits": float(bits.group(1)) if bits else None,
                      "format": ver.group(1) if ver else None}
    except Exception as e:
        return repo, {"codebook": None, "bits": None, "format": None, "err": str(e)[:80]}

def fetch_meta(repo):
    try:
        r = subprocess.run(["curl", "-sL", "--max-time", "20",
                            f"https://huggingface.co/{repo}/resolve/main/config.json",
                            "-r", "0-6000"], capture_output=True, text=True, timeout=30)
        c = json.loads(r.stdout)
        tc = c.get("text_config", c)
        arch = c.get("architectures", ["?"])[0]
        ne = tc.get("num_experts")
        return repo, {"arch": arch, "moe": ne is not None and ne > 1,
                      "experts": ne, "active": tc.get("num_experts_per_tok")}
    except Exception as e:
        return repo, {"err": str(e)[:80]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-downloads", type=int, default=100)
    ap.add_argument("--top", type=int, default=250)
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--out", default="exl3-scan.json")
    args = ap.parse_args()

    models = hf("https://huggingface.co/api/models?search=exl3&limit=1000&sort=downloads&direction=-1")
    live = [m for m in models if (m.get("downloads") or 0) >= args.min_downloads]
    live.sort(key=lambda m: -(m.get("downloads") or 0))
    targets = [m["modelId"] for m in live[:args.top]]
    print(f"к сканированию: {len(targets)} репозиториев")

    qc, meta = {}, {}
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(fetch_qc, r): r for r in targets}
        for i, f in enumerate(as_completed(futs)):
            repo, info = f.result(); qc[repo] = info
            if (i + 1) % 50 == 0: print(f"qc {i+1}/{len(targets)}")
        futs = {ex.submit(fetch_meta, r): r for r in targets}
        for i, f in enumerate(as_completed(futs)):
            repo, info = f.result(); meta[repo] = info
            if (i + 1) % 50 == 0: print(f"meta {i+1}/{len(targets)}")

    dl = {m["modelId"]: m.get("downloads") or 0 for m in models}
    out = {}
    for repo in targets:
        out[repo] = {**qc[repo], **meta[repo], "downloads": dl.get(repo, 0)}

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    cb = {}
    for v in out.values():
        k = v.get("codebook") or "(none)"
        cb[k] = cb.get(k, 0) + 1
    print("кодбуки:", cb)
    print("сохранено:", args.out)

if __name__ == "__main__":
    main()
