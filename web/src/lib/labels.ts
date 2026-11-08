import type { Evidence } from "./types";

export const METRIC: Record<string, { label: string; unit: string; scale: number }> = {
  house_price_median: { label: "戸建て相場", unit: "万円", scale: 1e4 },
  land_area_median:   { label: "土地面積", unit: "㎡", scale: 1 },
  share_land_150:     { label: "土地150㎡以上の割合", unit: "%", scale: 0.01 },
  flood_share:        { label: "浸水想定区域", unit: "%", scale: 0.01 },
  flood_deep_share:   { label: "深い浸水の想定区域", unit: "%", scale: 0.01 },
  landslide_share:    { label: "土砂災害警戒区域", unit: "%", scale: 0.01 },
};
export const POI: Record<string, string> = {
  large_shopping_mall: "大型商業施設", supermarket: "スーパー", golf_course: "ゴルフ場",
  large_park: "大きな公園", park: "公園", dog_park: "ドッグラン", hospital: "病院",
};

export function fmtEvidence(ev: Evidence): string {
  const c = ev.condition, v = ev.value;
  if (c.type === "commute")
    return v == null ? `${c.dest_station}: 到達不可` : `${c.dest_station}まで${Math.round(v)}分${ev.name ? `（${ev.name}）` : ""}`;
  if (c.type === "area_metric") {
    const m = METRIC[c.metric] ?? { label: c.metric, unit: "", scale: 1 };
    return v == null ? `${m.label}: データなし` : `${m.label} ${Math.round(v / m.scale).toLocaleString()}${m.unit}`;
  }
  const label = POI[c.category] ?? c.category;
  if (v == null) return `${label}: データなし`;
  const d = v >= 1000 ? `${(v / 1000).toFixed(1)}km` : `${Math.round(v)}m`;
  return `${label}${ev.name ? `「${ev.name}」` : ""}まで${d}`;
}
