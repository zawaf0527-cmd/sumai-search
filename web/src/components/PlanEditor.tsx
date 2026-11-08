"use client";
import type { Condition, FlexCondition, SearchPlan } from "@/lib/types";
import { METRIC, POI } from "@/lib/labels";
import FlexChip from "./FlexChip";

type Props = { plan: SearchPlan; onChange: (p: SearchPlan) => void };
const num = (s: string) => (s === "" ? null : Number(s));
const isFlex = (c: Condition): c is FlexCondition => c.type === "place_nearby" || c.type === "vibe";

export default function PlanEditor({ plan, onChange }: Props) {
  const replace = (i: number, nc: Condition) =>
    onChange({ ...plan, conditions: plan.conditions.map((c, j) => (j === i ? nc : c)) });
  const update = (i: number, patch: Partial<Condition>) =>
    replace(i, { ...plan.conditions[i], ...patch } as Condition);
  const remove = (i: number) =>
    onChange({ ...plan, conditions: plan.conditions.filter((_, j) => j !== i) });

  // 番号(i)を保ったまま、基本条件と自由入力条件に分ける
  const items = plan.conditions.map((c, i) => ({ c, i }));
  const baseItems = items.filter(({ c }) => !isFlex(c));
  const flexItems = items.filter(({ c }) => isFlex(c));

  const imp = (i: number, c: Condition) =>
    c.type !== "commute" && (
      <button
        className={`rounded-full px-2 text-xs font-semibold transition ${
          c.importance === "must" ? "bg-rose-500 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}
        title="クリックで 必須 ⇔ できれば を切り替え"
        onClick={() => update(i, { importance: c.importance === "must" ? "want" : "must" })}>
        {c.importance === "must" ? "必須" : "できれば"}
      </button>
    );

  const removeBtn = (i: number) => (
    <button className="ml-1 text-slate-400 hover:text-rose-600" onClick={() => remove(i)} aria-label="削除">×</button>
  );

  return (
    <div className="space-y-3">
      {plan.conditions.length === 0 && (
        <p className="text-sm text-slate-500">読み取れた条件がありません。文章を変えて検索し直してください。</p>
      )}

      {baseItems.length > 0 && (
        <div className="space-y-1">
          <p className="text-[11px] font-semibold text-slate-500">基本の条件</p>
          <div className="flex flex-wrap gap-2">
            {baseItems.map(({ c, i }) => (
              <div key={i}
                className="flex items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm shadow-sm">
                {c.type === "commute" && (
                  <>
                    <span className="rounded-full bg-sky-50 px-1.5 text-[10px] font-bold text-sky-700">通勤</span>
                    <span>{c.dest_station}まで</span>
                    <input type="number" className="w-14 rounded border border-slate-200 px-1"
                      value={c.max_minutes ?? ""}
                      onChange={(e) => update(i, { max_minutes: num(e.target.value) })} />
                    <span>分・乗換</span>
                    <select className="rounded border border-slate-200" value={c.max_transfers ?? ""}
                      onChange={(e) => update(i, { max_transfers: num(e.target.value) })}>
                      <option value="">制限なし</option>
                      <option value="0">なし</option>
                      <option value="1">1回まで</option>
                      <option value="2">2回まで</option>
                    </select>
                  </>
                )}

                {c.type === "area_metric" && (() => {
                  const m = METRIC[c.metric] ?? { label: c.metric, unit: "", scale: 1 };
                  const key = c.max_value != null ? "max_value" : "min_value";
                  const val = c[key];
                  return (
                    <>
                      <span className="rounded-full bg-amber-50 px-1.5 text-[10px] font-bold text-amber-700">街</span>
                      <span>{m.label}</span>
                      {val != null && (
                        <>
                          <input type="number" className="w-20 rounded border border-slate-200 px-1"
                            value={Math.round(val / m.scale)}
                            onChange={(e) => update(i, {
                              [key]: e.target.value === "" ? null : Number(e.target.value) * m.scale,
                            })} />
                          <span>{m.unit}{key === "max_value" ? "以下" : "以上"}</span>
                        </>
                      )}
                      {imp(i, c)}
                    </>
                  );
                })()}

                {c.type === "poi_proximity" && (
                  <>
                    <span className="rounded-full bg-emerald-50 px-1.5 text-[10px] font-bold text-emerald-700">施設</span>
                    <span>{POI[c.category] ?? c.category}が近い</span>
                    {imp(i, c)}
                  </>
                )}
                {removeBtn(i)}
              </div>
            ))}
          </div>
        </div>
      )}

      {flexItems.length > 0 && (
        <div className="space-y-1">
          <p className="text-[11px] font-semibold text-slate-500">お店・施設・街の雰囲気</p>
          <div className="flex flex-wrap gap-2">
            {flexItems.map(({ c, i }) =>
              isFlex(c) && (
                <FlexChip key={i} cond={c} onChange={(nc) => replace(i, nc)} onRemove={() => remove(i)} />
              ),
            )}
          </div>
        </div>
      )}

      {plan.unsupported.length > 0 && (
        <p className="text-xs text-slate-500">
          評価できない希望（順位には反映しません）：{plan.unsupported.map((u) => `「${u}」`).join(" ")}
        </p>
      )}
    </div>
  );
}
