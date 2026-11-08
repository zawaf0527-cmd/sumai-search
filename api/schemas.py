from pathlib import Path
from typing import Annotated, Literal, Union
import yaml
from pydantic import BaseModel, Field

CATALOG = yaml.safe_load((Path(__file__).parent / "catalog.yaml").read_text(encoding="utf-8"))
MetricName = Literal[tuple(CATALOG["area_metrics"])]
PoiName = Literal[tuple(CATALOG["poi"])]
Importance = Literal["must", "want"]

class Commute(BaseModel):
    type: Literal["commute"]
    dest_station: str = Field(description="行き先の駅名。例: 大手町")
    max_minutes: int = Field(ge=5, le=180)
    max_transfers: int | None = None   # 乗り換え回数の上限（None = 制限なし）


class AreaMetric(BaseModel):
    type: Literal["area_metric"]
    metric: MetricName
    max_value: float | None = None
    min_value: float | None = None
    importance: Importance = "want"

class PoiProximity(BaseModel):
    type: Literal["poi_proximity"]
    category: PoiName
    within_m: int | None = Field(default=None, le=15000)
    importance: Importance = "want"

class PlaceNearby(BaseModel):
    """店名・施設の種類（成城石井、温泉など）。何に当たるかは flex.py が決める"""
    type: Literal["place_nearby"]
    query: str                                   # ユーザーの言葉（名詞だけ）
    within_m: int | None = None                  # 未指定なら800m（徒歩10分）
    importance: Literal["must", "want"] = "want"


class Vibe(BaseModel):
    """街の雰囲気。catalog.yaml の vibes のキーからしか選べない"""
    type: Literal["vibe"]
    vibe: Literal[tuple(CATALOG["vibes"].keys())]
    importance: Literal["must", "want"] = "want"

Condition = Annotated[Union[Commute, AreaMetric, PoiProximity, PlaceNearby, Vibe],
                      Field(discriminator="type")]

class SearchPlan(BaseModel):
    conditions: list[Condition]
    unsupported: list[str] = Field(default_factory=list, description="カタログで表せない希望(原文)")
