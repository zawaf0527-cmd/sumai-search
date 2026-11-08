{{ config(materialized='table') }}
select osm_id, category, name, st_geogfromtext(wkt, make_valid => true) as geog
from {{ source('raw', 'osm_poi') }}