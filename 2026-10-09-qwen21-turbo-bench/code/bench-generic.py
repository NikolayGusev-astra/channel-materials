"""Бенчмарк диффузионной модели в ComfyUI через HTTP API.

Что делает: гоняет одинаковую сцену на N чекпойнтах с одинаковыми зернами,
меряет время исполнения по таймстампам ComfyUI (не по настенным часам) и
складывает результаты в JSON рядом со скриптом.

Что заменить под себя:
  - MODELS: список (имя_файла, класс_лоадера, число_шагов). Лоадер зависит от
    формата весов: UNETLoader для safetensors, UnetLoaderGGUF для gguf
    (нужен custom node ComfyUI-GGUF).
  - CORE + SCENES: свой канон персонажа и свои сцены. Держите хотя бы одну
    сцену с крупным текстом и одну с руками: это самые дешевые индикаторы
    деградации кванта.
  - SEEDS: свежие числа, не из прошлых прогонов. ComfyUI кэширует выполнения
    по промпту+зерну: повторный запрос вернет старую картинку за секунды.
  - CLIP, VAE: свои текстовый энкодер и декодер (для Qwen-Image это
    qwen3vl-энкодер и WanVAE; для SDXL - clip_l+clip_g и sdxl-vae и т.д.).

Грабли, зашитые в код:
  - unload() после КАЖДОГО кадра. Без этого веса остаются в памяти между
    кадрами: GGUF держит mmap файла плюс распакованные копии, и второй-третий
    кадр падает с DefaultCPUAllocator на декодере, а сервер умирает молча.
  - free_vram=False всегда. Значение True на Windows с драйвером WDDM течет:
    каждый цикл выгрузки оставляет мусор в памяти хоста.
  - warmup() перед каждой моделью: первый кадр после загрузки весов всегда
    медленнее (инициализация ядер), он портит среднюю.

Запуск: python bench-generic.py
Результат: bench-generic.json + картинки в output/<prefix>/
"""
import json
import os
import sys
import time
import urllib.request

HOST = "http://127.0.0.1:8188"

# --- под себя -----------------------------------------------------------
MODELS = [
    # (имя_файла_в_models/, класс_лоадера, шаги)
    ("model_base.safetensors",   "UNETLoader",     25),
    ("model_turbo.safetensors",  "UNETLoader",      8),
    ("model_turbo_Q4.gguf",      "UnetLoaderGGUF",  8),
]
CLIP = "text_encoder.safetensors"
VAE  = "vae.safetensors"
CLIP_TYPE = "qwen_image"   # для SDXL - "sdxl", для Flux - "flux" и т.д.
SIZE = 1024
SEEDS = [9101, 9102]       # свежие числа!
PREFIX = "bench"

CORE = ("опишите канон вашего персонажа или тему: причесна, одежда, "
        "характерные детали - этот кусок копируется вербатимом во все сцены")
SCENES = [
    ("poster", 'a poster with large clean text "SAMPLE TEXT" at the top, cinematic photo'),
    ("hands",  "sitting at a table holding a coffee mug with both hands, warm light"),
]
# -------------------------------------------------------------------------


def opener():
    # пустой ProxyHandler, чтобы не подхватить env-прокси на localhost
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


OP = opener()


def get(path, timeout=30):
    with OP.open(HOST + path, timeout=timeout) as r:
        return json.load(r)


def post(path, obj, timeout=60):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(HOST + path, data=data,
                                 headers={"Content-Type": "application/json"})
    with OP.open(req, timeout=timeout) as r:
        return r.status, json.load(r)


