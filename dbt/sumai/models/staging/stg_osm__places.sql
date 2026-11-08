{{ config(materialized='table') }}
with src as (
  select *,
    safe_cast(lon as float64) as lon_f,   -- 文字列 → 数値
    safe_cast(lat as float64) as lat_f
  from {{ source('raw', 'osm_places') }}
)
select
  osm_id, key, value,
  concat(key, '=', value) as category,          -- 例：shop=supermarket
  name, brand,
  st_geogpoint(lon_f, lat_f) as geom,
  -- 検索用の文字列。全角半角をそろえ（NFKC）、空白を消し、小文字にする
  lower(regexp_replace(normalize(
    concat(ifnull(brand, ''), ' ', ifnull(brand_en, ''), ' ', ifnull(name, '')), NFKC), r'\s', '')) as search_text
from src
where lon_f is not null and lat_f is not null   -- 数値にできなかった行は捨てる
