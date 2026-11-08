"use client";
import { useEffect, useRef } from "react";
import {
  Map as MlMap, LngLatBounds, NavigationControl, Popup,
  type GeoJSONSource, type MapLayerMouseEvent,
} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { StationResult } from "@/lib/types";

// 無料・登録不要のベクター地図（淡い色でピンが目立つ）。カラフルにしたいなら styles/liberty
const STYLE_URL = "https://tiles.openfreemap.org/styles/positron";

type Props = { results: StationResult[]; selected: string | null; onSelect: (s: string) => void };

export default function StationMap({ results, selected, onSelect }: Props) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<MlMap | null>(null);
  const loaded = useRef(false);
  // イベント処理の中から「最新の値」を読むための入れ物
  const latest = useRef({ results, selected, onSelect });
  latest.current = { results, selected, onSelect };

  // 検索結果をピンとして描き直す
  const draw = () => {
    const m = map.current;
    if (!m || !loaded.current) return;
    const src = m.getSource("st") as GeoJSONSource | undefined;
    if (!src) return;
    const rs = latest.current.results;
    src.setData({
      type: "FeatureCollection",
      features: rs.map((r, i) => ({
        type: "Feature",
        geometry: { type: "Point", coordinates: [r.lon, r.lat] },
        properties: { station: r.station, city: r.city ?? "", score: r.score, rank: i + 1 },
      })),
    });
    if (rs.length) {
      const b = new LngLatBounds();
      rs.forEach((r) => b.extend([r.lon, r.lat]));
      m.fitBounds(b, { padding: 70, maxZoom: 12, duration: 800 });
    }
  };

  // 選んだ駅だけ青い輪を出す
  const highlight = () => {
    const m = map.current;
    if (!m || !loaded.current || !m.getLayer("st-selected")) return;
    m.setFilter("st-selected", ["==", ["get", "station"], latest.current.selected ?? ""]);
  };

  // 地図の作成（最初の1回だけ）
  useEffect(() => {
    if (!box.current) return;
    const m = new MlMap({
      container: box.current,
      style: STYLE_URL,
      center: [139.7, 35.7],
      zoom: 9,
      attributionControl: { compact: true },
    });
    map.current = m;
    m.addControl(new NavigationControl({ showCompass: false }), "top-right");

    const popup = new Popup({ closeButton: false, closeOnClick: false, offset: 14 });

    m.on("load", () => {
      // (A-3) 地名を日本語優先にする（日本語名が無いものは元の名前）
      for (const layer of m.getStyle().layers ?? []) {
        if (layer.type === "symbol" && m.getLayoutProperty(layer.id, "text-field")) {
          m.setLayoutProperty(layer.id, "text-field", ["coalesce", ["get", "name:ja"], ["get", "name"]]);
        }
      }

      // (A-2) ピンのデータ置き場とレイヤーは、地図の読み込み後に作る
      m.addSource("st", { type: "geojson", data: { type: "FeatureCollection", features: [] } });

      // 選択中の駅：青い輪（ピンの下に敷く）
      m.addLayer({
        id: "st-selected", type: "circle", source: "st",
        filter: ["==", ["get", "station"], ""],
        paint: {
          "circle-radius": 20,
          "circle-color": "rgba(37, 99, 235, 0.15)",
          "circle-stroke-color": "#2563eb",
          "circle-stroke-width": 3,
        },
      });

      // 駅のピン：点数が高いほど濃いオレンジ、上位3駅は大きく
      m.addLayer({
        id: "st", type: "circle", source: "st",
        paint: {
          "circle-radius": ["case", ["<=", ["get", "rank"], 3], 13, ["<=", ["get", "rank"], 10], 10, 7],
          "circle-color": ["interpolate", ["linear"], ["get", "score"], 0, "#fdba74", 0.5, "#f97316", 1, "#c2410c"],
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 2.5,
        },
      });

      // 上位10駅にはピンの中に順位の数字
      m.addLayer({
        id: "st-rank", type: "symbol", source: "st",
        filter: ["<=", ["get", "rank"], 10],
        layout: {
          "text-field": ["to-string", ["get", "rank"]],
          "text-font": ["Noto Sans Bold"],
          "text-size": 11,
          "text-allow-overlap": true,
        },
        paint: { "text-color": "#ffffff" },
      });

      // クリックで選択、マウスを乗せると駅名と点数
      m.on("click", "st", (e: MapLayerMouseEvent) => {
        const s = e.features?.[0]?.properties?.station;
        if (s) latest.current.onSelect(String(s));
      });
      m.on("mousemove", "st", (e: MapLayerMouseEvent) => {
        m.getCanvas().style.cursor = "pointer";
        const p = e.features?.[0]?.properties;
        if (!p) return;
        popup
          .setLngLat(e.lngLat)
          .setHTML(
            `<div style="font-size:12px;line-height:1.5">
               <b>${p.rank}位　${p.station}</b><br/>
               <span style="color:#64748b">${p.city}・点数 ${Number(p.score).toFixed(2)}</span>
             </div>`,
          )
          .addTo(m);
      });
      m.on("mouseleave", "st", () => {
        m.getCanvas().style.cursor = "";
        popup.remove();
      });

      loaded.current = true;
      draw();
      highlight();
    });

    return () => {
      loaded.current = false;
      m.remove();
    };
  }, []);

  // 検索結果が変わったら描き直す
  useEffect(() => { draw(); }, [results]);

  // 駅が選ばれたら、そこへ移動して強調
  useEffect(() => {
    highlight();
    const r = results.find((x) => x.station === selected);
    if (r) map.current?.flyTo({ center: [r.lon, r.lat], zoom: 13, duration: 900 });
  }, [selected, results]);

  return (
    <div className="relative h-full min-h-[480px] w-full">
      <div ref={box} className="h-full w-full" />
      {results.length > 0 && (
        <div className="pointer-events-none absolute left-3 top-3 rounded-full bg-white/90 px-3 py-1 text-xs font-medium text-slate-700 shadow">
          候補 {results.length} 駅（数字は順位）
        </div>
      )}
    </div>
  );
}
