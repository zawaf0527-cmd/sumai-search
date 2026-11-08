{{ config(materialized='table') }}
select
  safe_cast(A31a_205 as int64) as depth_rank,  -- 浸水深ランク
  st_geogfromtext(wkt, make_valid => true) as geog
from {{ source('raw', 'reinfo_flood') }}