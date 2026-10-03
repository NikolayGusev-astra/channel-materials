# -*- coding: utf-8 -*-
# bench3: Ornith 4bpw, по-токенный тайминг. Один прогон, видно фазы и реальную скорость.
import os, time, json, argparse

from exllamav3 import Model, Cache, Generator, Tokenizer
from exllamav3.architecture.qwen3_5 import Qwen3_5VLMoeConfig
from exllamav3.generator import Job

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", "Ornith-1.5-35B-A3B-EXL3-4bpw")
PROMPT = "Назови пять планет солнечной системы, по одному слову на планету."

ap = argparse.ArgumentParser()
ap.add_argument("--mcl", type=int, default=40)
ap.add_argument("--max-new", type=int, default=64)
args = ap.parse_args()

if args.mcl:
    os.environ["EXL3_MOE_CPU_OFFLOAD"] = str(args.mcl)

events = []
t0 = time.perf_counter()
def mark(label):
    events.append({"t": round(time.perf_counter() - t0, 2), "label": label})

mark("start")
config = Qwen3_5VLMoeConfig(MODEL_DIR)
model = Model.from_config(config)
cache = Cache(model, max_num_tokens=4096)
mark("cache_created")

for _ in model.load_gen(max_chunk_size=2048, use_per_device=5.0):
    pass
mark("model_loaded")

tokenizer = Tokenizer(config)
gen = Generator(model, cache, tokenizer)
mark("generator_ready")

input_ids = tokenizer.encode(PROMPT, add_bos=True)
job = Job(input_ids=input_ids, max_new_tokens=args.max_new,
          min_new_tokens=args.max_new, decode_special_tokens=True)
gen.enqueue(job)
mark("enqueued")

n_out = 0
texts = []
error = None
while n_out < args.max_new:
    results = gen.iterate()
    if not results:
        continue
    for r in results:
        if r.get("stage") == "error":
            error = str(r.get("error"))[:200]
            mark("ERROR")
            n_out = args.max_new
            break
        if r.get("eos"):
            mark("eos_early")
            n_out = args.max_new
            break
        texts.append(r.get("text", ""))
        n_out += 1
        if n_out in (1, 2, 4, 8, 16, 32, 64):
            mark(f"token_{n_out}")
        if n_out >= args.max_new:
            break

mark("done")
dt_gen = events[-1]["t"] - next(e["t"] for e in events if e["label"] == "first_iter_start")

out = {
    "mcl": args.mcl, "max_new": args.max_new,
    "prompt_tokens": int(input_ids.shape[-1]),
    "generated": n_out, "error": error,
    "gen_wall_s": round(dt_gen, 2),
    "tok_per_s": round(n_out / dt_gen, 2) if dt_gen > 0 and n_out > 1 else 0,
    "text_sample": "".join(texts)[:120],
    "events": events,
}
print(json.dumps(out, ensure_ascii=False, indent=1))
with open("bench3_result.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
