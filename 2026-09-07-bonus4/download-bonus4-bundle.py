#!/usr/bin/env python3
"""Скачать все модели для Бонуса 4 (Krita + ComfyUI + 5 SDXL + IP-Adapter + inpaint + upscaler).
Поддерживает resume — перезапускать если оборвалось, докачает."""
import urllib.request, os, time, sys

ROOT = r"C:\Work\Assist\comfyui\app\models"
os.makedirs(os.path.join(ROOT, "checkpoints"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "loras"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "vae"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "text_encoders"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "ipadapter"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "clip_vision"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "inpaint"), exist_ok=True)
os.makedirs(os.path.join(ROOT, "upscale_models"), exist_ok=True)

# (относительный путь, URL, ожидаемый размер в МБ)
DOWNLOADS = [
    # Checkpoints (5 SDXL)
    ("checkpoints/novaAnimeXL_ilV125.safetensors",
     "https://huggingface.co/Acly/SD-Checkpoints/resolve/main/novaAnimeXL_ilV125.safetensors?download=true", 7000),
    ("checkpoints/RealVisXL_v5.0_fp16.safetensors",
     "https://huggingface.co/SG161222/RealVisXL_V5.0/resolve/main/RealVisXL_V5.0_fp16.safetensors?download=true", 7000),
    ("checkpoints/JuggernautXL_v9_rdphoto2.safetensors",
     "https://huggingface.co/RunDiffusion/Juggernaut-XL-v9/resolve/main/Juggernaut-XL_v9_RunDiffusionPhoto_v2.safetensors?download=true", 7000),
    ("checkpoints/DreamShaperXL_Turbo.safetensors",
     "https://huggingface.co/Lykon/dreamshaper-xl-turbo/resolve/main/DreamShaperXL_Turbo_SFWdpmppSde_half_pruned.safetensors?download=true", 7000),
    ("checkpoints/sd_xl_base_1.0.safetensors",
     "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors?download=true", 7000),
    # LoRA
    ("loras/Hyper-SDXL-8steps-CFG-lora.safetensors",
     "https://huggingface.co/Acly/SD-Checkpoints/resolve/main/Hyper-SDXL-8steps-CFG-lora.safetensors?download=true", 800),
    # VAE
    ("vae/sdxl_vae.safetensors",
     "https://huggingface.co/madebyollin/sdxl-vae-fp16-fix/resolve/main/sdxl_vae.safetensors?download=true", 334),
    # Text encoders
    ("text_encoders/clip_l_sdxl_base.safetensors",
     "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/text_encoder/model.safetensors?download=true", 246),
    ("text_encoders/clip_g_sdxl_base.safetensors",
     "https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/text_encoder_2/model.safetensors?download=true", 4930),
    # IP-Adapter
    ("ipadapter/ip-adapter_sdxl_vit-h.safetensors",
     "https://huggingface.co/h94/IP-Adapter/resolve/main/models/ip-adapter-plus_sdxl_vit-h.safetensors?download=true", 700),
    # CLIP-Vision
    ("clip_vision/clip-vision_vit-h.safetensors",
     "https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/image_encoder/model.safetensors?download=true", 2500),
    # Inpaint
    ("inpaint/fooocus_inpaint_head.pth",
     "https://huggingface.co/lllyasviel/fooocus/resolve/main/fooocus_inpaint/inpaint_head.fooocus.patch?download=true", 700),
    ("inpaint/inpaint_v26.fooocus.patch",
     "https://huggingface.co/lllyasviel/fooocus/resolve/main/fooocus_inpaint/inpaint_v26.fooocus.patch?download=true", 1300),
    # Upscaler
    ("upscale_models/4x_NMKD-Superscale-SP_178000_G.pth",
     "https://huggingface.co/datasets/Acly/SD-Checkpoints/resolve/main/4x_NMKD-Superscale-SP_178000_G.pth?download=true", 67),
    ("upscale_models/OmniSR_X2_DIV2K.safetensors",
     "https://huggingface.co/Acly/Omni-SR/resolve/main/OmniSR_X2_DIV2K.safetensors?download=true", 2),
    ("upscale_models/OmniSR_X3_DIV2K.safetensors",
     "https://huggingface.co/Acly/Omni-SR/resolve/main/OmniSR_X3_DIV2K.safetensors?download=true", 2),
    ("upscale_models/OmniSR_X4_DIV2K.safetensors",
     "https://huggingface.co/Acly/Omni-SR/resolve/main/OmniSR_X4_DIV2K.safetensors?download=true", 2),
    ("inpaint/MAT_Places512_G_fp16.safetensors",
     "https://huggingface.co/Acly/MAT/resolve/main/MAT_Places512_G_fp16.safetensors?download=true", 125),
]

def download(url, dst, expected_mb):
    name = os.path.basename(dst)
    cur = os.path.getsize(dst) if os.path.exists(dst) else 0
    cur_mb = cur // 1_000_000
    if cur_mb >= expected_mb * 0.95:
        print(f"  [SKIP] {name} already {cur_mb}MB", flush=True)
        return True
    print(f"  [GET]  {name} ({cur_mb}MB / ~{expected_mb}MB) ← {url[:60]}...", flush=True)
    t0 = time.time()
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        if cur > 0:
            headers["Range"] = f"bytes={cur}-"
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=1800) as r, open(dst, "ab" if cur else "wb") as f:
            total = int(r.headers.get("Content-Length", 0)) + cur
            read = cur
            chunk = 1024 * 1024
            last_print = t0
            while True:
                d = r.read(chunk)
                if not d: break
                f.write(d)
                read += len(d)
                if time.time() - last_print > 20:
                    pct = (read / total * 100) if total else 0
                    speed = (read - cur) / (time.time() - t0) / 1_000_000
                    eta = (total - read) / (speed * 1_000_000) if speed > 0 else 0
                    print(f"        {read//1_000_000}/{total//1_000_000}MB ({pct:.0f}%) {speed:.1f}MB/s ETA {eta:.0f}s", flush=True)
                    last_print = time.time()
        sz = os.path.getsize(dst)
        print(f"  [DONE] {name} {sz//1_000_000}MB in {(time.time()-t0):.0f}s", flush=True)
        return True
    except Exception as e:
        print(f"  [FAIL] {name}: {e}", flush=True)
        return False

print(f"=== Bonus 4 model bundle ===\n", flush=True)
ok = 0; fail = 0
for rel, url, expected_mb in DOWNLOADS:
    dst = os.path.join(ROOT, rel)
    if download(url, dst, expected_mb):
        ok += 1
    else:
        fail += 1
print(f"\n=== Result: {ok} OK, {fail} failed ===\n", flush=True)
if fail:
    print("Re-run this script to retry failed downloads (supports resume)", flush=True)
