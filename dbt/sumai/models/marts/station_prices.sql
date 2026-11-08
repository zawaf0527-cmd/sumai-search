-- 駅ごとの戸建て相場。取引が少ない駅は外れ値が相場扱いされるので null にする
{% set min_n = var('min_house_tx', 5) %}

with p as (
  select * from {{ ref('stg_reinfo__prices') }}
  where land_type like '%土地と建物%'
    and coalesce(building_use, '住宅') like '%住宅%'
    and price_yen > 0
),
matched as (   -- 取引点を、300m以内で一番近い駅グループに紐づける
  select p.*, s.group_code
  from p join {{ ref('dim_stations') }} s on st_dwithin(p.geom, s.geom, 300)
  where true
  qualify row_number() over (partition by p.tx_id order by st_distance(p.geom, s.geom)) = 1
),
agg as (       -- いったん全駅分を集計
  select
    group_code,
    count(*) as n_house_tx,
    approx_quantiles(price_yen, 2)[offset(1)]    as house_price_median,
    approx_quantiles(land_area_m2, 2)[offset(1)] as land_area_median,
    countif(land_area_m2 >= 150) / count(*)      as share_land_150
  from matched
  group by group_code
)
select
  group_code,
  n_house_tx,
  n_house_tx >= {{ min_n }} as price_reliable,   -- 相場として信頼できるか
  case when n_house_tx >= {{ min_n }} then house_price_median end as house_price_median,
  case when n_house_tx >= {{ min_n }} then land_area_median   end as land_area_median,
  case when n_house_tx >= {{ min_n }} then share_land_150     end as share_land_150
from agg
