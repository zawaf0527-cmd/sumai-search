-- 営業中で、1都3県（埼玉11・千葉12・東京13・神奈川14）の駅×路線だけ
select
  cast(station_cd as int64)   as station_cd,
  cast(station_g_cd as int64) as station_g_cd,
  replace(station_name, 'ヶ', 'ケ') as station_name,
  cast(line_cd as int64)      as line_cd,
  st_geogpoint(cast(lon as float64), cast(lat as float64)) as geom
from {{ source('raw', 'ekidata_station') }}
where cast(e_status as int64) = 0
  and cast(pref_cd as int64) between 11 and 14
