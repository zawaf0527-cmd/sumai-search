"""/explain：検索結果の根拠データから説明文を作る。数字はLLMに作らせない。"""
import json, os, re
import httpx
from pydantic import BaseModel
from schemas import SearchPlan
from schemas import SearchPlan, CATALOG


OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:14b")

# ---------- 1. 根拠データ(evidence) → 人が読める短文（数字はここで確定） ----------
def _man(yen):  return f"{yen / 1e4:,.0f}万円"
def _pct(v):    return f"{v * 100:.0f}%"
def _dist(m):   return f"{m / 1000:.1f}km" if m >= 1000 else f"{m:.0f}m"
def _num(v):    return f"{v:g}"

METRIC = {   # metric名: (日本語ラベル, 値の書式)
    "house_price_median": ("戸建て取引価格の中央値", _man),
    "land_area_median":   ("土地面積の中央値", lambda v: f"{v:.0f}㎡"),
    "share_land_150":     ("土地150㎡以上の取引の割合", _pct),
    "flood_share":        ("駅800m圏の浸水想定区域の割合", _pct),
    "flood_deep_share":   ("駅800m圏で浸水深3m以上の想定区域の割合", _pct),
    "landslide_share":    ("駅800m圏の土砂災害警戒区域の割合", _pct),
}
POI_LABEL = {   # catalog.yaml のカテゴリ名に合わせて増やす
    "large_shopping_mall": "大型商業施設",
    "supermarket": "スーパー",
    "golf_course": "ゴルフ場",
    "large_park": "大きな公園",
    "park": "公園",
    "dog_park": "ドッグラン",
    "hospital": "病院",
}

def station_name(row: dict) -> str:
    return str(row.get("station"))

def _fact(ev: dict) -> str:
    c, v = ev["condition"], ev["value"]
    t = c.get("type")
    if t == "commute":
        if v is None:
            return f"{c['dest_station']}までの所要時間: データなし"
        s = f"{c['dest_station']}まで約{v:.0f}分"
        if c.get("max_minutes") is not None:
            s += f"（条件 {c['max_minutes']}分以内）"
        if ev.get("name"):
            s += f"、{ev['name']}"     # 例：「…、乗換1回・総武線→錦糸町で乗換→半蔵門線」
        return s
    if t == "area_metric":
        label, fmt = METRIC.get(c["metric"], (c["metric"], _num))
        if v is None:
            return f"{label}: データなし"
        cond = []
        if c.get("max_value") is not None:
            cond.append(f"上限 {fmt(c['max_value'])}")
        if c.get("min_value") is not None:
            cond.append(f"下限 {fmt(c['min_value'])}")
        return f"{label} {fmt(v)}" + (f"（条件 {'・'.join(cond)}）" if cond else "")
    if t == "poi_proximity":
        label = POI_LABEL.get(c["category"], c["category"])
        if v is None:
            return f"近くの{label}: データなし"
        where = f"「{ev['name']}」" if ev.get("name") else ""
        return f"最寄りの{label}{where}まで駅から直線{_dist(v)}"
    if t == "place_nearby":                     # 店名・施設の種類（flex.py）
        within = c.get("within_m") or 800
        if v is None:
            return f"「{c['query']}」は駅から{_dist(within)}以内に見つかりませんでした"
        where = f"「{ev['name']}」" if ev.get("name") else ""
        return f"「{c['query']}」に当たる{where}まで駅から直線{_dist(v)}"
    if t == "vibe":                             # 街の雰囲気（flex.py）
        label = c.get("label") or CATALOG["vibes"].get(c["vibe"], {}).get("label", c["vibe"])
        if v is None:
            return f"街の雰囲気「{label}」: データなし"
        detail = f"（{ev['detail']}）" if ev.get("detail") else ""
        return f"街の雰囲気「{label}」は{round(v * 100)}点{detail}"
    return f"{t}: {v}"

