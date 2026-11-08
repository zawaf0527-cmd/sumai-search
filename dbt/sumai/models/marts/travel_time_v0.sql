-- v0：直線距離×1.5分＋10分。v1で乗換込みの計算に差し替える（列の形は同じにする）
select
  o.group_code as origin_group,
  d.group_code as dest_group,
  if(o.group_code = d.group_code, 0,
     cast(round(st_distance(o.geom, d.geom) / 1000 * 1.5 + 10) as int64)) as minutes
from {{ ref('dim_stations') }} o
cross join {{ ref('dim_stations') }} d
