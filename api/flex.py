"""自由入力の条件（店名・施設の種類・街の雰囲気）を扱う部品。
engine.py の検索結果を受け取り、絞り込み・加点・並べ替えをする。"""
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

from engine import search as base_search
from schemas import CATALOG, PlaceNearby, Vibe

DATA = Path(__file__).parent / "data"
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "bge-m3")

# ===== 列名の設定（D-1 の表示に合わせる）=====
PL_GROUP, PL_CAT, PL_NAME, PL_TEXT, PL_DIST = "group_code", "category", "name", "search_text", "dist_m"
CI_CAT, CI_LABEL, CI_VEC = "category", "ja", "vec"
VB_GROUP = "group_code"

# ===== 調整用のつまみ =====
DEFAULT_WITHIN = 800   # 距離の指定がないときは徒歩10分
SIM_CATEGORY = 0.60    # これ以上似ていれば「施設の種類」として扱う
SIM_MIN = 0.55         # 店名で見つからないとき、種類として認める最低ライン
VIBE_MUST = 0.6        # 雰囲気が「必須」のとき、この点数未満の駅は除外
ALIASES = {"スタバ": "スターバックス", "マック": "マクドナルド", "マクド": "マクドナルド",
           "オーケーストア": "オーケー", "ドンキ": "ドン・キホーテ"}
STRIP = re.compile(r"(がある|のある|が近い|駅|ストア|店)$")


def norm(s) -> str:
    """表記ゆれ吸収。stg_osm__places の search_text と同じルール"""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(s))).lower()


def norm_code(x) -> str:
    """group_code の型の違い（int / float / str）をそろえる"""
    try:
        return str(int(float(x)))
    except (TypeError, ValueError):
        return str(x)


# ---------- 起動時に1回だけ読み込む ----------
places = pd.read_parquet(DATA / "station_places.parquet")
places["code"] = places[PL_GROUP].map(norm_code)
places[PL_TEXT] = places[PL_TEXT].fillna("")
places["brand_n"] = places["brand"].fillna("").map(norm)   # チェーン名（OSMのbrandタグ）

cat_idx = pd.read_parquet(DATA / "category_index.parquet").reset_index(drop=True)
CAT_MAT = np.vstack(cat_idx[CI_VEC].to_numpy()).astype("float32")
CAT_MAT /= np.linalg.norm(CAT_MAT, axis=1, keepdims=True) + 1e-9


def embed(text: str) -> np.ndarray:
    r = httpx.post(f"{OLLAMA_URL}/api/embed",
                   json={"model": EMBED_MODEL, "input": [text]}, timeout=120)
    r.raise_for_status()
    v = np.array(r.json()["embeddings"][0], dtype="float32")
    return v / (np.linalg.norm(v) + 1e-9)


# ---------- 店名・施設 ----------
@lru_cache(maxsize=512)
def resolve_place(query: str) -> dict:
    """①チェーン名に一致 → 店名 / ②施設の種類に十分近い → 種類 / ③名前に含む → 店名"""
    q = ALIASES.get(query.strip(), query.strip())
    needle = STRIP.sub("", norm(q)) or norm(q)
    n_brand = places.loc[places["brand_n"].str.contains(needle, regex=False), "code"].nunique()
    n_name = places.loc[places[PL_TEXT].str.contains(needle, regex=False), "code"].nunique()

    sims = CAT_MAT @ embed(q)
    i = int(sims.argmax())
    best = float(sims[i])
    cat = cat_idx.iloc[i]
    best_cat = f"{cat[CI_LABEL]}（{cat[CI_CAT]}）"

    def as_name():
        return {"query": query, "kind": "name", "key": needle,
                "label": f"名前に「{needle}」を含む施設", "sim": round(best, 3),
                "n_stations": int(n_name), "best_cat": best_cat}

    def as_category():
        n = places.loc[places[PL_CAT] == cat[CI_CAT], "code"].nunique()
        return {"query": query, "kind": "category", "key": cat[CI_CAT],
                "label": f"施設の種類「{best_cat}」", "sim": round(best, 3),
                "n_stations": int(n), "best_cat": best_cat}

    if n_brand > 0 and n_name > 0:
        return as_name()
    if best >= SIM_CATEGORY:
        return as_category()
    if n_name > 0:
        return as_name()
    if best >= SIM_MIN:
        return as_category()
    return {"query": query, "kind": None, "key": None, "label": "該当データなし",
            "sim": round(best, 3), "n_stations": 0, "best_cat": best_cat}

@lru_cache(maxsize=512)
def nearest_places(kind: str, key: str) -> dict:
    """駅ごとに一番近い該当施設 → {code: (距離m, 施設名)}"""
    if kind == "category":
        sub = places[places[PL_CAT] == key]
    else:
        sub = places[places[PL_TEXT].str.contains(key, regex=False)]
    sub = sub.sort_values(PL_DIST).drop_duplicates("code")
    return dict(zip(sub["code"],
                    zip(sub[PL_DIST].astype(float), sub[PL_NAME].fillna("（名称なし）"))))


