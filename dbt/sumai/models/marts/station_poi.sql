with base as (
  select category, name, geog, st_area(geog) as area_m2 from {{ ref('stg_osm__poi') }}
),
poi as (  -- 「大型」はここで定義。カタログとの対応はこのSQLで管理する
  select * from base where category <> 'mall'
  union all select 'large_shopping_mall', name, geog, area_m2 from base
    where category = 'mall' and area_m2 >= 20000
  union all select 'large_park', name, geog, area_m2 from base
    where category = 'park' and area_m2 >= 30000
)
select
  s.group_code,
  p.category,
  min(st_distance(s.geom, p.geog)) as nearest_m,
  array_agg(p.name ignore nulls order by st_distance(s.geom, p.geog) limit 1)[safe_offset(0)] as nearest_name,
  countif(st_distance(s.geom, p.geog) <= 1000) as cnt_1km
from {{ ref('dim_stations') }} s
join poi p on st_dwithin(s.geom, p.geog, 15000)
group by 1, 2
