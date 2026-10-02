"""Cover art: Jill driving at an intersection, three traffic lights (red/amber/green).

Traffic-light count and colour assignment are the load-bearing part of the
scene, so both are stated explicitly in the prompt and reinforced in the
negative (no fourth light, no duplicated colours). The colour words are
visual attributes, not text in frame, so the no-text negative stays.
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

# The count comes first, exactly as the six-arm cover had to lead with anatomy.
LIGHTS = (
    "exactly three traffic lights standing side by side over the three lanes of "
    "the road, one traffic light per lane, the left traffic light shows a red "
    "signal, the middle traffic light shows an amber signal, the right traffic "
    "light shows a green signal, all three housings fully visible and separate"
)

SCENE = (
    f"{CORE}, driving a small car seen from the front through the windscreen, "
    f"both hands on the steering wheel, stopped at a city intersection, {LIGHTS}, "
    "crosswalk stripes on the asphalt, dusk sky, anime style, cinematic lighting, "
    "wide shot showing the driver and all three traffic lights in one frame"
)

NEGATIVE = (
    "two traffic lights, four traffic lights, more than three traffic lights, "
    "two red lights, two green lights, amber and yellow together in one light, "
    "duplicate traffic lights on neighbouring poles, traffic lights behind the "
    "camera, text, letters, captions, labels, signs, road markings that look "
    "like words, watermark, signature, extra arms, extra hands, fused fingers, "
    "malformed hands, lowres, worst quality"
)

LORA = "Qwen-Image-2.1-viggle-turbo-v0.2.1-6step-lora-r128.safetensors"
UNET = "qwen_image_2.1_int8_convrot.safetensors"
CLIP = "qwen3vl_8b_w4a8.safetensors"
VAE = "qwen_image_2.1_vae_bf16.safetensors"
SIGMAS = "1.0, 0.9375, 0.875, 0.75, 0.5, 0.25"

WIDTH, HEIGHT = 2048, 1152
SEEDS = [20261010, 20261011]


def find_gate():
    for c in (os.path.join(HERE, "memgate.py"),
              os.path.join(os.path.dirname(HERE), "memgate.py"),
              r"C:\Work\Assist\comfyui\memgate.py"):
        if os.path.exists(c):
            return os.path.abspath(c)
    return None


def gate(profile="comfyui-ref"):
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


def wait(pid, label, budget=700):
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
    free_models()      # documented order: free -> gate -> submit
    gate("comfyui-ref")
    q = json.load(opener.open(BASE + "/queue", timeout=20))
    if q.get("queue_running") or q.get("queue_pending"):
        print("QUEUE BUSY")
        return 1

    for seed in SEEDS:
        prefix = f"viggle/decision-models/cover-seed{seed}"
        pid = queue(wf(seed, prefix), "rin-cover")
        img = wait(pid, f"seed{seed}", 700)
        if img:
            print("OUT:", json.dumps(img, ensure_ascii=False), flush=True)
        free_models()
    return 0


if __name__ == "__main__":
    sys.exit(main())