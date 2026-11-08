select
  cast(line_cd as int64)   as line_cd,
  line_name,
  cast(line_type as int64) as line_type   -- 1:新幹線 2:一般 3:地下鉄 4:路面電車 5:モノレール・新交通
from {{ source('raw', 'ekidata_line') }}
