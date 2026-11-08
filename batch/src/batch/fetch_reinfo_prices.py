from pathlib import Path
import pandas as pd
from batch.common import station_points, tiles_around, fetch_tile, load_df

FROM, TO = "20221", "20254"   # 2022年1Q〜2025年4Q。期間を変えたらキャッシュフォルダを削除
CACHE = Path("data/raw/reinfo/XPT001")

def main():
    CACHE.mkdir(parents=True, exist_ok=True)
    st = station_points()
    tiles = set().union(*(tiles_around(r.lon, r.lat, 14, 300) for r in st.itertuples()))
    print(f"{len(tiles)} タイル取得します")
    rows = []
    for i, (z, x, y) in enumerate(sorted(tiles), 1):
        data = fetch_tile("XPT001", z, x, y,
                          {"from": FROM, "to": TO, "priceClassification": "01",
                           "landTypeCode": "01,02"}, CACHE)
        for j, f in enumerate(data.get("features", [])):
            lon, lat = f["geometry"]["coordinates"][:2]
            rows.append({"tx_id": f"{z}_{x}_{y}_{j}", "lon": lon, "lat": lat, **f["properties"]})
        if i % 100 == 0:
            print(f"  {i}/{len(tiles)}")
    load_df(pd.DataFrame(rows), "reinfo_prices")

if __name__ == "__main__":
    main()
