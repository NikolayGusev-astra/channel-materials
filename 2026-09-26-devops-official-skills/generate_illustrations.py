"""Generate article illustrations for devops-official-skills via Qwen-Image-2.1 + Jill canon.

Fire-and-forget: submits all jobs, ComfyUI queues them.
"""
import json
import os
import urllib.request

for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(k, None)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE = "http://127.0.0.1:8188"

CORE = ("young woman bartender, purple hair in two round buns, white shirt, "
        "black vest, tired kind eyes")

SCENES = [
    ("vendor-shelves", f'{CORE}, standing in a dim storage room before tall shelves filled '
     f'with labeled cardboard boxes of documents, holding a small flashlight, inspecting a '
     f'single box taken from the shelf, focused tired expression, cool blue lab lighting '
     f'with warm lamp accent, anime style, no text no letters no signs'),
    ("empty-kubernetes", f'{CORE}, sitting at a bare desk facing a completely dark blank '
     f'screen, one hand resting on an empty cardboard box with no label, shoulders slightly '
     f'slumped, disappointed but calm expression, dim room lit only by the monitor glow, '
     f'blank screen, no text no letters no signs, anime style'),
    ("own-toolbox", f'{CORE}, at a well-used workbench writing notes on a clipboard next to '
     f'her own handwritten notebooks, sticky notes on a board behind her, wrench and '
     f'terminal cable on the bench, warm afternoon light through a window, anime style, '
     f'no text no letters no signs'),
    ("grabla-mismatch", f'{CORE}, holding two almost identical name tags, squinting at them '
     f'closely, puzzled frown, one name tag slightly out of focus, dim desk lamp light, '
     f'dark background, anime style, no text no letters no signs'),
    ("dispatcher-desk", f'{CORE}, standing before a wall of many small drawers with switches '
     f'and labels, calmly choosing one drawer with a marker in hand, warm workshop light, '
     f'cozy organized atmosphere, anime style, no text no letters no signs'),
]


def build(name, scene, seed):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {
            "unet_name": "qwen_image_2.1_int8_convrot.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {
            "clip_name": "qwen3vl_8b_w4a8.safetensors", "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
        "9": {"class_type": "LoadImage", "inputs": {"image": "ref_canon.png"}},
        "4": {"class_type": "TextEncodeQwenImage21", "inputs": {
            "clip": ["2", 0], "prompt": scene, "negative_prompt": "", "resolution": 1024,
            "images.image_1": ["9", 0], "vae": ["3", 0]}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["4", 0], "negative": ["4", 1],
            "latent_image": ["4", 2], "seed": seed, "steps": 25, "cfg": 1.0,
            "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "8": {"class_type": "SaveImage", "inputs": {
            "images": ["7", 0], "filename_prefix": f"devops-skills/art-{name}"}},
    }


q = json.load(opener.open(BASE + "/queue", timeout=10))
if q.get("queue_running") or q.get("queue_pending"):
    print("QUEUE BUSY - aborting to avoid mixing", flush=True)
    raise SystemExit(1)

for i, (name, scene) in enumerate(SCENES):
    req = urllib.request.Request(
        BASE + "/prompt",
        data=json.dumps({"prompt": build(name, scene, 7100 + i * 13),
                         "client_id": "rin-devops-skills"}).encode(),
        headers={"Content-Type": "application/json"})
    res = json.load(opener.open(req, timeout=60))
    print("queued", name, "->", res["prompt_id"], flush=True)
print("ALL SUBMITTED (5 jobs)", flush=True)
