"""Cover: Jill assembles a working mechanism from different gears on a stand.

Turbo clean t2i (no reference: turbo+ref crashes on 8GB, verified 22.10),
1376x768, 8 steps cfg 1.0. Small warmup frame first.
"""
import json, os, time, urllib.request

for v in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(v, None)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE = "http://127.0.0.1:8188"

CORE = ("young woman bartender, purple hair in two round buns, white shirt, "
        "black vest, purple shoes, tired kind eyes, anime style, cel shaded, clean line art")

PROMPT = (
    "wide workshop scene, " + CORE + ", standing at a technical display stand, "
    "assembling a large working clockwork mechanism from many different gears, "
    "brass and steel gears of different sizes clicking together into one functioning machine, "
    "holding a gear in her hands about to place it into the assembly, focused clever expression, "
    "sleeves rolled up, workbench with scattered gears springs and tools around the stand, "
    "warm workshop lighting, no text anywhere in the image"
)

NEGATIVE = "text, letters, captions, labels, signs, watermark, blurry, bad anatomy, bad hands, extra fingers, deformed faces"


def nodes(prompt, prefix, seed, w, h, steps):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "qwen-image-2.1-turbo-int8-convrot.safetensors", "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_8b_w4a8.safetensors", "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
        "4": {"class_type": "TextEncodeQwenImage21", "inputs": {"clip": ["2", 0], "prompt": prompt, "negative_prompt": NEGATIVE, "resolution": 1024}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {
            "model": ["1", 0], "positive": ["4", 0], "negative": ["4", 1], "latent_image": ["5", 0],
            "seed": seed, "steps": steps, "cfg": 1.0, "sampler_name": "euler",
            "scheduler": "simple", "denoise": 1.0}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}},
        "8": {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": prefix}},
    }


def free():
    try:
        req = urllib.request.Request(BASE + "/free", data=json.dumps(
            {"free_models": True, "free_vram": False}).encode(),
            headers={"Content-Type": "application/json"})
        opener.open(req, timeout=30).read()
    except Exception as e:
        print("free (empty body is normal):", e, flush=True)


def submit(wf, tag):
    req = urllib.request.Request(BASE + "/prompt",
        data=json.dumps({"prompt": wf, "client_id": "rin-cover-gears"}).encode(),
        headers={"Content-Type": "application/json"})
    res = json.load(opener.open(req, timeout=60))
    print("queued", tag, "->", res["prompt_id"], flush=True)
    return res["prompt_id"]


def wait(pid, label, timeout=1800):
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = json.load(opener.open(BASE + "/history/" + pid, timeout=30))
        if pid in h:
            st = h[pid].get("status", {})
            if st.get("status_str") == "error":
                raise SystemExit(f"ERROR on {label}: {str(st.get('messages'))[:800]}")
            out = h[pid]["outputs"]["8"]["images"][0]
            print(f"DONE {label}: {out['filename']} ({time.time()-t0:.0f}s)", flush=True)
            return out
        time.sleep(15)
    raise SystemExit(f"timeout on {label}")


if __name__ == "__main__":
    warm = nodes("simple blue circle on white", "qwen21/warmup-gears", 7, 512, 512, 8)
    wait(submit(warm, "warmup"), "warmup", timeout=900)
    free()
    main = nodes(PROMPT, "qwen21/cover-gears", 20261023, 1376, 768, 8)
    print(wait(submit(main, "cover-gears"), "cover-gears"), flush=True)
    free()
