import pandas as pd
from flex import resolve_place, vibe_scores, norm_code
from schemas import CATALOG

for q in ["成城石井", "オーケーストア", "コストコ", "スタバ", "温泉", "銭湯",
          "図書館", "ジム", "ゴルフ練習場", "病院"]:
    r = resolve_place(q)
    print(f"{q:10} → {r['kind']!s:9} {r['label']}  類似度{r['sim']}  {r['n_stations']}駅")

names = pd.read_parquet("data/transit_nodes.parquet")
names = dict(zip(names["group_code"].map(norm_code), names["station_name"]))
for k in CATALOG["vibes"]:
    top = sorted(vibe_scores(k).items(), key=lambda kv: -kv[1][0])[:5]
    print(f"\n[{k}]", " / ".join(f"{names.get(c, c)} {s:.2f}" for c, (s, _) in top))
    print(f"{q:8} → {r['kind']!s:9} {r['label']}  {r['n_stations']}駅  "
          f"（一番近い種類: {r['best_cat']} 類似度{r['sim']}）")
