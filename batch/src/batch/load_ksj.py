"""国土数値情報を GCS に保存し、BigQuery の raw にそのまま読み込む（加工はしない）。"""
import glob
import os
from datetime import datetime, timezone

import geopandas as gpd          # 地図データを扱える「表計算」ライブラリ
import pandas as pd              # 表データを扱うライブラリ
from google.cloud import bigquery, storage   # GCPを操作するための公式ライブラリ

# .env に書いた値を読み込む
PROJECT = os.environ["GCP_PROJECT"]
BUCKET = os.environ["RAW_BUCKET"]

# 「BigQueryでのテーブル名: (探すファイル, 倉庫での保存場所)」の対応表
SPECS = {
    "n02_station":    ("data/raw/N02/**/UTF-8/*Station*.geojson", "ksj/N02/2025"),
    "n03_admin":      ("data/raw/N03/**/*.geojson",               "ksj/N03/latest"),
    "s12_passengers": ("data/raw/S12/**/UTF-8/*.geojson",         "ksj/S12/2024"),
}



def main() -> None:
    gcs = storage.Client(project=PROJECT).bucket(BUCKET)   # 倉庫につなぐ
    bq = bigquery.Client(project=PROJECT)                  # BigQueryにつなぐ
    for table, (pattern, prefix) in SPECS.items():
        files = sorted(glob.glob(pattern, recursive=True))  # サブフォルダも含めてファイルを探す
        assert files, f"ファイルが見つかりません: {pattern}"
        frames = []
        for f in files:
            print(f"[{table}] {f}")
            gcs.blob(f"{prefix}/{os.path.basename(f)}").upload_from_filename(f)  # ① 原本を倉庫へ
            g = gpd.read_file(f)                                                # ② GeoJSONを表として読む
            g["_source_file"] = os.path.basename(f)                             # どのファイル由来かを記録
            frames.append(g)
        gdf = pd.concat(frames, ignore_index=True)       # 4都県分などを1つの表にまとめる
        print(f"[{table}] 列名: {gdf.columns.tolist()}")
        # ③ 地図の形を文字列（WKT）に変換。例: "POINT (139.76 35.68)"
        df = gdf.to_wkt().rename(columns={"geometry": "geometry_wkt"})
        df["_loaded_at"] = datetime.now(timezone.utc)     # いつ読み込んだかを記録
        # ④ BigQuery の raw 棚へ。WRITE_TRUNCATE = 毎回中身を入れ替える（何度実行しても同じ結果）
        job = bq.load_table_from_dataframe(
            df,
            f"{PROJECT}.raw.{table}",
            job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"),
        )
        job.result()   # 読み込みが終わるまで待つ
        print(f"[{table}] {len(df)} 行を読み込みました")


if __name__ == "__main__":
    main()
