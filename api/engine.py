from pathlib import Path
import pandas as pd
import transit
from schemas import CATALOG, Commute, AreaMetric, PoiProximity, SearchPlan

DATA = Path(__file__).parent / "data"
features = pd.read_parquet(DATA / "station_features.parquet")
poi = pd.read_parquet(DATA / "station_poi.parquet")

def clean(v):
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return None
    return v.item() if hasattr(v, "item") else v

def gkey(g) -> str | None:
    """group_code の型のずれ（int / float / str）をそろえて、突き合わせできるようにする"""
    if g is None or (not isinstance(g, str) and pd.isna(g)):
        return None
    if isinstance(g, float) and g.is_integer():
        g = int(g)
    return str(g)

features["gkey"] = features.group_code.map(gkey)

def commute_lookup(c: Commute):
    """乗り換えグラフで、全駅 → 行き先 の分数と経路を計算する"""
    table = transit.commute_table(c.dest_station, getattr(c, "max_transfers", None))
    if table is None:
        raise ValueError(f"駅が見つかりません: {c.dest_station}")
    minutes = {gkey(g): r.minutes for g, r in table.items()}
    routes = {gkey(g): f"乗換{r.transfers}回・{r.text}" for g, r in table.items()}
    return minutes, routes

def search(plan: SearchPlan, top_n: int = 20) -> list[dict]:
    df = features.copy()
    for i, c in enumerate(plan.conditions):
        val, sc = f"c{i}_value", f"c{i}"
        if isinstance(c, Commute):
            minutes, routes = commute_lookup(c)
            df[val] = df.gkey.map(minutes)
            df[f"c{i}_name"] = df.gkey.map(routes)          # 経路を根拠(name)に載せる
            df = df[df[val].notna()].copy()                  # 乗換上限の中で行けない駅は除外
            if c.max_minutes is not None:
                df = df[df[val] <= c.max_minutes].copy()     # 通勤は必ず守る条件
                df[sc] = 1 - df[val] / c.max_minutes
            else:
                df[sc] = 1 - df[val].rank(pct=True)
        elif isinstance(c, AreaMetric):
            df[val] = df[c.metric]
            if c.importance == "must":                       # 値が null の駅もここで除外される
                if c.max_value is not None: df = df[df[val] <= c.max_value].copy()
                if c.min_value is not None: df = df[df[val] >= c.min_value].copy()
            r = df[val].rank(pct=True)
            better_high = CATALOG["area_metrics"][c.metric]["better"] == "high"
            df[sc] = (r if better_high else 1 - r).fillna(0)
        elif isinstance(c, PoiProximity):
            within = c.within_m or CATALOG["poi"][c.category]["default_within_m"]
            p = poi[poi.category == c.category].copy()
            p["gkey"] = p.group_code.map(gkey)
            p = p.set_index("gkey")
            df[val] = df.gkey.map(p["nearest_m"])
            df[f"c{i}_name"] = df.gkey.map(p["nearest_name"])
            if c.importance == "must":
                df = df[df[val] <= within].copy()
            df[sc] = (1 - df[val] / (within * 2)).clip(0, 1).fillna(0)

    cols = [f"c{i}" for i in range(len(plan.conditions))]
    df["score"] = df[cols].mean(axis=1) if cols else 0.0
    out = []
    for _, r in df.sort_values("score", ascending=False).head(top_n).iterrows():
        out.append({
            "station": r.station_name, "city": r.city_name,
            "lat": r.lat, "lon": r.lon, "score": round(float(r.score), 3),
            "evidence": [
                {"condition": c.model_dump(), "value": clean(r[f"c{i}_value"]),
                 "name": clean(r.get(f"c{i}_name"))}
                for i, c in enumerate(plan.conditions)
            ],
            "group_code": str(r["group_code"]),   # ← 追加（r は隣の行と同じ変数名に合わせる）
        })
    return out
