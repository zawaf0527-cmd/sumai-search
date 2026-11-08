-- 「4,000万円」「1億2,000万円」のような文字列を数値(円)に変換する
with src as (select * from {{ source('raw', 'reinfo_prices') }}),
t as (
  select *, replace(u_transaction_price_total_ja, ',', '') as p from src
)
select
  tx_id,
  st_geogpoint(cast(lon as float64), cast(lat as float64)) as geom,
  land_type_name_ja      as land_type,
  building_use_name_ja   as building_use,
  point_in_time_name_ja  as period,
  coalesce(safe_cast(regexp_extract(p, r'(\d+)億') as int64), 0) * 100000000
    + coalesce(safe_cast(regexp_extract(p, r'(\d+)万') as int64), 0) * 10000 as price_yen,
  safe_cast(regexp_extract(replace(u_area_ja, ',', ''), r'([\d.]+)') as float64) as land_area_m2,
  safe_cast(regexp_extract(replace(u_building_total_floor_area_ja, ',', ''), r'([\d.]+)') as float64) as floor_area_m2
from t
