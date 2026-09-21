"""Batch-generate 5 article illustrations with Jill mascot via Qwen-Image-2.1.

Uses the fixed canon (jill-canon-qwen21.png) as image_1 reference for every panel.
Fire-and-forget: submits all jobs, ComfyUI queues them.
"""
import json, os, urllib.request

os.environ.pop("HTTP_PROXY", None); os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None); os.environ.pop("https_proxy", None)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE = "http://127.0.0.1:8188"

CORE = ("young woman bartender, purple hair in two round buns, white shirt, black vest, tired kind eyes")

SCENES = [
    ("bonsai-bench", f'{CORE}, sitting at a workbench cluttered with server racks and benchmark graphs on monitors, holding a stopwatch, focused expression, dim tech-lab lighting with green terminal glow, anime style'),
    ("bonsai-fail", f'{CORE}, looking skeptically at a bonsai tree in a pot on the bar counter, one eyebrow raised, holding a wrench, deadpan tired face, dim bar with a single hanging lamp over the bonsai, anime style'),
    ("eisenhower-matrix", f'{CORE}, standing at a whiteboard divided into four quadrants with sticky notes, holding a marker, pointing at the top-right quadrant, confident smirk, office lighting, anime style'),
    ("jev-checkpoints", f'{CORE}, as a referee holding two small glowing model figurines on a balance scale, comparing them, one blue one orange, focused look, dark background with floating evaluation charts, anime style'),
    ("barts-letters", f'{CORE}, at the bar counter late at night reading a huge stack of handwritten letters, warm desk lamp light, cozy tired atmosphere, envelope scattered around, anime style'),
]

def build(name, scene):
    return {
      "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen_image_2.1_int8_convrot.safetensors", "weight_dtype": "default"}},
      "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_8b_w4a8.safetensors", "type": "qwen_image", "device": "default"}},
      "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
      "9": {"class_type": "LoadImage", "inputs": {"image": "ref_canon.png"}},
      "4": {"class_type": "TextEncodeQwenImage21", "inputs": {
        "clip": ["2", 0], "prompt": scene, "negative_prompt": "", "resolution": 1024,
        "images.image_1": ["9", 0], "vae": ["3", 0]}},
      "6": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["4", 1],
            "latent_image": ["4", 2], "seed": 4242, "steps": 25, "cfg": 1.0, "sampler_name": "euler",
            "scheduler": "simple", "denoise": 1.0}},
      "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
      "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": f"qwen21/art-{name}"}},
    }

q = json.load(opener.open(BASE + "/queue", timeout=10))
if q.get("queue_running") or q.get("queue_pending"):
    print("QUEUE BUSY - aborting to avoid mixing")
    raise SystemExit(1)

for name, scene in SCENES:
    wf = build(name, scene)
    req = urllib.request.Request(BASE + "/prompt",
        data=json.dumps({"prompt": wf, "client_id": "rin-batch5"}).encode(),
        headers={"Content-Type": "application/json"})
    res = json.load(opener.open(req, timeout=60))
    print("queued", name, "->", res["prompt_id"], flush=True)
print("ALL SUBMITTED (5 jobs, ~9 min each with 1 ref = ~45 min total)")
