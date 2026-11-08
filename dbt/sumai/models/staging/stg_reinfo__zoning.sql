{{ config(materialized='table') }}
-- 用途地域：文字列(WKT)を図形に戻す。壊れた図形は make_valid で直す
select
  use_area_ja as use_area,
  st_geogfromtext(wkt, make_valid => true) as geog
from {{ source('raw', 'reinfo_zoning') }}
where wkt is not null
