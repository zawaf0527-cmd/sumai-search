-- 隣の駅までの所要時間 = 直線距離 ÷ 路線の種類ごとの平均速度（停車時間込み）
with j as (
  select cast(line_cd as int64) as line_cd,
         cast(station_cd1 as int64) as a_cd,
         cast(station_cd2 as int64) as b_cd
  from {{ source('raw', 'ekidata_join') }}
),
n as (select * from {{ ref('transit_nodes') }})
select
  j.line_cd, a.station_cd as from_cd, b.station_cd as to_cd,
  round(st_distance(st_geogpoint(a.lon, a.lat), st_geogpoint(b.lon, b.lat))) as dist_m,
  greatest(1.0, round(
    st_distance(st_geogpoint(a.lon, a.lat), st_geogpoint(b.lon, b.lat)) / 1000
        / case
        when regexp_contains(a.line_name, r'東京メトロ|都営(浅草|三田|新宿|大江戸)|地下鉄|りんかい') then 32
        when regexp_contains(a.line_name, r'都電|荒川線|世田谷線') then 13
        when regexp_contains(a.line_name, r'モノレール|ゆりかもめ|ライナー|シーサイド') then 27
        else 42 end * 60
  , 1)) as minutes
from j
join n a on j.a_cd = a.station_cd
join n b on j.b_cd = b.station_cd
