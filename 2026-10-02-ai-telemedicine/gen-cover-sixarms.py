"""Cover art retry: Jill with SIX arms (Shiva pose), 3 handsets + 3 pens.

First attempt rendered two arms - vision confirmed it. The prompt described the
six arms but did not make the count load-bearing, so the model collapsed to
the canon pose. This version leads with the anatomy and names each arm group
explicitly, and keeps the no-text negative because the scene implies writing.
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

for _k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(_k, None)

BASE = "http://127.0.0.1:8188"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
HERE = os.path.dirname(os.path.abspath(__file__))

CORE = (
    "young woman bartender, purple hair in two round buns, white shirt, "
    "black vest, tired kind eyes"
)

# Anatomy first, count stated twice, each group enumerated. The model lost the
# count when it was mentioned after the scene; now it is the first thing read.
ARMS = (
    "a six-armed woman, exactly six arms in total, three arms on her left side "
    "and three arms on her right side, fanning out symmetrically from her "
    "shoulders like the Hindu goddess Durga with six arms, each of the six arms "
    "is fully visible and separately drawn, six hands visible in the frame"
)

HELD = (
    "the upper three hands each hold a black corded telephone handset, one "
    "handset lifted to each ear and one held out to the side, the lower three "
    "hands each hold a pen writing on a blank white sheet of paper on the desk"
)

SCENE = (
    f"{CORE}, {ARMS}, {HELD}, seated behind a clinic reception desk, front view, "
    "full upper body visible so all six arms are inside the frame, warm dim "
    "clinic lighting, telephone cord coiled on the desk, anime style"
)

NEGATIVE = (
    "two arms, four arms, eight arms, missing arms, hidden arms, arms out of "
    "frame, text, letters, captions, labels, signs, handwriting, printed words, "
    "watermark, signature, fused fingers, malformed hands, extra fingers, "
    "lowres, worst quality"
)

LORA = "Qwen-Image-2.1-viggle-turbo-v0.2.1-6step-lora-r128.safetensors"
UNET = "qwen_image_2.1_int8_convrot.safetensors"
CLIP = "qwen3vl_8b_w4a8.safetensors"
VAE = "qwen_image_2.1_vae_bf16.safetensors"
SIGMAS = "1.0, 0.9375, 0.875, 0.75, 0.5, 0.25"

WIDTH, HEIGHT = 1280, 768
SEEDS = [20261003, 20261004]


def find_gate() -> str | None:
    cands = [
        os.path.join(HERE, "memgate.py"),
        os.path.join(os.path.dirname(HERE), "memgate.py"),
        r"<local-path>\Work\Assist\comfyui\memgate.py",
    ]
    for c in cands:
        if os.path.exists(c):
            return os.path.abspath(c)
    return None


def gate(profile: str = "comfyui-ref") -> None:
    g = find_gate()
    if g is None:
        print("memgate.py not found - refusing to run", flush=True)
        sys.exit(3)
    proc = subprocess.run([sys.executable, g, "--profile", profile],
                          capture_output=True, text=True, timeout=180)
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        print(f"memgate rc={proc.returncode}; nothing queued", flush=True)
        sys.exit(proc.returncode)
    print("memgate rc=0", flush=True)


def queue(wf, client):
    req = urllib.request.Request(
        BASE + "/prompt",
        data=json.dumps({"prompt": wf, "client_id": client}).encode(),
        headers={"Content-Type": "application/json"})
    return json.load(opener.open(req, timeout=90))["prompt_id"]


def wait(pid, label, budget=600):
    t0 = time.time()
    while time.time() - t0 < budget:
        try:
            h = json.load(opener.open(f"{BASE}/history/{pid}", timeout=20))
        except Exception:
            h = {}
        if h:
            st = h[pid]["status"]
            if not st.get("completed"):
                print(f"{label}: FAILED {st.get('status_str')}", flush=True)
                for m in st.get("messages", [])[:2]:
                    print("   ", str(m)[:240], flush=True)
                return None
            print(f"{label}: ok in {time.time() - t0:.0f}s", flush=True)
            for _n, out in h[pid].get("outputs", {}).items():
                for im in out.get("images", []):
                    return im
            return {}
        time.sleep(8)
    print(f"{label}: TIMEOUT", flush=True)
    return None


def free_models():
    body = json.dumps({"unload_models": True, "free_memory": True}).encode()
    try:
        opener.open(urllib.request.Request(
            BASE + "/free", data=body,
            headers={"Content-Type": "application/json"}), timeout=30).read()
        print("models unloaded", flush=True)
    except urllib.error.HTTPError as exc:
        print("free failed:", exc.code, flush=True)
    time.sleep(5)


def wf(seed, prefix):
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": UNET, "weight_dtype": "default"}},
        "2": {"class_type": "ViggleTurboLora", "inputs": {"model": ["1", 0], "lora_name": LORA, "strength": 1.0}},
        "3": {"class_type": "CLIPLoader", "inputs": {"clip_name": CLIP, "type": "qwen_image", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "5": {"class_type": "LoadImage", "inputs": {"image": "ref_canon.png"}},
        "6": {"class_type": "TextEncodeQwenImage21", "inputs": {
            "clip": ["3", 0], "prompt": SCENE, "negative_prompt": NEGATIVE,
            "resolution": 1024, "images.image_1": ["5", 0], "vae": ["4", 0]}},
        "7": {"class_type": "EmptyLatentImage", "inputs": {"width": WIDTH, "height": HEIGHT, "batch_size": 1}},
        "8": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "9": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "10": {"class_type": "ViggleTurboSigmas", "inputs": {"latent": ["7", 0], "nodes": SIGMAS}},
        "11": {"class_type": "BasicGuider", "inputs": {"model": ["2", 0], "conditioning": ["6", 0]}},
        "12": {"class_type": "SamplerCustomAdvanced", "inputs": {
            "noise": ["8", 0], "guider": ["11", 0], "sampler": ["9", 0],
            "sigmas": ["10", 0], "latent_image": ["7", 0]}},
        "13": {"class_type": "VAEDecode", "inputs": {"samples": ["12", 0], "vae": ["4", 0]}},
        "14": {"class_type": "SaveImage", "inputs": {"images": ["13", 0], "filename_prefix": prefix}},
    }


def main():
    # Release models BEFORE the gate reads memory. ComfyUI keeps the DiT and
    # the 6 GB text encoder resident after a frame, so gating first measures a
    # baseline that the previous run created - the gate then refuses a job the
    # host can actually afford. Order matters: free -> gate -> submit.
    free_models()

    gate("comfyui-ref")
    q = json.load(opener.open(BASE + "/queue", timeout=20))
    if q.get("queue_running") or q.get("queue_pending"):
        print("QUEUE BUSY")
        return 1

    for i, seed in enumerate(SEEDS):
        prefix = f"viggle/ai-telemedicine/sixarms-seed{seed}"
        pid = queue(wf(seed, prefix), "rin-sixarms")
        img = wait(pid, f"seed{seed}", 700)
        if img:
            print("OUT:", json.dumps(img, ensure_ascii=False), flush=True)
        free_models()  # documented requirement between frames

    return 0


if __name__ == "__main__":
    sys.exit(main())
