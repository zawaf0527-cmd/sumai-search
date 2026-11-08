"""/parse → /search → /explain を通しで試す"""
import json, sys, httpx

BASE = "http://127.0.0.1:8000"
text = sys.argv[1] if len(sys.argv) > 1 else "大手町まで45分、5000万以内、大きな公園。静かな街がいい"

r = httpx.post(f"{BASE}/parse", json={"text": text}, timeout=300); r.raise_for_status()
plan = r.json()
print("■解釈:", json.dumps(plan, ensure_ascii=False))

r = httpx.post(f"{BASE}/search", json=plan, timeout=60); r.raise_for_status()
res = r.json()
results = res["results"] if isinstance(res, dict) and "results" in res else res
print(f"■ヒット {len(results)} 駅")

r = httpx.post(f"{BASE}/explain", json={"plan": plan, "results": results}, timeout=300)
r.raise_for_status()
ex = r.json()
for i, it in enumerate(ex["items"], 1):
    print(f"{i}. {it['station']} [{it['source']}] {it['summary']}")
for n in ex["notes"]:
    print("※", n)
