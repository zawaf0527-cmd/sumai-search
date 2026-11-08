from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from schemas import SearchPlan
from engine import search
from flex import search_flex 

app = FastAPI(title="住むエリア検索")

class ParseRequest(BaseModel):
    text: str

@app.post("/search")
def search_api(plan: SearchPlan):
    try:
        res = search_flex(plan)
    except ValueError as e:              # 「駅が見つかりません」など
        raise HTTPException(status_code=400, detail=str(e))
    # 画面は {"plan": ..., "results": [...]} の形を前提にしているので、形をそろえる
    return res if isinstance(res, dict) else {"plan": plan, "results": res}

@app.post("/parse", response_model=SearchPlan)
def parse(req: ParseRequest):
    from llm import parse_text   # Phase 6で作成
    return parse_text(req.text)

from fastapi import HTTPException
from pydantic import BaseModel
from llm import parse_text
from schemas import SearchPlan

class ParseRequest(BaseModel):
    text: str

@app.post("/parse", response_model=SearchPlan)
def parse(req: ParseRequest):
    """自然文 → 検索計画(JSON)。順位は決めない"""
    try:
        return parse_text(req.text)
    except ValueError as e:          # 2回試してもスキーマに合わなかった場合
        raise HTTPException(status_code=422, detail=str(e))

from explain import explain as run_explain, ExplainResponse

class ExplainRequest(BaseModel):
    plan: SearchPlan
    results: list[dict]      # /search の結果をそのまま渡す
    top_n: int = 5

@app.post("/explain", response_model=ExplainResponse)
def explain_endpoint(req: ExplainRequest):
    return run_explain(req.plan, req.results, req.top_n)