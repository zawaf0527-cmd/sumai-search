"""OSMから施設・お店をほぼ全部取り出して raw.osm_places に入れる"""
import osmium
import pandas as pd
from batch.common import load_df

PBF = "data/raw/osm/kanto-261102.osm.pbf"
KEYS = ["shop", "amenity", "leisure", "tourism", "healthcare", "historic"]
SKIP = {"parking", "parking_space", "bicycle_parking", "motorcycle_parking", "bench",
        "waste_basket", "waste_disposal", "recycling", "vending_machine", "toilets",
        "telephone", "post_box", "drinking_water", "shelter", "parking_entrance", "yes"}
BBOX = (138.9, 34.85, 140.9, 36.3)   # 1都3県をざっくり囲む（経度・緯度の最小/最大）


def in_bbox(lon, lat):
    return BBOX[0] <= lon <= BBOX[2] and BBOX[1] <= lat <= BBOX[3]


class H(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.rows = []

    def _add(self, o, oid, lon, lat):
        if not in_bbox(lon, lat):
            return
        t = o.tags
        for k in KEYS:
            v = t.get(k)
            if v and v not in SKIP:
                self.rows.append(dict(
                    osm_id=oid, key=k, value=v,
                    name=t.get("name:ja") or t.get("name"),
                    brand=t.get("brand:ja") or t.get("brand"),
                    brand_en=t.get("brand:en"),
                    lon=lon, lat=lat))
                return            # 1つの施設は1行だけ

    def node(self, n):
        if n.location.valid():
            self._add(n, f"n{n.id}", n.location.lon, n.location.lat)

    def area(self, a):            # 建物や敷地として描かれた施設は、外周の平均を代表点にする
        for ring in a.outer_rings():
            pts = [(nd.location.lon, nd.location.lat) for nd in ring if nd.location.valid()]
            if pts:
                lon = sum(p[0] for p in pts) / len(pts)
                lat = sum(p[1] for p in pts) / len(pts)
                self._add(a, f"a{a.id}", lon, lat)
            return


def main():
    h = H()
    h.apply_file(PBF, locations=True)
    df = pd.DataFrame(h.rows)
    print(df["key"].value_counts())
    print("ブランド付き:", df["brand"].notna().sum(), "件")
    load_df(df, "osm_places")


if __name__ == "__main__":
    main()
