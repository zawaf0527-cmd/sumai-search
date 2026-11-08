-- 駅データ.jp の駅を、国土数値情報ベースの group_code に結びつける
-- 500m以内で「同じ駅名」を優先、なければ一番近い駅
with e as (select * from {{ ref('stg_ekidata__stations') }}),
s as (
  select group_code, replace(station_name, 'ヶ', 'ケ') as station_name, geom
  from {{ ref('dim_stations') }}
),
m as (
  select e.station_cd, s.group_code
  from e join s on st_dwithin(e.geom, s.geom, 500)
  where true
  qualify row_number() over (
    partition by e.station_cd
    order by (e.station_name = s.station_name) desc, st_distance(e.geom, s.geom)
  ) = 1
)
select
  e.station_cd, e.station_g_cd, e.station_name,
  e.line_cd, l.line_name, l.line_type,
  m.group_code,                       -- 対応しない駅は null（つながりは残す）
  st_y(e.geom) as lat, st_x(e.geom) as lon
from e
join {{ ref('stg_ekidata__lines') }} l using (line_cd)
left join m using (station_cd)
where l.line_name not like '%新幹線%'   -- 新幹線は通勤の対象外にする
