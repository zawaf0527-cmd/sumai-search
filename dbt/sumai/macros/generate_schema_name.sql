-- dbtは標準だと「stg_marts」のような名前の棚を勝手に作ってしまう。
-- Terraformで作った棚（stg / marts）の名前をそのまま使うための設定。
{% macro generate_schema_name(custom_schema_name, node) -%}
  {{ custom_schema_name if custom_schema_name else target.schema }}
{%- endmacro %}