def unload():
    """Выгрузить веса из памяти после кадра. Обязательно.

    free_vram=False: значение True на Windows+WDDM течет, см. докстринг модуля.
    """
    body = json.dumps({"free_memory": True, "free_models": True,
                       "unload_models": True, "free_vram": False}).encode()
    req = urllib.request.Request(HOST + "/free", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with OP.open(req, timeout=60) as r:
            return r.status
    except Exception as e:
        print("unload failed:", e, flush=True)
        return None


def loader_node(model_file, loader):
    if loader == "UnetLoaderGGUF":
        return {"class_type": loader, "inputs": {"unet_name": model_file}}
    return {"class_type": loader, "inputs": {"unet_name": model_file}}


def build_wf(model_file, loader, steps, prompt, seed, prefix):
    return {
        "1": loader_node(model_file, loader),
        "3": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": CLIP, "type": CLIP_TYPE, "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "6": {"class_type": "TextEncodeQwenImage21",   # под свою модель: CLIPTextEncode и т.п.
              "inputs": {"clip": ["3", 0], "prompt": prompt,
                         "negative_prompt": "", "resolution": SIZE}},
        "9": {"class_type": "EmptyLatentImage",
              "inputs": {"width": SIZE, "height": SIZE, "batch_size": 1}},
        "6b": {"class_type": "KSampler",
               "inputs": {"model": ["1", 0], "positive": ["6", 0],
                          "negative": ["6", 1], "latent_image": ["9", 0],
                          "seed": seed, "steps": steps, "cfg": 1.0,
                          "sampler_name": "euler", "scheduler": "simple",
                          "denoise": 1.0}},
        "13": {"class_type": "VAEDecode",
               "inputs": {"samples": ["6b", 0], "vae": ["4", 0]}},
        "14": {"class_type": "SaveImage",
               "inputs": {"images": ["13", 0], "filename_prefix": prefix}},
    }


def exec_seconds(entry):
    """Время исполнения из таймстампов ComfyUI (в мс), без загрузки весов."""
    start = end = None
    for kind, payload in entry.get("status", {}).get("messages", []) or []:
        ts = (payload or {}).get("timestamp")
        if not ts:
            continue
        if kind == "execution_start":
            start = ts
        elif kind in ("execution_success", "execution_error", "execution_interrupted"):
            end = ts
    if start and end:
        return round((end - start) / 1000.0, 1)
    return None


def wait(pid, timeout=2400):
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = get("/history/" + pid)
        if pid in h:
            e = h[pid]
            imgs = []
            for o in e.get("outputs", {}).values():
                imgs += o.get("images", [])
            return {"wall": round(time.time() - t0, 1), "exec": exec_seconds(e),
                    "status": e.get("status", {}).get("status_str"),
                    "images": [i["filename"] for i in imgs]}
        time.sleep(4)
    return None


def warmup(model_file, loader, steps, tag):
    """Прогрев: маленький быстрый кадр, в замер не идет."""
    wf = build_wf(model_file, loader, steps, "warmup", 99999, f"{PREFIX}/{tag}/_warm")
    for n in wf.values():
        if n["class_type"] == "EmptyLatentImage":
            n["inputs"].update({"width": 512, "height": 512})
        if n["class_type"] == "KSampler":
            n["inputs"]["steps"] = 4
    st, r = post("/prompt", {"prompt": wf, "client_id": "bench"})
    if st == 200:
        wait(r["prompt_id"], timeout=1800)
    time.sleep(3)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(here, "bench-generic.json")
    results = []
    for model_file, loader, steps in MODELS:
        tag = os.path.splitext(model_file)[0]
        print(f"===== {tag} ({steps} steps) =====", flush=True)
        unload()
        time.sleep(6)
        warmup(model_file, loader, steps, tag)
        for seed in SEEDS:
            for name, scene in SCENES:
                prompt = f"{CORE}, {scene}"
                prefix = f"{PREFIX}/{tag}/{name}-s{seed}"
                wf = build_wf(model_file, loader, steps, prompt, seed, prefix)
                st, r = post("/prompt", {"prompt": wf, "client_id": "bench"})
                if st != 200:
                    print(f"[{tag} {name} s{seed}] QUEUE FAIL {st}", flush=True)
                    results.append({"model": tag, "scene": name, "seed": seed,
                                    "status": f"queue_fail_{st}"})
                    continue
                d = wait(r["prompt_id"])
                if not d:
                    print(f"[{tag} {name} s{seed}] TIMEOUT", flush=True)
                    results.append({"model": tag, "scene": name, "seed": seed,
                                    "status": "timeout"})
                    unload()
                    continue
                unload()
                time.sleep(4)
                rec = {"model": tag, "steps": steps, "scene": name, "seed": seed,
                       "wall_s": d["wall"], "exec_s": d["exec"], "status": d["status"],
                       "images": d["images"]}
                results.append(rec)
                print(f"[{tag} {name} s{seed}] exec={d['exec']}s {d['status']}", flush=True)
                json.dump(results, open(out_path, "w", encoding="utf-8"),
                          indent=2, ensure_ascii=False)

    print("\nWROTE", out_path, flush=True)
    ok = [r for r in results if r.get("status") == "success"]
    by_model = {}
    for r in ok:
        by_model.setdefault(r["model"], []).append(r["exec_s"])
    for model, xs in by_model.items():
        print(f"  {model}: n={len(xs)} mean={sum(xs)/len(xs):.1f}s "
              f"min={min(xs):.1f} max={max(xs):.1f}", flush=True)


if __name__ == "__main__":
    main()
