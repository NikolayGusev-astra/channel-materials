"""Шаг 4: дообучение mmBERT-энкодера из laya на своих метках.
Запуск: python 04_train.py --data mails_labeled.json --out best_model
Железо: любая карта 8+ ГБ (замерено на RTX 4060: 1к писем = 82 с, 10к = 15.5 мин).
"""
import os, json, time, argparse, shutil, random
os.environ.setdefault("USE_TF", "0")
import torch
from torch.utils.data import Dataset, DataLoader
from transformers import AutoTokenizer, AutoModelForSequenceClassification, get_linear_schedule_with_warmup

def prepare_laya_encoder(laya_snapshot_dir, work_dir):
    """laya хранит веса в нестандартной схеме (encoder.*, act_head, scorer).
    Вынимаем чистый mmBERT-энкодер: переименование encoder.* -> modernbert.*
    и config.json с model_type=modernbert."""
    os.makedirs(work_dir, exist_ok=True)
    from safetensors.torch import load_file, save_file
    shutil.copy(os.path.join(laya_snapshot_dir, "model.safetensors"),
                os.path.join(work_dir, "model.safetensors"))
    shutil.copytree(os.path.join(laya_snapshot_dir, "tokenizer"),
                    os.path.join(work_dir, "tokenizer"), dirs_exist_ok=True)
    sd = load_file(os.path.join(work_dir, "model.safetensors"))
    new_sd = {("modernbert." + k[len("encoder."):]): v for k, v in sd.items() if k.startswith("encoder.")}
    save_file(new_sd, os.path.join(work_dir, "model.safetensors"), metadata={"format": "pt"})
    enc_cfg = json.load(open(os.path.join(laya_snapshot_dir, "encoder", "config.json"), encoding="utf-8"))
    enc_cfg["num_labels"] = 2
    json.dump(enc_cfg, open(os.path.join(work_dir, "config.json"), "w", encoding="utf-8"), indent=1)
    return work_dir

class DS(Dataset):
    def __init__(self, rows, tok):
        self.rows, self.tok = rows, tok
    def __len__(self): return len(self.rows)
    def __getitem__(self, i):
        r = self.rows[i]
        enc = self.tok(r["text"], truncation=True, max_length=512, padding="max_length", return_tensors="pt")
        return {"input_ids": enc["input_ids"][0], "attention_mask": enc["attention_mask"][0],
                "labels": torch.tensor(r["label"])}

def loader(rows, tok, shuffle):
    return DataLoader(DS(rows, tok), batch_size=16, shuffle=shuffle, generator=torch.Generator().manual_seed(42))

@torch.no_grad()
def evaluate(m, rows, tok):
    m.eval(); correct, probs, labels = 0, [], []
    for b in loader(rows, tok, False):
        b = {k: v.cuda() for k, v in b.items()}
        out = m(**b)
        probs += torch.softmax(out.logits, -1)[:, 1].float().tolist()
        labels += b["labels"].tolist()
        correct += (out.logits.argmax(-1) == b["labels"]).sum().item()
    m.train()
    return correct / len(rows), probs, labels

def f1_at(pv, yv):
    tp = sum((p>0.5) and y==1 for p,y in zip(pv,yv))
    fp = sum((p>0.5) and y==0 for p,y in zip(pv,yv))
    fn = sum((p<=0.5) and y==1 for p,y in zip(pv,yv))
    return 2*tp/max(2*tp+fp+fn, 1)

def ece_calc(ps, ys, bins=10):
    tot = len(ps); e = 0.0
    for i in range(bins):
        lo, hi = i/bins, (i+1)/bins
        sel = [(p, y) for p, y in zip(ps, ys) if lo <= max(p,1-p) < hi]
        if not sel: continue
        e += len(sel)/tot * abs(sum(max(p,1-p) for p,_ in sel)/len(sel) - sum((p>0.5)==bool(y) for p,y in sel)/len(sel))
    return e

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="mails_labeled.json")
    ap.add_argument("--laya-dir", default=None, help="папка snapshot multilingual из кеша HF; если нет - скачается")
    ap.add_argument("--work-dir", default="laya_mm_hf")
    ap.add_argument("--out", default="best_model")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    random.seed(args.seed)

    rows = [r for r in json.load(open(args.data, encoding="utf-8")) if r.get("label") is not None]
    for r in rows: r["text"] = (r["subject"] + "\n" + r["body_snippet"])[:1800]
    random.shuffle(rows)
    n = len(rows)
    train, val, test = rows[:int(n*0.8)], rows[int(n*0.8):int(n*0.9)], rows[int(n*0.9):]
    print(f"train {len(train)} / val {len(val)} / test {len(test)}")

    if args.laya_dir:
        work = prepare_laya_encoder(args.laya_dir, args.work_dir)
    else:
        work = args.work_dir
    tok = AutoTokenizer.from_pretrained(os.path.join(work, "tokenizer"))
    model = AutoModelForSequenceClassification.from_pretrained(work, num_labels=2, torch_dtype=torch.bfloat16).cuda()

    opt = torch.optim.AdamW(model.parameters(), lr=2e-5, weight_decay=0.01)
    total = len(loader(train, tok, True)) * args.epochs
    sched = get_linear_schedule_with_warmup(opt, int(0.1*total), total)

    best_f1, t0 = 0, time.time()
    for ep in range(args.epochs):
        model.train(); run = 0.0
        for b in loader(train, tok, True):
            b = {k: v.cuda() for k, v in b.items()}
            with torch.autocast("cuda", dtype=torch.bfloat16):
                out = model(**b)
            out.loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step(); sched.step(); opt.zero_grad()
            run += out.loss.item()
        acc_v, pv, yv = evaluate(model, val, tok)
        f1 = f1_at(pv, yv)
        print(f"epoch {ep+1}: loss={run/len(loader(train,tok,True)):.4f} val_acc={acc_v:.3f} val_f1={f1:.3f} | {time.time()-t0:.0f}s", flush=True)
        if f1 > best_f1:
            best_f1 = f1
            model.save_pretrained(args.out)

    best = AutoModelForSequenceClassification.from_pretrained(args.out).cuda()
    acc_t, pt, yt = evaluate(best, test, tok)
    print(f"TEST: acc={acc_t:.3f} f1={f1_at(pt,yt):.3f} ece={ece_calc(pt,yt):.3f} | {time.time()-t0:.0f}s всего")
    json.dump({"acc": round(acc_t,3), "f1": round(f1_at(pt,yt),3), "ece": round(ece_calc(pt,yt),3)},
              open(os.path.join(args.out, "metrics.json"), "w"))

if __name__ == "__main__":
    main()
