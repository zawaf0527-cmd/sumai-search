{{ config(materialized='table') }}
select
  safe_cast(A33_002 as int64) as zone_class,   -- 1:警戒区域 2:特別警戒区域
  st_geogfromtext(wkt, make_valid => true) as geog
from {{ source('raw', 'reinfo_landslide') }}
