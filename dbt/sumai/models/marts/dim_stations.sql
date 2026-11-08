select g.*, a.pref_code, a.pref_name, a.city_code, a.city_name
from {{ ref('int_station_groups') }} g
join {{ ref('stg_ksj__admin_areas') }} a
  on st_intersects(a.geom, g.geom)              -- 「駅の点」が「市区町村の面」の中にあるか
where a.pref_code in ('11', '12', '13', '14')   -- 埼玉・千葉・東京・神奈川
qualify row_number() over (partition by g.group_code order by a.city_code) = 1  -- 境界上の駅の重複を除く
