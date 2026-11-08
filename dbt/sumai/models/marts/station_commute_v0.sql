-- 一番近いターミナルまでの直線距離(km) × 1.5分 + 10分（乗り換えや徒歩の時間）
-- あくまで仮の近似。後で路線のつながりを使う v1 に置き換える
with d as (
  select s.group_code, t.terminal_name,
         st_distance(s.geom, st_geogpoint(t.lon, t.lat)) / 1000 as km   -- 2点間の距離（m→km）
  from {{ ref('dim_stations') }} s
  cross join {{ ref('terminals') }} t      -- 全駅 × 全ターミナルの組み合わせを作る
)
select
  group_code,
  array_agg(terminal_name order by km limit 1)[offset(0)] as nearest_terminal,  -- 一番近いターミナル
  round(min(km), 1) as distance_km,
  cast(round(min(km) * 1.5 + 10) as int64) as commute_min_v0
from d
group by group_code
