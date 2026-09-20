"""Шаг 5: инференс обученной модели (для встраивания в пайплайн).
Запуск: python 05_infer.py --model best_model --text "тема\nтело письма"
"""
import os, argparse
os.environ.setdefault("USE_TF", "0")
import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

def load(model_dir):
    # токенизатор лежит в laya_mm_hf/tokenizer (оригинальный), не в best_model
    work = os.path.join(os.path.dirname(os.path.abspath(model_dir)), "laya_mm_hf", "tokenizer")
    if not os.path.isdir(work):
        work = model_dir
    tok = AutoTokenizer.from_pretrained(work)
    model = AutoModelForSequenceClassification.from_pretrained(model_dir).cuda().eval()
    return tok, model

@torch.no_grad()
def predict(tok, model, text):
    enc = tok(text[:1800], truncation=True, max_length=512, return_tensors="pt").to("cuda")
    return torch.softmax(model(**enc).logits, -1)[0, 1].item()  # p(важное)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="best_model")
    ap.add_argument("--text", required=True)
    a = ap.parse_args()
    tok, model = load(a.model)
    p = predict(tok, model, a.text)
    print(f"p(важное) = {p:.3f} -> {'ВАЖНОЕ' if p > 0.5 else 'шум'}")
