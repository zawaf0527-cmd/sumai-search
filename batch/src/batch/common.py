"""API取得・タイル計算・BigQueryロードの共通部品"""
import json, math, os, time
from pathlib import Path

import pandas as pd
import requests
from google.cloud import bigquery

PROJECT = os.environ["GCP_PROJECT"]
API_KEY = os.environ["REINFOLIB_API_KEY"]
BASE = "https://www.reinfolib.mlit.go.jp/ex-api/external"


def lonlat_to_tile(lon, lat, z):
    """経度緯度 → 地図タイル番号(x, y)。地図を格子状に切ったときの『マス目の番地』"""
    n = 2 ** z
    x = int((lon + 180) / 360 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return x, y


def tiles_around(lon, lat, z, r_m=0):
    """駅から半径 r_m メートルを覆うタイルの集合"""
    dlat = r_m / 111_320
    dlon = r_m / (111_320 * math.cos(math.radians(lat)))
    x0, y0 = lonlat_to_tile(lon - dlon, lat + dlat, z)
    x1, y1 = lonlat_to_tile(lon + dlon, lat - dlat, z)
    return {(z, x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def station_points():
    sql = "select group_code, st_x(geom) as lon, st_y(geom) as lat from marts.dim_stations"
    return bigquery.Client(project=PROJECT).query(sql).to_dataframe()


SESSION = requests.Session()   # 接続を使い回す（毎回つなぎ直さないので相手にも優しい）
FAILED = []                    # 取れなかったタイルの記録

def fetch_tile(api, z, x, y, extra, cache_dir: Path):
    """1タイル取得。取得済みならファイルから読む（途中で止まっても続きから再開できる）"""
    path = cache_dir / f"{z}_{x}_{y}.geojson"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    params = {"response_format": "geojson", "z": z, "x": x, "y": y, **extra}

    r = None
    for attempt in range(5):
        try:
            r = SESSION.get(f"{BASE}/{api}", params=params,
                            headers={"Ocp-Apim-Subscription-Key": API_KEY},
                            timeout=(10, 120))   # (接続待ち10秒, 応答待ち120秒)
        except requests.exceptions.RequestException as e:
            wait = 10 * (attempt + 1)
            print(f"  通信エラー {z}/{x}/{y}（{type(e).__name__}）{wait}秒後に再試行")
            time.sleep(wait)
            continue
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(10 * (attempt + 1))
            continue
        break
    else:
        FAILED.append((api, z, x, y))   # 5回ダメなら諦めて次へ。保存しないので再実行で再挑戦される
        return {"features": []}

    if r.status_code == 204 or not r.content:
        data = {"features": []}
    elif r.status_code != 200:
        print(f"  警告 {api} {z}/{x}/{y}: HTTP {r.status_code}（スキップ）")
        FAILED.append((api, z, x, y))
        return {"features": []}
    else:
        data = r.json()
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    time.sleep(0.5)  # 国のサーバーに優しく（0.3→0.5秒に延長）
    return data


def load_df(df: pd.DataFrame, table: str):
    """DataFrameを raw.<table> に全件入れ替えでロード（全部文字列のまま）"""
    client = bigquery.Client(project=PROJECT)
    job = client.load_table_from_dataframe(
        df.astype("string"), f"{PROJECT}.raw.{table}",
        job_config=bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE"))
    job.result()
    print(f"raw.{table}: {len(df):,} 行ロード")
