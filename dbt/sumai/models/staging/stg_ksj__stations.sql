select
  N02_005c as station_code,   -- 駅コード（路線ごとに別の番号）
  N02_005g as group_code,     -- グループコード（同じ名前で近くにある駅をまとめた番号）
  N02_005  as station_name,   -- 駅名
  N02_003  as line_name,      -- 路線名
  N02_004  as operator_name,  -- 鉄道会社
  st_geogfromtext(geometry_wkt, make_valid => true) as geom   -- 文字列（WKT）を地理データに変換
from {{ source('raw', 'n02_station') }}
