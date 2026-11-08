"""/parse → /search を実行し、結果1件目の中身を表示する"""
import json, httpx

BASE = "http://127.0.0.1:8000"
text = "大手町まで45分、5000万以内、大きな公園"

plan = httpx.post(f"{BASE}/parse", json={"text": text}, timeout=300).json()
res = httpx.post(f"{BASE}/search", json=plan, timeout=60).json()

print("■ /search の返り値の型:", type(res).__name__)
if isinstance(res, dict):
    print("■ 一番外側のキー:", list(res.keys()))
    results = res.get("results", [])
else:
    results = res

print(f"■ ヒット件数: {len(results)}")
if results:
    print("■ 1件目の中身:")
    print(json.dumps(results[0], ensure_ascii=False, indent=2))
