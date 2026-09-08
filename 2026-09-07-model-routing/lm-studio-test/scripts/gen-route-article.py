import json, urllib.request, time, os, sys

opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

# 6 панелей: Джилл разруливает задачи (диспетчерская тема статьи model-routing)
panels = [
    {"n": 1, "title": "Входящие задачи",
     "prompt": "young woman bartender, purple hair in two round buns, white shirt, black vest, tired kind eyes, standing behind a futuristic bar counter that looks like a server terminal, three glowing monitors showing incoming task cards and queue lists, cyberpunk bar interior, neon purple and cyan lights, bottles with glowing labels, focused expression, anime style"},
    {"n": 2, "title": "Сортировка: quick / free / deep / architect",
     "prompt": "young woman bartender, purple hair in two round buns, white shirt, black vest, tired kind eyes, sorting colorful cocktail glasses into four groups on the counter, each group glowing different color: green, cyan, orange, magenta, labels floating above groups, decisive gesture, cyberpunk bar, neon lights, anime style"},
    {"n": 3, "title": "Шейкер делегации",
     "prompt": "young woman bartender, purple hair in two round buns, white shirt, black vest, tired kind eyes, energetically shaking a glowing cocktail shaker with both hands, sparkles and data streams flying around, motion blur on shaker, confident smirk, cyberpunk bar counter with monitors, neon purple lighting, anime style"},
    {"n": 4, "title": "Подача результата",
     "prompt": "young woman bartender, purple hair in two round buns, white shirt, black vest, tired kind eyes, sliding a glowing cocktail glass across the counter to a satisfied client sitting at the bar, the glass emits soft golden light with a small report hologram above it, warm atmosphere, cyberpunk bar, anime style"},
    {"n": 5, "title": "Экономия токенов",
     "prompt": "young woman bartender, purple hair in two round buns, white shirt, black vest, tired kind eyes, pointing at a holographic scoreboard above the bar showing a large saved budget counter and falling cost graph, proud smile, arms crossed, cyberpunk bar interior with neon signs, anime style"},
    {"n": 6, "title": "Смена закрыта",
     "prompt": "young woman bartender, purple hair in two round buns, white shirt with rolled sleeves, black vest loosened, tired kind eyes with satisfied smile, leaning on the clean bar counter, two small dogs sitting near her feet, dimmed neon lights, closing time atmosphere, warm and cozy, cyberpunk bar, anime style"},
]

def gen(prompt, seed, prefix):
    api = {
      "1": {"class_type": "LLaDAImageLoader", "inputs": {
            "diffusion_model": "LLaDA-Image-Turbo-INT8.safetensors",
            "text_encoder": "LLaDA-Image-Turbo-text_encoder-Q4_K_M.gguf",
            "vae": "LLaDa_VAE.safetensors",
            "dtype": "bfloat16", "offload": "cuda", "vae_tiling": "On"}},
      "3": {"class_type": "LLaDAImageTextToImage", "inputs": {
            "pipeline": ["1", 0], "prompt": prompt,
            "width": 896, "height": 672, "steps": 8, "guidance_scale": 2.0,
            "seed": seed, "negative_prompt": "text, letters, words, watermark, deformed hands, extra fingers"}},
      "4": {"class_type": "SaveImage", "inputs": {"images": ["3", 0], "filename_prefix": prefix}},
    }
    req = urllib.request.Request("http://127.0.0.1:8188/prompt",
        data=json.dumps({"prompt": api}).encode(), headers={"Content-Type": "application/json"})
    pid = json.loads(opener.open(req, timeout=60).read())["prompt_id"]
    while True:
        h = json.loads(opener.open(f"http://127.0.0.1:8188/history/{pid}", timeout=10).read())
        if h != {}:
            return
        time.sleep(5)

t0 = time.time()
for p in panels:
    out = rf"C:\Work\Assist\comfyui\app\output\jill_route_{p['n']:02d}_00001_.png"
    if os.path.exists(out):
        print(f"panel {p['n']} exists, skip")
        continue
    gen(p["prompt"], 7700 + p["n"] * 11, f"jill_route_{p['n']:02d}")
    el = time.time() - t0
    print(f"panel {p['n']} done @ {el:.0f}s", flush=True)
print("JILL_ROUTE_DONE")
