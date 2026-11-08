"""駅データ.jp の CSV を BigQuery raw に入れるだけ（加工は dbt で行う）"""
import glob
import pandas as pd
from batch.common import load_df

SPECS = {
    "ekidata_station": "data/raw/ekidata/station*.csv",
    "ekidata_line":    "data/raw/ekidata/line*.csv",
    "ekidata_join":    "data/raw/ekidata/join*.csv",
}

def main():
    for table, pattern in SPECS.items():
        path = sorted(glob.glob(pattern))[-1]          # 複数あれば最新のもの
        df = pd.read_csv(path, encoding="utf-8-sig")
        load_df(df, table)
        print(f"raw.{table}: {len(df):,} 行ロード（{path}）")

if __name__ == "__main__":
    main()
