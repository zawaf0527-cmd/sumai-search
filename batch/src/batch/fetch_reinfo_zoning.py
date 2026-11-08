from pathlib import Path
import pandas as pd
from shapely.geometry import shape
from batch.common import station_points, tiles_around, fetch_tile, load_df

API, TABLE, Z = "XKT002", "reinfo_zoning", 14   # 都市計画決定GISデータ（用途地域）

def main():
    st = station_points()
    cache = Path(f"data/raw/reinfo/{API}")
    cache.mkdir(parents=True, exist_ok=True)
    tiles = set().union(*(tiles_around(r.lon, r.lat, Z, 800) for r in st.itertuples()))
    print(f"[{API}] {len(tiles)} タイル")
    rows = []
    for i, (z_, x, y) in enumerate(sorted(tiles), 1):
        for f in fetch_tile(API, z_, x, y, {}, cache).get("features", []):
            if f.get("geometry"):
                rows.append({"tile": f"{z_}/{x}/{y}", "wkt": shape(f["geometry"]).wkt,
                             **f["properties"]})
        if i % 200 == 0:
            print(f"  {i}/{len(tiles)}")
    df = pd.DataFrame(rows)
    before = len(df)
    df = df.drop_duplicates(subset=["wkt", "use_area_ja"])   # 隣のタイルと重なった同じ図形を除く
    print(f"重複除去: {before:,} → {len(df):,} 行")
    load_df(df, TABLE)

if __name__ == "__main__":
    main()
