"""Разовая генерация картинки через ComfyUI: шаблон workflow + ожидание результата.

Это минимальный клиент, с которого проще всего собрать свой пайп: подставьте
свою модель, энкодер и декодер в build_wf, свой промпт в main - и запускайте.
Выгрузка весов в конце уже зашита.

Запуск: python submit-generic.py
"""
import json
import time
import urllib.request

HOST = "http://127.0.0.1:8188"

OP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


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
    """Выгрузить веса после работы. free_vram=False: True течет на Windows+WDDM."""
    body = json.dumps({"free_memory": True, "free_models": True,
                       "unload_models": True, "free_vram": False}).encode()
    req = urllib.request.Request(HOST + "/free", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with OP.open(req, timeout=60) as r:
            print("unload:", r.status, flush=True)
    except Exception as e:
        print("unload failed:", e, flush=True)


def build_wf(prompt, seed):
    # --- под себя: имена файлов из ComfyUI/models и классы нод своей модели ---
    return {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": "model_turbo.safetensors", "weight_dtype": "default"}},
        "3": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": "text_encoder.safetensors",
                         "type": "qwen_image", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": "vae.safetensors"}},
        "6": {"class_type": "TextEncodeQwenImage21",
              "inputs": {"clip": ["3", 0], "prompt": prompt,
                         "negative_prompt": "", "resolution": 1024}},
        "9": {"class_type": "EmptyLatentImage",
              "inputs": {"width": 1024, "height": 1024, "batch_size": 1}},
        "6b": {"class_type": "KSampler",
               "inputs": {"model": ["1", 0], "positive": ["6", 0],
                          "negative": ["6", 1], "latent_image": ["9", 0],
                          "seed": seed, "steps": 8, "cfg": 1.0,
                          "sampler_name": "euler", "scheduler": "simple",
                          "denoise": 1.0}},
        "13": {"class_type": "VAEDecode",
               "inputs": {"samples": ["6b", 0], "vae": ["4", 0]}},
        "14": {"class_type": "SaveImage",
               "inputs": {"images": ["13", 0], "filename_prefix": "my-pipe/out"}},
    }


def main():
    prompt = "ваш промпт здесь, канон персонажа или сцена"
    seed = 9101  # свежее число: повторный seed возвращает закешированный кадр

    q = get("/queue")
    if q.get("queue_running") or q.get("queue_pending"):
        raise SystemExit("очередь занята, дождитесь окончания текущих задач")

    st, r = post("/prompt", {"prompt": build_wf(prompt, seed), "client_id": "my-pipe"})
    if st != 200:
        raise SystemExit("submit failed: " + json.dumps(r)[:500])
    pid = r["prompt_id"]
    print("submitted", pid, flush=True)

    t0 = time.time()
    while True:
        time.sleep(5)
        h = get(f"/history/{pid}")
        if pid not in h:
            print(f"waiting... {time.time()-t0:.0f}s", flush=True)
            continue
        e = h[pid]
        print(f"done in {time.time()-t0:.0f}s status={e.get('status', {}).get('status_str')}")
        for o in e.get("outputs", {}).values():
            for img in o.get("images", []):
                print("IMAGE:", img["subfolder"] + "/" + img["filename"])
        unload()
        break
    # таймаут по вкусу: в проде ставьте предел и падайте, а не ждите вечно


if __name__ == "__main__":
    main()
