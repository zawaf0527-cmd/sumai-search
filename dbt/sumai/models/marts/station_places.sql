{{ config(materialized='table') }}
select
  s.group_code, p.category, p.name, p.brand, p.search_text,
  cast(round(st_distance(s.geom, p.geom)) as int64) as dist_m
from {{ ref('dim_stations') }} s
join {{ ref('stg_osm__places') }} p
  on st_dwithin(s.geom, p.geom, 1500)
