"use client";
import type { FlexCondition } from "@/lib/types";
import { VIBE_LABEL, chipLabel } from "@/lib/format";

type Props = { cond: FlexCondition; onChange: (c: FlexCondition) => void; onRemove: () => void };

export default function FlexChip({ cond, onChange, onRemove }: Props) {
  const isPlace = cond.type === "place_nearby";
  const must = cond.importance === "must";
  return (
    <div className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-sm shadow-sm ${
      isPlace ? "border-emerald-200 bg-emerald-50 text-emerald-900"
              : "border-violet-200 bg-violet-50 text-violet-900"}`}>
      <span className="rounded-full bg-white/70 px-1.5 text-[10px] font-bold">{isPlace ? "施設" : "雰囲気"}</span>

      {cond.type === "place_nearby" ? (
        <>
          <span className="font-medium" title={cond.resolved}>{chipLabel(cond)}</span>
          <select className="rounded-md bg-white/70 px-1 text-xs" value={cond.within_m ?? 800}
            onChange={(e) => onChange({ ...cond, within_m: Number(e.target.value) })}>
            <option value={400}>徒歩5分</option>
            <option value={800}>徒歩10分</option>
            <option value={1200}>徒歩15分</option>
          </select>
        </>
      ) : (
        <select className="rounded-md bg-white/70 px-1 text-sm font-medium" value={cond.vibe}
          onChange={(e) => onChange({ ...cond, vibe: e.target.value, label: undefined })}>
          {Object.entries(VIBE_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      )}

      <button
        className={`rounded-full px-2 text-xs font-semibold transition ${
          must ? "bg-rose-500 text-white" : "bg-white/70 text-slate-600 hover:bg-white"}`}
        title="クリックで 必須 ⇔ できれば を切り替え"
        onClick={() => onChange({ ...cond, importance: must ? "want" : "must" })}>
        {must ? "必須" : "できれば"}
      </button>
      <button className="text-slate-400 hover:text-slate-700" onClick={onRemove} aria-label="削除">×</button>
    </div>
  );
}
