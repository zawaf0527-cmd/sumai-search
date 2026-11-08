"use client";
import { useRef, useState } from "react";
import dynamic from "next/dynamic";
import PlanEditor from "@/components/PlanEditor";
import ResultList from "@/components/ResultList";
import * as api from "@/lib/api";
import type { ExplainItem, FlexInfo, SearchPlan, StationResult } from "@/lib/types";

const StationMap = dynamic(() => import("@/components/StationMap"), {
  ssr: false,
  loading: () => <div className="h-full w-full animate-pulse bg-slate-100" />,
});

const EXAMPLES = [
  "成城石井がある駅で静かな街、東京まで乗換1回",
  "温泉が近くて大宮まで30分、5000万以内",
  "洗練された街並みで子育てしやすい、品川まで45分",
  "豊洲まで60分、乗り換え1回以内、5000万以内、大きな公園",
  "大手町まで45分、庭付き戸建て、水害が心配",
  "新宿まで乗り換えなしで40分、スーパーが近い",
  "ゴルフが趣味。品川まで60分、土砂崩れが怖い",
];

function toMessage(e: unknown) {
  return e instanceof Error ? e.message : String(e);
}

export default function Home() {
  const [text, setText] = useState(EXAMPLES[0]);
  const [plan, setPlan] = useState<SearchPlan | null>(null);
  const [results, setResults] = useState<StationResult[]>([]);
  const [flex, setFlex] = useState<FlexInfo[]>([]);
  const [explains, setExplains] = useState<Record<string, ExplainItem>>({});
  const [notes, setNotes] = useState<string[]>([]);
  const [busy, setBusy] = useState<"" | "parse" | "search">("");
  const [explaining, setExplaining] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);
  const reqId = useRef(0);

  async function runSearch(p: SearchPlan) {
    const id = ++reqId.current;
    setBusy("search"); setError(""); setExplains({}); setNotes([]); setFlex([]);
    try {
      const res = await api.search(p);
      if (id !== reqId.current) return;

      // APIがエラーを返したとき（results が無い）は、中身を見せて止める
      const list = Array.isArray(res?.results) ? res.results : null;
      if (!list) {
        throw new Error(`検索APIの応答に results がありません: ${JSON.stringify(res).slice(0, 300)}`);
      }
      const flexInfo = (res as unknown as { flex?: FlexInfo[] }).flex;
      setFlex(Array.isArray(flexInfo) ? flexInfo : []);
      setResults(list); setSelected(null); setSearched(true);
      setBusy("");
      if (list.length === 0) return;             // 0件なら説明文は作らない

      setExplaining(true);                       // 説明文は後から届く
      try {
        const ex = await api.explain(p, list);
        if (id !== reqId.current) return;        // その間に再検索されたら捨てる
        setExplains(Object.fromEntries((ex?.items ?? []).map((it) => [it.station, it])));
        setNotes(ex?.notes ?? []);
      } catch (e) {
        if (id === reqId.current) setNotes([`説明文の生成に失敗しました（検索結果は有効です）: ${toMessage(e)}`]);
      }
    } catch (e) {
      if (id === reqId.current) { setError(toMessage(e)); setResults([]); }
    } finally {
      if (id === reqId.current) { setBusy(""); setExplaining(false); }
    }
  }

  async function onParse() {
    if (!text.trim() || busy) return;
    setBusy("parse"); setError("");
    try {
      const p = await api.parse(text);
      setPlan(p);
      await runSearch(p);
    } catch (e) {
      setError(toMessage(e)); setBusy("");
    }
  }

  const top = results[0];

  return (
    <div className="flex h-screen flex-col bg-slate-50 text-slate-900">
      {/* ヘッダー */}
      <header className="flex items-center justify-between border-b border-slate-200 bg-white px-5 py-3">
        <div className="flex items-center gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-orange-500 text-lg font-bold text-white shadow-sm">住</div>
          <div>
            <p className="font-bold leading-tight">住むエリア検索</p>
            <p className="text-xs text-slate-500">ふだんの言葉で、首都圏の駅から暮らす街を探す</p>
          </div>
        </div>
        <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">β版・ローカル実行</span>
      </header>

      <div className="flex min-h-0 flex-1 flex-col md:flex-row">
        {/* 左：検索パネル */}
        <aside className="flex min-h-0 w-full flex-col border-slate-200 bg-white md:w-[480px] md:border-r">
          <div className="space-y-3 border-b border-slate-200 p-4">
            <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3 shadow-sm focus-within:border-orange-400 focus-within:ring-2 focus-within:ring-orange-100">
              <textarea
                className="w-full resize-none bg-transparent text-sm leading-relaxed outline-none"
                rows={3}
                value={text}
                placeholder="例：成城石井がある駅で静かな街、豊洲まで乗り換え1回以内で45分"
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); onParse(); }
                }}
              />
              <div className="mt-2 flex items-center justify-between">
                <span className="text-xs text-slate-400">Ctrl + Enter で検索</span>
                <button
                  className="flex items-center gap-2 rounded-xl bg-orange-500 px-5 py-2 text-sm font-bold text-white shadow-sm transition hover:bg-orange-600 disabled:opacity-50"
                  disabled={!!busy || !text.trim()}
                  onClick={onParse}
                >
                  {busy && <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />}
                  {busy === "parse" ? "条件を読み取り中…" : busy === "search" ? "検索中…" : "この条件で探す"}
                </button>
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              {EXAMPLES.map((ex) => (
                <button key={ex} onClick={() => setText(ex)} disabled={!!busy}
                  className="max-w-full truncate rounded-full border border-slate-200 bg-white px-3 py-1 text-xs text-slate-600 transition hover:border-orange-300 hover:bg-orange-50 hover:text-orange-700">
                  {ex}
                </button>
              ))}
            </div>
          </div>

          <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-4">
            {error && (
              <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                <p className="font-bold">エラーが発生しました</p>
                <p className="mt-1 break-all">{error}</p>
              </div>
            )}

            {plan && (
              <section className="space-y-3 rounded-xl border border-orange-200 bg-orange-50/60 p-3">
                <p className="text-xs font-bold text-orange-700">AIが読み取った条件（編集して再検索できます）</p>
                <PlanEditor plan={plan} onChange={setPlan} />

                {flex.length > 0 && (
                  <div className="space-y-1 rounded-lg border border-slate-200 bg-white/80 p-2.5 text-xs text-slate-600">
                    <p className="font-semibold text-slate-700">自由入力の読み取り結果</p>
                    {flex.map((f, i) => (
                      <p key={i}>
                        「{f.query}」→{" "}
                        {f.kind ? (
                          <>
                            <span className={f.kind === "name" ? "text-emerald-700" : "text-violet-700"}>{f.label}</span>
                            <span className="text-slate-400">（{f.n_stations}駅の周辺にあり）</span>
                          </>
                        ) : (
                          <span className="text-rose-600">データが見つからないため条件から外しました</span>
                        )}
                      </p>
                    ))}
                  </div>
                )}

                <button
                  className="rounded-lg border border-orange-500 bg-white px-3 py-1 text-sm font-medium text-orange-700 transition hover:bg-orange-100 disabled:opacity-50"
                  disabled={!!busy} onClick={() => runSearch(plan)}>
                  この条件で再検索
                </button>
              </section>
            )}

            {notes.length > 0 && (
              <div className="space-y-1 rounded-xl bg-slate-100 p-3">
                {notes.map((n) => <p key={n} className="text-xs text-slate-600">※ {n}</p>)}
              </div>
            )}

            {busy ? (
              <div className="space-y-3">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="animate-pulse rounded-xl border border-slate-200 p-4">
                    <div className="h-4 w-1/3 rounded bg-slate-200" />
                    <div className="mt-3 h-3 w-full rounded bg-slate-100" />
                    <div className="mt-2 h-3 w-2/3 rounded bg-slate-100" />
                  </div>
                ))}
              </div>
            ) : results.length > 0 ? (
              <>
                <div className="grid grid-cols-2 gap-2">
                  <div className="rounded-xl bg-slate-900 p-3 text-white">
                    <p className="text-xs text-slate-300">見つかった街</p>
                    <p className="text-2xl font-bold">{results.length}<span className="ml-1 text-sm font-normal">駅</span></p>
                  </div>
                  <div className="rounded-xl bg-orange-500 p-3 text-white">
                    <p className="text-xs text-orange-100">いちばんのおすすめ</p>
                    <p className="truncate text-2xl font-bold">{top?.station ?? "-"}</p>
                  </div>
                </div>
                <ResultList results={results} explains={explains} explaining={explaining}
                  selected={selected} onSelect={setSelected} />
              </>
            ) : searched && !error ? (
              <div className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
                <p className="font-bold text-slate-700">条件に合う駅が見つかりませんでした</p>
                <p className="mt-1">通勤時間を延ばす、乗り換えの上限を外す、「必須」を「できれば」に変えるなどして再検索してみてください。</p>
              </div>
            ) : !error ? (
              <div className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500">
                <p className="font-bold text-slate-700">希望を文章で入力してください</p>
                <p className="mt-1">通勤先・乗り換え・予算・災害リスクに加えて、「成城石井」「温泉」などのお店や施設、「静かな街」などの雰囲気でも探せます。</p>
              </div>
            ) : null}
          </div>
        </aside>

        {/* 右：地図 */}
        <section className="relative h-[50vh] flex-1 md:h-auto">
          {results.length > 0 ? (
            <StationMap results={results} selected={selected} onSelect={setSelected} />
          ) : (
            <div className="grid h-full place-items-center bg-slate-100">
              <p className="text-sm text-slate-400">検索すると、ここに候補の駅が地図で表示されます</p>
            </div>
          )}
        </section>
      </div>

      <footer className="border-t border-slate-200 bg-white px-5 py-2 text-[11px] text-slate-500">
        出典：国土交通省 不動産情報ライブラリ／国土数値情報／駅データ.jp／© OpenStreetMap contributors（ODbL）／OpenFreeMap／OpenMapTiles。
        所要時間は駅間距離と路線種別からの推計（乗換1回5分）で、急行・時刻表は考慮していません。街の雰囲気は用途地域と周辺施設数からの推計です。
      </footer>
    </div>
  );
}
