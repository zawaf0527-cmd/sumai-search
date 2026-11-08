select
  group_code,
  any_value(station_name) as station_name,
  array_agg(distinct line_name ignore nulls) as lines,   -- 乗り入れ路線の一覧
  count(distinct line_name) as n_lines,                  -- 路線の数（多いほど便利な駅）
  st_centroid_agg(st_centroid(geom)) as geom             -- 各路線のホーム位置の中心点
from {{ ref('stg_ksj__stations') }}
group by group_code
