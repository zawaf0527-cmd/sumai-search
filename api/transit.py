"""乗り換えを考慮した所要時間。グラフは起動時に1回だけ組み立てる。
状態 = (乗り場, それまでの乗換回数)。行き先から逆向きにダイクストラ法で全駅への最短を求める。"""
import heapq, itertools
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import pandas as pd

PARQUET_DIR = Path(__file__).parent / "data"   # ← engine.py と同じ場所に合わせる
TRANSFER_MIN = 6      # 乗り換え1回の歩き＋待ち（分）
MAX_K = 3             # 乗り換えは3回まで計算する

nodes = pd.read_parquet(PARQUET_DIR / "transit_nodes.parquet")
edges = pd.read_parquet(PARQUET_DIR / "transit_edges.parquet")

info = nodes.set_index("station_cd").to_dict("index")
adj = defaultdict(list)                    # 乗車の辺（上り下りの両方向）
for f, t, m in edges[["from_cd", "to_cd", "minutes"]].itertuples(index=False):
    adj[f].append((t, m))
    adj[t].append((f, m))
same_station = nodes.groupby("station_g_cd")["station_cd"].apply(list).to_dict()

def _norm(name: str) -> str:
    return name.replace("ヶ", "ケ").removesuffix("駅").strip()

by_name = nodes.groupby(nodes["station_name"].map(_norm))["station_cd"].apply(list).to_dict()

@dataclass
class Route:
    minutes: int
    transfers: int
    text: str            # 例: "JR京浜東北線→東京メトロ東西線（乗換: 大手町）"

@lru_cache(maxsize=256)
def _search_from(dest_name: str):
    cds = by_name.get(_norm(dest_name))
    if not cds:
        return None
    starts = {cd for c in cds for cd in same_station[info[c]["station_g_cd"]]}
    tie = itertools.count()                 # 同じ時間のときの並び順用
    pq = [(0.0, next(tie), cd, 0, None) for cd in starts]
    heapq.heapify(pq)
    best = {}                               # (乗り場, 乗換回数) -> (分, ひとつ前の状態)
    while pq:
        cost, _, cd, k, prev = heapq.heappop(pq)
        if (cd, k) in best:
            continue
        best[(cd, k)] = (cost, prev)
        for nb, m in adj[cd]:                                   # そのまま乗る
            if (nb, k) not in best:
                heapq.heappush(pq, (cost + m, next(tie), nb, k, (cd, k)))
        if k < MAX_K:                                           # 同じ駅で別の路線に乗り換え
            for nb in same_station[info[cd]["station_g_cd"]]:
                if nb != cd and (nb, k + 1) not in best:
                    heapq.heappush(pq, (cost + TRANSFER_MIN, next(tie), nb, k + 1, (cd, k)))
    return best

def _describe(state, best) -> str:
    lines, via, cur = [], [], state
    while cur:                                   # 出発駅 → 行き先 の順にたどる
        cd, k = cur
        prev = best[cur][1]
        ln = info[cd]["line_name"]
        if not lines or lines[-1] != ln:
            lines.append(ln)
        if prev and prev[1] != k:
            via.append(info[cd]["station_name"])
        cur = prev
    return "→".join(lines) + (f"（乗換: {'・'.join(via)}）" if via else "")

@lru_cache(maxsize=256)
def commute_table(dest_name: str, max_transfers: int | None = None) -> dict | None:
    """{group_code: Route}。行き先の駅名が見つからなければ None"""
    best = _search_from(dest_name)
    if best is None:
        return None
    kmax = MAX_K if max_transfers is None else min(max_transfers, MAX_K)
    pick = {}
    for (cd, k), (cost, _) in best.items():
        g = info[cd]["group_code"]
        if k > kmax or pd.isna(g):
            continue
        if g not in pick or cost < pick[g][0]:
            pick[g] = (cost, k, (cd, k))
    return {g: Route(round(c), k, _describe(s, best)) for g, (c, k, s) in pick.items()}
