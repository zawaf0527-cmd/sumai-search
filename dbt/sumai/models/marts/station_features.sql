select
  s.group_code, s.station_name, s.city_name,
  st_x(s.geom) as lon, st_y(s.geom) as lat,
  p.n_house_tx, p.house_price_median, p.land_area_median, p.share_land_150,
  h.flood_share, h.flood_deep_share, h.landslide_share
from {{ ref('dim_stations') }} s
left join {{ ref('station_prices') }} p using (group_code)
left join {{ ref('station_hazard') }}  h using (group_code)
