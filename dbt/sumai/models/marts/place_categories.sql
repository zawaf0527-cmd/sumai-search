select category, count(*) as n
from {{ ref('stg_osm__places') }}
group by category
having n >= 20
order by n desc