# ---------- 街の雰囲気 ----------
PLACE_COUNTS = {   # station_vibe に無いものだけ、ここで数える
    "n_playground": ["leisure=playground"],
}
FEATURE_LABEL = {
    "share_lowrise_res": "低層住居専用地域の割合", "share_midhigh_res": "中高層住居地域の割合",
    "share_commercial": "商業地域の割合", "share_industrial": "工業系地域の割合",
    "n_nightlife_500": "飲み屋の数", "n_shop_500": "お店の数", "n_restaurant_500": "飲食店の数",
    "n_cafe_500": "カフェの数", "n_park_1000": "公園の数", "n_childcare_1000": "保育園・幼稚園の数",
    "n_mall_1500": "大型商業施設の数", "n_playground": "遊び場の数",
}
VIBE_RULES = {     # キーは catalog.yaml の vibes と同じにする
    "quiet":  {"plus":  {"share_lowrise_res": 2},
               "minus": {"share_commercial": 1, "n_nightlife_500": 1, "n_restaurant_500": 0.5}},
    "modern": {"plus":  {"share_commercial": 1.5, "share_midhigh_res": 1, "n_cafe_500": 1, "n_mall_1500": 1},
               "minus": {"share_industrial": 1}},
    "lively": {"plus":  {"n_restaurant_500": 2, "n_nightlife_500": 1, "n_shop_500": 1, "share_commercial": 1}},
    "family": {"plus":  {"n_playground": 1.5, "n_childcare_1000": 1.5, "n_park_1000": 1, "share_lowrise_res": 1},
               "minus": {"n_nightlife_500": 1}},
    "green":  {"plus":  {"n_park_1000": 2, "share_lowrise_res": 1},
               "minus": {"share_commercial": 1}},
}



def _build_features() -> pd.DataFrame:
    f = pd.read_parquet(DATA / "station_vibe.parquet")
    f["code"] = f[VB_GROUP].map(norm_code)
    f = f.drop_duplicates("code").set_index("code")
    near = places[places[PL_DIST] <= DEFAULT_WITHIN]
    for col, cats in PLACE_COUNTS.items():
        cnt = near[near[PL_CAT].isin(cats)].groupby("code").size()
        f[col] = cnt.reindex(f.index).fillna(0)
    return f


FEAT = _build_features()
_missing = sorted({c for r in VIBE_RULES.values() for d in r.values() for c in d} - set(FEAT.columns))
if _missing:
    print("[flex] station_vibe に無い列なので無視します:", _missing)

_no_rule = set(CATALOG["vibes"]) - set(VIBE_RULES)
if _no_rule:
    print("[flex] catalog.yaml の vibes に対応するルールがありません:", sorted(_no_rule))



@lru_cache(maxsize=64)
def vibe_scores(key: str) -> dict:
    """雰囲気の点数（0〜1）と根拠 → {code: (点数, 根拠の文章)}"""
    rule = VIBE_RULES.get(key, {})
    parts, weights, plus_used = [], [], []
    for sign in ("plus", "minus"):
        for col, w in rule.get(sign, {}).items():
            if col not in FEAT.columns:
                continue
            p = FEAT[col].rank(pct=True).fillna(0.5)   # 1都3県の中で上位何%か
            parts.append((p if sign == "plus" else 1 - p) * w)
            weights.append(w)
            if sign == "plus":
                plus_used.append((col, p))
    if not parts:
        return {}
    score = sum(parts) / sum(weights)
    out = {}
    for code, s in score.items():
        tops = sorted(plus_used, key=lambda cp: -cp[1][code])[:2]
        reason = "、".join(f"{FEATURE_LABEL.get(c, c)}が上位{max(1, round((1 - p[code]) * 100))}%"
                          for c, p in tops)
        out[code] = (float(s), reason)
    return out


# ---------- 検索本体（engine.py を包む） ----------
def search_flex(plan, top_n: int = 20) -> dict:
    flex_conds = [c for c in plan.conditions if isinstance(c, (PlaceNearby, Vibe))]
    base_conds = [c for c in plan.conditions if not isinstance(c, (PlaceNearby, Vibe))]

    res = base_search(plan.model_copy(update={"conditions": base_conds}), top_n=100000)
    rows = res["results"] if isinstance(res, dict) else res
    if not flex_conds:
        return {"plan": plan, "results": rows[:top_n], "flex": []}

    info, lookups = [], []
    for c in flex_conds:
        if isinstance(c, PlaceNearby):
            r = resolve_place(c.query)
            info.append(r)
            if r["kind"]:                       # 見つからない言葉は条件から外す（画面で知らせる）
                lookups.append((c, r, nearest_places(r["kind"], r["key"])))
        else:
            lookups.append((c, None, vibe_scores(c.vibe)))

    n_base = len(base_conds)
    out = []
    for row in rows:
        code = norm_code(row.get("group_code"))
        total = float(row.get("score") or 0) * n_base if n_base else 0.0
        ev, ok = list(row.get("evidence", [])), True
        for c, r, table in lookups:
            cond, hit = c.model_dump(), table.get(code)
            if isinstance(c, PlaceNearby):
                within = c.within_m or DEFAULT_WITHIN
                cond["resolved"] = r["label"]
                if hit is None or hit[0] > within:
                    if c.importance == "must":
                        ok = False
                        break
                    s, val, name = 0.0, None, None
                else:
                    s, val, name = 1 - hit[0] / within, round(hit[0]), hit[1]
                ev.append({"condition": cond, "value": val, "name": name, "detail": r["label"]})
            else:
                score, reason = hit if hit else (0.0, "データなし")
                if c.importance == "must" and score < VIBE_MUST:
                    ok = False
                    break
                s = score
                cond["label"] = CATALOG["vibes"][c.vibe]["label"]
                ev.append({"condition": cond, "value": round(score, 2), "name": None, "detail": reason})
            total += s
        if ok:
            out.append({**row, "score": round(total / (n_base + len(lookups)), 3), "evidence": ev})

    out.sort(key=lambda x: -x["score"])
    return {"plan": plan, "results": out[:top_n], "flex": info}
