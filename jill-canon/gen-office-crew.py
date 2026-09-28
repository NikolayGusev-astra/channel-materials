"""Cover illustration: four Jills in an office, four work uniforms, four LLM provider badges.

Canon reference: ref_canon.png (jill-canon-qwen21.png) as images.image_1.
Warmup job first (mandatory before reference batches), then the cover.
"""
import json, os, time, urllib.request

for v in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
    os.environ.pop(v, None)
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
BASE = "http://127.0.0.1:8188"

CORE = (
    "four identical young women, same face repeated four times, purple hair in two round buns, "
    "white shirt, black vest, tie, tired kind eyes, anime style, cel shaded, clean line art"
)

PROMPT = (
    "wide office interior, " + CORE + ", standing side by side at four separate workstations, "
    "each wearing a different work uniform: "
    "leftmost as a system administrator in a dark navy shirt with rolled sleeves, standing at a tall "
    "server rack, white name badge on her chest reading OPENCODE-GO; "
    "second as a secretary in a beige blouse and dark pencil skirt, seated at a desk with a telephone "
    "and a stack of manila folders, name badge reading OPENROUTER; "
    "third as an office manager in a grey blazer holding a tablet, standing beside a whiteboard, "
    "name badge reading KILO; "
    "rightmost as a cleaning lady in blue overalls and purple shoes holding a mop and a bucket, "
    "name badge reading NOUS; "
    "bright daylight through office windows, potted plants, each woman at her own desk, "
    "the only text anywhere in the image is the four name badges"
)

NEGATIVE = "text, watermark, blurry, bad anatomy, bad hands, extra fingers, deformed faces, letters other than the badges"


def nodes(prompt, prefix, unet, res, seed, steps=25, ref=True):
    n = {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": unet, "weight_dtype": "default"}},
        "2": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen3vl_8b_w4a8.safetensors", "type": "qwen_image", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "qwen_image_2.1_vae_bf16.safetensors"}},
    }
    enc = {"clip": ["2", 0], "prompt": prompt, "negative_prompt": NEGATIVE, "resolution": res}
    if ref:
        n["9"] = {"class_type": "LoadImage", "inputs": {"image": "ref_canon.png"}}
        enc["images.image_1"] = ["9", 0]
        enc["vae"] = ["3", 0]
        latent = ["4", 2]
    else:
        n["5"] = {"class_type": "EmptyLatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}}
        n["4"] = {"class_type": "TextEncodeQwenImage21", "inputs": {
            "clip": ["2", 0], "prompt": "simple grey dot on white", "negative_prompt": "", "resolution": 512}}
        latent = ["5", 0]
    n["4"] = {"class_type": "TextEncodeQwenImage21", "inputs": enc} if ref else n["4"]
    n["6"] = {"class_type": "KSampler", "inputs": {
        "model": ["1", 0], "positive": ["4", 0], "negative": ["4", 1], "latent_image": latent,
        "seed": seed, "steps": steps, "cfg": 1.0, "sampler_name": "euler",
        "scheduler": "simple", "denoise": 1.0}}
    n["7"] = {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["3", 0]}}
    n["8"] = {"class_type": "SaveImage", "inputs": {"images": ["7", 0], "filename_prefix": prefix}}
    return n


def submit(wf, tag):
    req = urllib.request.Request(
        BASE + "/prompt", data=json.dumps({"prompt": wf, "client_id": "rin-office-crew"}).encode(),
        headers={"Content-Type": "application/json"})
    res = json.load(opener.open(req, timeout=60))
    print("queued", tag, "->", res["prompt_id"], flush=True)
    return res["prompt_id"]


def wait(pid, label, timeout=2400):
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = json.load(opener.open(BASE + "/history/" + pid, timeout=30))
        if pid in h:
            out = h[pid]["outputs"]["8"]["images"][0]
            print(f"DONE {label}: {out['filename']} ({time.time()-t0:.0f}s)", flush=True)
            return out
        q = json.load(opener.open(BASE + "/queue", timeout=10))
        print(f"  {label} {time.time()-t0:.0f}s running={len(q.get('queue_running',[]))} pending={len(q.get('queue_pending',[]))}", flush=True)
        time.sleep(30)
    raise SystemExit(f"timeout on {label}")


if __name__ == "__main__":
    # Mandatory warmup: cold start with references goes to swap mode (up to 60 s/step).
    warm = nodes("", "qwen21/warmup", "qwen_image_2.1_int4_convrot.safetensors", 512, 7, steps=8, ref=False)
    warm["6"]["inputs"]["steps"] = 8
    wait(submit(warm, "warmup"), "warmup", timeout=900)

    main = nodes(PROMPT, "qwen21/office-crew", "qwen_image_2.1_int8_convrot.safetensors", 1536, 20260928)
    wait(submit(main, "office-crew"), "office-crew")
