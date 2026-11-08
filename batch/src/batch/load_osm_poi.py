import osmium
import pandas as pd
from batch.common import load_df

PBF = "data/raw/osm/kanto-261102.osm.pbf"
RULES = [  # (OSMタグのキー, 値, 自分のカテゴリ名)
    ("shop", "mall", "mall"),
    ("shop", "supermarket", "supermarket"),
    ("leisure", "golf_course", "golf_course"),
    ("leisure", "park", "park"),
    ("leisure", "dog_park", "dog_park"),
    ("amenity", "hospital", "hospital"),
]

def classify(tags):
    for k, v, cat in RULES:
        if tags.get(k) == v:
            return cat
    return None

class PoiHandler(osmium.SimpleHandler):
    def __init__(self):
        super().__init__()
        self.fab = osmium.geom.WKTFactory()
        self.rows = []

    def _add(self, oid, tags, make_wkt):
        cat = classify(tags)
        if not cat:
            return
        try:
            wkt = make_wkt()
        except Exception:
            return  # 形が壊れているデータは捨てる
        self.rows.append({"osm_id": oid, "category": cat, "name": tags.get("name"), "wkt": wkt})

    def node(self, n):   # 点で登録された施設
        self._add(f"n{n.id}", n.tags, lambda: self.fab.create_point(n))

    def area(self, a):   # 敷地(面)で登録された施設
        self._add(f"a{a.id}", a.tags, lambda: self.fab.create_multipolygon(a))

def main():
    h = PoiHandler()
    h.apply_file(PBF, locations=True)
    df = pd.DataFrame(h.rows)
    print(df.category.value_counts())
    load_df(df, "osm_poi")

if __name__ == "__main__":
    main()
