{{ config(materialized='table') }}   -- 境界データは重いので作り置きする
select
  N03_007 as city_code,                       -- 市区町村コード（例：13101 = 千代田区）
  substr(N03_007, 1, 2) as pref_code,         -- 先頭2桁が都道府県コード（13 = 東京都）
  N03_001 as pref_name,
  concat(ifnull(N03_003, ''), ifnull(N03_004, '')) as city_name,  -- 例：「横浜市」+「中区」
  st_geogfromtext(geometry_wkt, make_valid => true) as geom
from {{ source('raw', 'n03_admin') }}
where N03_007 is not null
