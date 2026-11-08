from pathlib import Path
import pandas as pd
from shapely.geometry import shape
from batch.common import station_points, tiles_around, fetch_tile, load_df

TARGETS = {  # API名: (rawテーブル名, ズーム)
    "XKT026": ("reinfo_flood", 14),      # 洪水浸水想定区域（想定最大規模）
    "XKT029": ("reinfo_landslide", 14),  # 土砂災害警戒区域
}

def main():
    st = station_points()
    for api, (table, z) in TARGETS.items():
        cache = Path(f"data/raw/reinfo/{api}")
        cache.mkdir(parents=True, exist_ok=True)
        tiles = set().union(*(tiles_around(r.lon, r.lat, z, 800) for r in st.itertuples()))
        print(f"[{api}] {len(tiles)} タイル")
        rows = []
        for i, (z_, x, y) in enumerate(sorted(tiles), 1):
            for f in fetch_tile(api, z_, x, y, {}, cache).get("features", []):
                if f.get("geometry"):
                    rows.append({"tile": f"{z_}/{x}/{y}", "wkt": shape(f["geometry"]).wkt,
                                 **f["properties"]})
            if i % 200 == 0:
                print(f"  {i}/{len(tiles)}")
        load_df(pd.DataFrame(rows), table)

if __name__ == "__main__":
    main()
