"""Ollamaとのやり取り。LLMは『条件の構造化』と『説明文』だけを担当し、順位は決めない"""
import json, os
import httpx, yaml
from pydantic import ValidationError
from schemas import CATALOG, SearchPlan

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434") 
MODEL = os.environ.get("OLLAMA_MODEL", "qwen3.5:27b") # 選択肢：gpt-oss:20b,qwen3:14b,qwen3:30b-a3b,qwen3.5:27b
THINKING_MODELS = ("qwen3", "deepseek-r1")   # 考える過程を出力するタイプのモデル


def chat(system: str, user: str, schema: dict, temperature: float = 0.0) -> str:
    payload = {
        "model": MODEL, "stream": False,
        "format": schema,                                    # このJSONの形でしか答えさせない
        "options": {"temperature": temperature, "num_ctx": 8192},
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
    }
    if MODEL.startswith(THINKING_MODELS):
        payload["think"] = False                             # 思考過程は不要（速度優先）
    r = httpx.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=300)
    if r.status_code == 400 and "think" in payload and "think" in r.text:
        payload.pop("think")       # think非対応のモデルなら、外してやり直す
        r = httpx.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=300)
    r.raise_for_status()
    return r.json()["message"]["content"]


PARSE_SYSTEM = f"""あなたは住まい探しの希望を、検索条件JSONに変換する係です。
ルール:
- 各条件には必ず "type"（commute / area_metric / poi_proximity のいずれか）を入れる。
- ユーザーが書いていない条件は絶対に追加しない。希望1つにつき条件は最大1つ。
- 条件の種類は次の5つ。上から順に当てはまるものを使う。
  1. commute：「〇〇まで△分」「乗換◯回」
  2. area_metric：予算・土地の広さ・災害リスク（カタログの area_metrics にあるもの）
  3. poi_proximity：カタログの poi のカテゴリにある施設（大きな公園、ゴルフ場、スーパー等）
  4. place_nearby：それ以外の店名・チェーン名・施設（成城石井、オーケー、コストコ、温泉、図書館、ジム等）。query には名詞だけを入れる（「成城石井がある駅」→「成城石井」）
  5. vibe：街の雰囲気・印象（静か、洗練、下町、子育て、緑が多い等）。カタログの vibes の hint を見て、最も近いキーを1つ選ぶ
- unsupported に入れてよいのは、5つのどれにも当てはまらない希望だけ（例：富士山が見える、治安が良い）。店名・施設名・雰囲気は unsupported に入れない。
- 「徒歩5分」は within_m=400、「徒歩10分」は within_m=800。
- 駅名の推薦や順位付けは絶対にしない。変換だけを行う。
- 「〇〇まで△分」は commute。dest_station は駅名のみ(「駅」は付けない)。「1時間」は60分。
- 予算は円に換算(5000万円→50000000)し、metric=house_price_median, importance=must。
- 「庭付き」「広い土地」は share_land_150、「水害」「浸水」「川の氾濫」は flood_share、「土砂崩れ」「がけ崩れ」は landslide_share。
- 明確な必須条件以外は importance=want。
- unsupported には「評価できない部分だけ」を短く抜き出す。原文全体を入れない
- 「車で〇〇に行く」「週末は〇〇に行く」のように行動として書かれた希望も、カタログにあれば条件にする
- 「〇〇はなくても構わない」は条件に入れない
- 「乗り換えX回以内」「乗り換えなし（直通・1本で）」は commute の max_transfers に入れる（なし=0）。書いていなければ null

入力：「成城石井がある駅で静かな街、東京まで乗換1回」
出力：{{"conditions":[
 {{"type":"place_nearby","query":"成城石井","within_m":null,"importance":"want"}},
 {{"type":"vibe","vibe":"quiet","importance":"want"}},
 {{"type":"commute","dest_station":"東京","max_minutes":null,"max_transfers":1}}],
 "unsupported":[]}}

例1:
入力「品川まで50分、4000万円以内、ドッグランが近い、日当たりがいい」
出力 {{"conditions":[
  {{"type":"commute","dest_station":"品川","max_minutes":50}},
  {{"type":"area_metric","metric":"house_price_median","max_value":40000000,"importance":"must"}},
  {{"type":"poi_proximity","category":"dog_park","importance":"want"}}],
 "unsupported":["日当たりがいい"]}}

例2:
入力「川の近くは避けたい。駅前にスーパーがほしい」
出力 {{"conditions":[
  {{"type":"area_metric","metric":"flood_share","importance":"want"}},
  {{"type":"poi_proximity","category":"supermarket","importance":"want"}}],
 "unsupported":[]}}

カタログ:
{yaml.safe_dump(CATALOG, allow_unicode=True)}

- 具体的な店名・チェーン名（成城石井、オーケー、コストコ等）や、カタログの category に無い施設の種類（温泉、図書館、ジム等）は place_nearby を使う。query にはユーザーの言葉から名詞だけを入れる（「成城石井がある駅」→「成城石井」）。
- カタログの category にある施設（大きな公園、ゴルフ場など）は従来どおり poi_proximity を使う。
- 街の雰囲気・印象（静か、洗練、下町、子育て、緑が多い等）は vibe を使い、カタログの vibes の hint を見て最も近いものを1つ選ぶ。どれにも当てはまらなければ unsupported に原文で入れる。
- 「徒歩5分」は within_m=400、「徒歩10分」は within_m=800 とする。

"""



def parse_text(text: str) -> SearchPlan:
    schema = SearchPlan.model_json_schema()
    user, last_error = text, None
    for _ in range(2):
        content = chat(PARSE_SYSTEM, user, schema)
        try:
            return SearchPlan.model_validate_json(content)
        except ValidationError as e:
            last_error = e
            user = (f"{text}\n\n（前回の出力は形式エラーでした: {e.errors()[0]['msg']}。"
                    "各条件に必ず type を入れ、カタログ内の値だけを使ってください）")
    raise ValueError(f"条件を読み取れませんでした: {last_error}")

