import os
from pathlib import Path
from google.cloud import bigquery

OUT = Path("api/data")
TABLES = ["station_features", "station_poi", "travel_time_v0" , "transit_nodes", "transit_edges","station_places","place_categories","station_vibe"]

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    client = bigquery.Client(project=os.environ["GCP_PROJECT"])
    for t in TABLES:
        df = client.query(f"select * from marts.{t}").to_dataframe()
        df.to_parquet(OUT / f"{t}.parquet", index=False)
        print(f"{t}: {len(df):,} 行")

if __name__ == "__main__":
    main()