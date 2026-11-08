{{ config(materialized='table') }}
-- 駅ごとの「雰囲気の材料」：用途地域の割合（駅800m円内）＋施設の数
with s as (
  select group_code, st_buffer(st_centroid(geom), 800) as buf
  from {{ ref('dim_stations') }}
),
z as (   -- 用途地域を5種類にまとめ、駅の円で切り取る
  select s.group_code,
    case when z.use_area like '%低層住居専用%' or z.use_area like '%田園住居%' then 'lowrise'
         when z.use_area like '%中高層住居専用%' then 'midhigh'
         when z.use_area like '%商業%' then 'commercial'
         when z.use_area like '%工業%' then 'industrial'
         else 'other' end as zone,
    st_intersection(z.geog, s.buf) as g
  from s join {{ ref('stg_reinfo__zoning') }} z on st_intersects(z.geog, s.buf)
),
zs as (  -- タイルの境目で重なった図形は1つにまとめてから面積を測る
  select group_code, zone, st_area(st_union_agg(g)) as m2
  from z group by group_code, zone
),
zp as (  -- 円の面積に対する割合（0〜1）
  select s.group_code,
    least(sum(if(zs.zone = 'lowrise',    zs.m2, 0)) / any_value(st_area(s.buf)), 1) as share_lowrise_res,
    least(sum(if(zs.zone = 'midhigh',    zs.m2, 0)) / any_value(st_area(s.buf)), 1) as share_midhigh_res,
    least(sum(if(zs.zone = 'commercial', zs.m2, 0)) / any_value(st_area(s.buf)), 1) as share_commercial,
    least(sum(if(zs.zone = 'industrial', zs.m2, 0)) / any_value(st_area(s.buf)), 1) as share_industrial
  from s left join zs using (group_code)
  group by s.group_code
),
pl as (  -- 施設の数（Part B の station_places から数える）
  select group_code,
    countif(dist_m <= 500 and category in ('amenity=bar','amenity=pub','amenity=nightclub',
            'amenity=karaoke_box','leisure=adult_gaming_centre','amenity=gambling')) as n_nightlife_500,
    countif(dist_m <= 500 and starts_with(category, 'shop='))                         as n_shop_500,
    countif(dist_m <= 500 and category in ('amenity=restaurant','amenity=fast_food')) as n_restaurant_500,
    countif(dist_m <= 500 and category = 'amenity=cafe')                              as n_cafe_500,
    countif(dist_m <= 1000 and category = 'leisure=park')                             as n_park_1000,
    countif(dist_m <= 1000 and category in ('amenity=kindergarten','amenity=childcare')) as n_childcare_1000,
    countif(dist_m <= 1500 and category = 'shop=mall')                                as n_mall_1500
  from {{ ref('station_places') }}
  group by group_code
)
select zp.*,
  ifnull(n_nightlife_500, 0)  as n_nightlife_500,
  ifnull(n_shop_500, 0)       as n_shop_500,
  ifnull(n_restaurant_500, 0) as n_restaurant_500,
  ifnull(n_cafe_500, 0)       as n_cafe_500,
  ifnull(n_park_1000, 0)      as n_park_1000,
  ifnull(n_childcare_1000, 0) as n_childcare_1000,
  ifnull(n_mall_1500, 0)      as n_mall_1500
from zp left join pl using (group_code)
