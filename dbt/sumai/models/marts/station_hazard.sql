with buf as (
  select group_code, st_buffer(geom, 800) as buf from {{ ref('dim_stations') }}
),
flood_any as (
  select b.group_code, st_union_agg(st_intersection(b.buf, f.geog)) as g
  from buf b join {{ ref('stg_reinfo__flood') }} f on st_intersects(b.buf, f.geog)
  group by b.group_code
),
flood_deep as (
  select b.group_code, st_union_agg(st_intersection(b.buf, f.geog)) as g
  from buf b join {{ ref('stg_reinfo__flood') }} f on st_intersects(b.buf, f.geog)
  where f.depth_rank >= 3
  group by b.group_code
),
slide as (
  select b.group_code, st_union_agg(st_intersection(b.buf, l.geog)) as g
  from buf b join {{ ref('stg_reinfo__landslide') }} l on st_intersects(b.buf, l.geog)
  where st_dimension(l.geog) = 2
  group by b.group_code
)
select
  b.group_code,
  ifnull(st_area(fa.g), 0) / st_area(b.buf) as flood_share,
  ifnull(st_area(fd.g), 0) / st_area(b.buf) as flood_deep_share,
  ifnull(st_area(sl.g), 0) / st_area(b.buf) as landslide_share
from buf b
left join flood_any  fa using (group_code)
left join flood_deep fd using (group_code)
left join slide      sl using (group_code)
