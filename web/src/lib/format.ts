import type { Evidence, FlexCondition } from "./types";

// キーは api\catalog.yaml の vibes と同じにする
export const VIBE_LABEL: Record<string, string> = {
  quiet: "静かな住宅街",
  modern: "洗練された都会的な街並み",
  lively: "にぎやか・飲食店が多い",
  family: "子育てしやすい",
  green: "緑が多い",
};

const dist = (m: number) => (m >= 1000 ? `${(m / 1000).toFixed(1)}km` : `${Math.round(m)}m`);

export function chipLabel(c: FlexCondition): string {
  return c.type === "place_nearby" ? `${c.query}が近い` : VIBE_LABEL[c.vibe] ?? c.vibe;
}

/** 新しい条件の根拠文。従来の条件は null を返す（labels.ts の fmtEvidence を使う） */
export function evidenceText(e: Evidence): string | null {
  const c = e.condition;
  if (c.type === "place_nearby") {
    return e.value == null
      ? `${c.query}：${dist(c.within_m ?? 800)}以内になし`
      : `${c.query}：「${e.name ?? "名称なし"}」まで${dist(e.value)}`;
  }
  if (c.type === "vibe") {
    const label = c.label ?? VIBE_LABEL[c.vibe] ?? c.vibe;
    return `${label} ${Math.round((e.value ?? 0) * 100)}点`;
  }
  return null;
}

/** マウスを乗せたときに出す詳しい根拠（雰囲気の理由・店名の解釈） */
export function evidenceDetail(e: Evidence): string | undefined {
  return e.detail ?? undefined;
}
