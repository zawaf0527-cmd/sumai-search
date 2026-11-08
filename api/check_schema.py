"""SearchPlan のスキーマに新しい部品が入っているか確認する"""
import json
from schemas import SearchPlan

s = json.dumps(SearchPlan.model_json_schema(), ensure_ascii=False)
print("place_nearby:", "place_nearby" in s)
print("vibe        :", '"vibe"' in s)

# conditions に入っている部品の一覧を表示する
defs = SearchPlan.model_json_schema().get("$defs", {})
print("部品の一覧  :", list(defs.keys()))
