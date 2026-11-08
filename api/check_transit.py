"""transit.py が正しく動くか、有名な区間で確かめる"""
import transit

names = transit.nodes.drop_duplicates("group_code").set_index("group_code")["station_name"].to_dict()

for dest, origin_kw, k in [("東京", "大宮", None), ("一之江", "豊洲", 1),
                           ("一之江", "大門", 1), ("新宿", "町田", 0)]:
    t = transit.commute_table(dest, k)
    if t is None:
        print(f"目的駅「{dest}」が見つかりません")
        continue
    hits = [(names.get(g), r) for g, r in t.items() if origin_kw in str(names.get(g))]
    if not hits:
        print(f"{origin_kw} → {dest}（乗換上限 {k}）: 到達できません")
    for n, r in hits[:1]:
        print(f"{n} → {dest}（乗換上限 {k}）: {r.minutes}分 乗換{r.transfers}回 {r.text}")
