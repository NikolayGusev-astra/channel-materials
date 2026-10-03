"""Обложка и внутренняя иллюстрация статьи про форматы объяснений.

Канон Джилл: ref_canon.png как images.image_1 для обоих кадров.
Обложка: у доски, азартно рисует схемы, поза человека из мема про теорию заговора.
Второй кадр: у монитора с анимацией формул, под статью про видео-формат.
"""
import json
import os
import urllib.request

for v in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(v, None)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE = "http://127.0.0.1:8188"

CORE = "young woman bartender, purple hair in two round buns, white shirt, black vest, tired kind eyes"

COVER = (
    CORE + ", standing at a large whiteboard completely covered with hand-drawn "
    "diagrams, boxes connected by arrows, timelines, flowcharts and circled nodes, "
    "she is frantically drawing a new arrow on the board with a red marker, "
    "mouth open in manic enthusiasm, one eye wide, conspiracy theorist energy, "
    "string of red yarn connecting pins on the board, marker in other hand, "
    "anime style, cel shaded, clean line art, dim room lit by the whiteboard glow, "
    "no text, no letters, no numbers, blank whiteboard surface"
)

VIDEO = (
    CORE + ", sitting in front of a large monitor showing a glowing blue sine wave "
    "curve on black background with a yellow dot travelling along it, she points at "
    "the curve with one hand and holds a half-empty coffee cup with the other, "
    "calm focused expression, night desk lighting, teal and yellow accents, "
    "anime style, cel shaded, clean line art, "
    "no text, no letters, no numbers, blank monitor bezel"
)

SCENES = [
    ("cover-formats", COVER, 778811),
    ("video-curve", VIDEO, 424242),
]


def build(name, prompt, seed):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_2.1_int8_convrot.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_8b_w4a8.safetensors", "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
        "9": {"class_type": "LoadImage", "inputs": {"image": "ref_canon.png"}},
        "4": {"class_type": "TextEncodeQwenImage21", "inputs": {
            "clip": ["2", 0], "prompt": prompt, "negative_prompt": "", "resolution": 1024,
            "images.image_1": ["9", 0], "vae": ["3", 0]}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["4", 0], "negative": ["4", 1],
            "latent_image": ["4", 2], "seed": seed, "steps": 25, "cfg": 1.0,
            "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": f"qwen21/art-{name}"}},
    }


q = json.load(opener.open(BASE + "/queue", timeout=10))
if q.get("queue_running") or q.get("queue_pending"):
    raise SystemExit("QUEUE BUSY - aborting to avoid mixing")

for name, prompt, seed in SCENES:
    req = urllib.request.Request(
        BASE + "/prompt",
        data=json.dumps({"prompt": build(name, prompt, seed), "client_id": "rin-explain-skills"}).encode(),
        headers={"Content-Type": "application/json"},
    )
    res = json.load(opener.open(req, timeout=60))
    print("queued", name, "->", res["prompt_id"], flush=True)
print("SUBMITTED: %d jobs, ~3 min each with one reference" % len(SCENES))
