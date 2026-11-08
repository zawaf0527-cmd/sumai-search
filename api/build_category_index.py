"""OSMカテゴリ → 日本語ラベル・言い換え → ベクトル。結果は data/category_index.parquet"""
import json, os
from pathlib import Path
import httpx, numpy as np, pandas as pd

DATA = Path(__file__).parent / "data"
URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "qwen3.5:27b")
LABELS = DATA / "category_labels.csv"
SCHEMA = {"type": "object", "properties": {"items": {"type": "array", "items": {
    "type": "object", "required": ["category", "ja", "aliases"],
    "properties": {"category": {"type": "string"}, "ja": {"type": "string"},
                   "aliases": {"type": "array", "items": {"type": "string"}}}}}},
    "required": ["items"]}


def label_batch(cats):
    payload = {"model": MODEL, "stream": False, "format": SCHEMA, "think": False,
               "options": {"temperature": 0},
               "messages": [{"role": "user", "content":
                   "次のOpenStreetMapのタグそれぞれに、日本で一般的な呼び名(ja)と、"
                   "利用者が検索で使いそうな言い換え(aliases、3〜6個)を付けてJSONで返して。\n"
                   + "\n".join(cats)}]}
    r = httpx.post(f"{URL}/api/chat", json=payload, timeout=600)
    if r.status_code == 400 and "think" in r.text:
        payload.pop("think"); r = httpx.post(f"{URL}/api/chat", json=payload, timeout=600)
    r.raise_for_status()
    return json.loads(r.json()["message"]["content"])["items"]


def main():
    cats = pd.read_parquet(DATA / "place_categories.parquet")["category"].tolist()
    if not LABELS.exists():                       # ① ラベル作り（1回だけ。CSVは手で直してOK）
        rows = []
        for i in range(0, len(cats), 30):
            rows += [it for it in label_batch(cats[i:i + 30]) if it["category"] in cats]
            print(f"  {min(i + 30, len(cats))}/{len(cats)}")
        pd.DataFrame([{**r, "aliases": "、".join(r["aliases"])} for r in rows]) \
            .to_csv(LABELS, index=False, encoding="utf-8-sig")
    lab = pd.read_csv(LABELS, encoding="utf-8-sig").fillna("")
    texts = (lab["ja"] + "：" + lab["aliases"] + "（" + lab["category"] + "）").tolist()
    vecs = []                                     # ② ベクトル化
    for i in range(0, len(texts), 64):
        r = httpx.post(f"{URL}/api/embed", json={"model": "bge-m3", "input": texts[i:i + 64]}, timeout=300)
        r.raise_for_status(); vecs += r.json()["embeddings"]
    v = np.array(vecs, dtype="float32"); v /= np.linalg.norm(v, axis=1, keepdims=True)
    lab["vec"] = list(v)
    lab.to_parquet(DATA / "category_index.parquet")
    print(len(lab), "カテゴリを索引化しました")


if __name__ == "__main__":
    main()
