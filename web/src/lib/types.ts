export type Importance = "must" | "want";

// ---------- 検索条件（api\schemas.py と同じ形） ----------
export type Commute = {
  type: "commute"; dest_station: string; max_minutes: number | null; max_transfers?: number | null;
};
export type AreaMetric = {
  type: "area_metric"; metric: string; max_value: number | null; min_value: number | null; importance: Importance;
};
export type PoiProximity = {
  type: "poi_proximity"; category: string; within_m: number | null; importance: Importance;
};
export type PlaceNearbyCondition = {
  type: "place_nearby"; query: string; within_m?: number | null; importance: Importance;
  resolved?: string;   // flex.py が付ける「どう解釈したか」
};
export type VibeCondition = {
  type: "vibe"; vibe: string; importance: Importance;
  label?: string;      // flex.py が付ける日本語名
};
export type FlexCondition = PlaceNearbyCondition | VibeCondition;
export type Condition = Commute | AreaMetric | PoiProximity | FlexCondition;
export type SearchPlan = { conditions: Condition[]; unsupported: string[] };

// ---------- 検索結果 ----------
export type Evidence = {
  condition: Condition; value: number | null; name: string | null;
  detail?: string | null;   // 雰囲気の根拠・店名の解釈
};
export type StationResult = {
  group_code?: string; station: string; city: string | null;
  lat: number; lon: number; score: number; evidence: Evidence[];
};
export type FlexInfo = {
  query: string; kind: "name" | "category" | null; label: string;
  sim: number; n_stations: number; best_cat?: string;
};
export type SearchResponse = { plan: SearchPlan; results: StationResult[]; flex?: FlexInfo[] };

// ---------- 説明文 ----------
export type ExplainItem = { station: string; summary: string; facts: string[]; source: "llm" | "template" };
export type ExplainResponse = { items: ExplainItem[]; notes: string[] };