def facts_for(row: dict) -> list[str]:
    facts = [_fact(ev) for ev in row.get("evidence", [])]
    if row.get("city"):
        facts.append(f"所在地 {row['city']}")
    return facts

# ---------- 2. 数字チェック（根拠にない数字が出たら不採用） ----------
NUM = re.compile(r"\d[\d,]*(?:\.\d+)?")
def _nums(s: str) -> set[str]:
    return {n.replace(",", "") for n in NUM.findall(s)}

def numbers_ok(summary: str, facts: list[str], plan_json: str) -> bool:
    allowed = _nums(" ".join(facts)) | _nums(plan_json)  # 条件の「45分」等は使ってよい
    return _nums(summary) <= allowed

# ---------- 3. LLM呼び出し ----------
SYSTEM = """あなたは住まい探しの説明係です。
各駅について、与えられた「根拠」だけを使い、ユーザーの条件に沿って1〜2文の日本語で説明してください。
- 根拠にない数字・施設名・評判は絶対に書かない
- 数字は根拠の表記をそのまま使う（計算・言い換えをしない）
- 順位を変えたり、他の駅を勧めたりしない
- 条件に合わない点があれば正直に書く"""

OUT_SCHEMA = {
    "type": "object",
    "properties": {"items": {"type": "array", "items": {
        "type": "object",
        "properties": {"station": {"type": "string"}, "summary": {"type": "string"}},
        "required": ["station", "summary"]}}},
    "required": ["items"],
}

def _call_llm(user: str) -> dict:
    payload = {
        "model": MODEL, "stream": False, "format": OUT_SCHEMA,
        "options": {"temperature": 0, "num_ctx": 8192},
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": user}],
    }
    if MODEL.startswith("qwen3"):
        payload["think"] = False
    elif MODEL.startswith("gpt-oss"):
        payload["think"] = "low"
    r = httpx.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=300)
    if r.status_code == 400 and "think" in payload:
        payload.pop("think")
        r = httpx.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=300)
    r.raise_for_status()
    return json.loads(r.json()["message"]["content"])

# ---------- 4. 本体 ----------
class ExplainItem(BaseModel):
    station: str
    summary: str
    facts: list[str]
    source: str            # "llm" か "template"（数字チェックで落ちた等）

class ExplainResponse(BaseModel):
    items: list[ExplainItem]
    notes: list[str]

def explain(plan: SearchPlan, results: list[dict], top_n: int = 5) -> ExplainResponse:
    rows = results[:top_n]
    plan_json = plan.model_dump_json()
    facts = {station_name(r): facts_for(r) for r in rows}

    user = f"ユーザーの条件(JSON): {plan_json}\n\n" + "\n".join(
        f"■{name}\n根拠: " + " / ".join(fs) for name, fs in facts.items())
    try:
        llm_out = {i["station"]: i["summary"] for i in _call_llm(user)["items"]}
    except Exception:
        llm_out = {}           # LLMが落ちても説明は出す

    items = []
    for name, fs in facts.items():
        s = llm_out.get(name, "")
        if s and numbers_ok(s, fs, plan_json):
            items.append(ExplainItem(station=name, summary=s, facts=fs, source="llm"))
        else:
            items.append(ExplainItem(station=name, summary="、".join(fs[:3]) + "。",
                                     facts=fs, source="template"))

    notes = [f"「{u}」は評価できるデータがないため、順位には反映していません。"
             for u in plan.unsupported]
    _log_unsupported(plan.unsupported)
    return ExplainResponse(items=items, notes=notes)

def _log_unsupported(texts: list[str]):
    """評価できなかった希望を貯める → 後でBigQueryに送り、カタログ追加の優先度に使う"""
    if not texts:
        return
    os.makedirs("logs", exist_ok=True)
    with open("logs/unsupported.jsonl", "a", encoding="utf-8") as f:
        for t in texts:
            f.write(json.dumps({"text": t}, ensure_ascii=False) + "\n")
