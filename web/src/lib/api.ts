import type { ExplainResponse, SearchPlan, SearchResponse, StationResult } from "./types";

async function post<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(`/api${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`${path} ${r.status}: ${await r.text()}`);
  return (await r.json()) as T;
}

export const parse = (text: string) => post<SearchPlan>("/parse", { text });
export const search = (plan: SearchPlan) => post<SearchResponse>("/search", plan);
export const explain = (plan: SearchPlan, results: StationResult[]) =>
  post<ExplainResponse>("/explain", { plan, results, top_n: 5 });
