"use client";
import { useEffect, useRef } from "react";
import type { ExplainItem, StationResult } from "@/lib/types";
import { fmtEvidence } from "@/lib/labels";
import { evidenceDetail, evidenceText } from "@/lib/format";

type Props = {
  results: StationResult[]; explains: Record<string, ExplainItem>; explaining: boolean;
  selected: string | null; onSelect: (s: string) => void;
};

const EV_STYLE: Record<string, string> = {
  commute: "bg-sky-50 text-sky-800",
  area_metric: "bg-amber-50 text-amber-800",
  poi_proximity: "bg-emerald-50 text-emerald-800",
  place_nearby: "bg-emerald-50 text-emerald-800 ring-1 ring-emerald-200",
  vibe: "bg-violet-50 text-violet-800 ring-1 ring-violet-200",
};

export default function ResultList({ results, explains, explaining, selected, onSelect }: Props) {
  const refs = useRef<Record<string, HTMLLIElement | null>>({});

  // 地図で駅を選んだら、リストもその駅までスクロール
  useEffect(() => {
    if (selected) refs.current[selected]?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [selected]);

  return (
    <ol className="space-y-2">
      {results.map((r, i) => {
        const ex = explains[r.station];
        const isSel = selected === r.station;
        const pct = Math.max(0, Math.min(100, Math.round((r.score ?? 0) * 100)));
        return (
          <li key={r.station}
            ref={(el) => { refs.current[r.station] = el; }}
            onClick={() => onSelect(r.station)}
            className={`cursor-pointer rounded-xl border bg-white p-3 transition hover:shadow-md ${
              isSel ? "border-orange-400 ring-2 ring-orange-200" : "border-slate-200"
            }`}>
            <div className="flex items-center gap-2">
              <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-sm font-bold ${
                i < 3 ? "bg-orange-500 text-white" : "bg-slate-100 text-slate-600"
              }`}>{i + 1}</span>
              <span className="truncate text-lg font-bold">{r.station}</span>
              <span className="truncate text-sm text-slate-500">{r.city}</span>
              <span className="ml-auto shrink-0 text-sm font-semibold text-slate-700">{pct}点</span>
            </div>

            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
              <div className="h-full rounded-full bg-gradient-to-r from-amber-300 to-orange-500"
                style={{ width: `${pct}%` }} />
            </div>

            <div className="mt-2 flex flex-wrap gap-1">
              {r.evidence.map((ev, j) => {
                const t = ev.condition?.type ?? "";
                return (
                  <span key={j} title={evidenceDetail(ev)}
                    className={`rounded-md px-2 py-0.5 text-xs ${EV_STYLE[t] ?? "bg-slate-100 text-slate-700"}`}>
                    {evidenceText(ev) ?? fmtEvidence(ev)}
                  </span>
                );
              })}
            </div>

            {i < 5 && (
              <p className="mt-2 text-sm leading-relaxed text-slate-700">
                {ex ? ex.summary : explaining ? (
                  <span className="inline-flex items-center gap-1 text-slate-400">
                    <span className="h-3 w-3 animate-spin rounded-full border-2 border-slate-300 border-t-transparent" />
                    説明文を作成中…
                  </span>
                ) : ""}
                {ex?.source === "template" && <span className="ml-1 text-xs text-slate-400">（定型文）</span>}
              </p>
            )}
          </li>
        );
      })}
    </ol>
  );
}
