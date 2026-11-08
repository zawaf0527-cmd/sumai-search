"""/parse の評価：20問 × 複数モデルを比較し、eval_results.csv に保存する
使い方: python eval_parse.py qwen3:14b gpt-oss:20b qwen3:30b-a3b qwen3.5:27b
"""
import csv, sys, time
import httpx
import llm
from llm import parse_text


# 期待する条件を短く書くための補助関数
def C(dest, minutes):                       # 通勤
    return ("commute", dest, {"max_minutes": minutes})

def M(metric, **attrs):                     # 地域の指標（metricは文字列、または候補のset）
    return ("area_metric", metric, attrs)

def P(cat, **attrs):                        # 施設
    return ("poi_proximity", cat, attrs)

def BUDGET(yen):                            # 予算（必ずmust）
    return M("house_price_median", max_value=yen, importance="must")


GLOBAL_OK_EXTRA = {("area_metric", "land_area_median")}   # 「庭付き」で一緒に選ばれても許す

CASES = [
    # ---------- 基本（これまでの7問） ----------
    dict(id=1, level="基本", text="大手町まで45分以内、予算5000万円、庭付き戸建て",
         expect=[C("大手町", 45), BUDGET(50_000_000), M("share_land_150")]),
    dict(id=2, level="基本", text="水害が心配。新宿まで1時間くらい",
         expect=[C("新宿", (55, 70)), M("flood_share")]),
    dict(id=3, level="基本", text="犬を多頭飼いしているので大きな公園が近いといい",
         expect=[P("large_park")], ok_extra={("poi_proximity", "dog_park")}),
    dict(id=4, level="基本", text="ゴルフが趣味。品川まで60分",
         expect=[C("品川", 60), P("golf_course")]),
    dict(id=5, level="基本", text="イオンみたいな大きな商業施設があって、スーパーも近いといい",
         expect=[P("large_shopping_mall"), P("supermarket")]),
    dict(id=6, level="基本", text="土砂崩れが怖い",
         expect=[M("landslide_share")]),
    dict(id=7, level="基本", text="静かな街がいい、池袋まで40分",
         expect=[C("池袋", 40)], unsupported=True),

    # ---------- 応用：数値・表記 ----------
    dict(id=8, level="応用", text="予算は4千5百万円。通勤は東京駅まで1時間半以内",
         expect=[C("東京", 90), BUDGET(45_000_000)]),
    dict(id=9, level="応用", text="0.6億くらいまでなら出せます。渋谷まで70分",
         expect=[C("渋谷", 70), BUDGET(60_000_000)]),
    dict(id=20, level="応用", text="勤務先は東京駅の八重洲口。片道40分以内で、予算の上限は六千万円",
         expect=[C("東京", 40), BUDGET(60_000_000)]),
    dict(id=19, level="応用", text="通勤は池袋までドアtoドアで1時間弱が限界",
         expect=[C("池袋", (45, 60))]),

    # ---------- 応用：否定・複数・重要度 ----------
    dict(id=10, level="応用", text="ゴルフはやらないのでゴルフ場は不要。病院が近いと安心",
         expect=[P("hospital")]),
    dict(id=11, level="応用", text="共働きで、夫は新宿、私は横浜に通勤しています。どちらも50分以内がいい",
         expect=[C("新宿", 50), C("横浜", 50)]),
    dict(id=12, level="応用", text="浸水リスクがある地域は絶対に嫌。公園は近ければうれしい程度",
         expect=[M("flood_share", importance="must"), P({"park", "large_park"}, importance="want")]),

    # ---------- 応用：言い換え・細かい区別 ----------
    dict(id=13, level="応用", text="床上まで水が来るような深い浸水だけは避けたい",
         expect=[M("flood_deep_share")]),
    dict(id=14, level="応用", text="土地は広め、できれば50坪以上ほしい",
         expect=[M({"share_land_150", "land_area_median"})]),
    dict(id=18, level="応用", text="高台で、がけ崩れの心配もない場所がいい",
         expect=[M("landslide_share")],
         ok_extra={("area_metric", "flood_share"), ("area_metric", "flood_deep_share")}),

    # ---------- 応用：データがない条件だけ ----------
    dict(id=15, level="応用", text="治安が良くて、日当たりのいい南向きの家",
         expect=[], unsupported=True),

    # ---------- 応用：長文（関係ない情報が混ざる） ----------
    dict(id=16, level="長文",
         text=("今は都内の賃貸マンションに住んでいて、子どもが来年小学生になるので引っ越しを考えています。"
               "妻の実家が埼玉なので、その方面もアリかなと思っています。夫婦とも大手町勤務なので45分以内、"
               "予算は5000万円まで、子どもを遊ばせられる大きな公園があるとうれしいです。"
               "小学校の評判も気になります。"),
         expect=[C("大手町", 45), BUDGET(50_000_000), P("large_park")], unsupported=True),
    dict(id=17, level="長文",
         text=("趣味はゴルフとキャンプで、週末はよくゴルフ場に行きます。犬を1匹飼っていて、"
               "ドッグランがあるとなお良し。買い物は車で大型ショッピングモールに行くので、"
               "駅前のスーパーはなくても構いません。品川まで1時間15分以内なら通えます。"),
         expect=[C("品川", 75), P("golf_course"), P("dog_park"), P("large_shopping_mall")],
         unsupported=True),
    dict(id=21, level="応用", text="豊洲まで60分、乗り換え1回以内で通えるところ", expect=[C("豊洲", 60, 1)]),
    dict(id=22, level="応用", text="新宿まで1本で行けて、45分以内", expect=[C("新宿", 45, 0)]),

]


def cond_key(c):
    if c.type == "commute":
        return c.dest_station.removesuffix("駅")
    return c.metric if c.type == "area_metric" else c.category


def key_ok(exp, got):
    return got in exp if isinstance(exp, set) else got == exp


def val_ok(exp, got):
    if isinstance(exp, tuple):                       # (下限, 上限) の範囲指定
        return got is not None and exp[0] <= got <= exp[1]
    return got == exp


def judge(case, plan):
    """問題点のリストを返す。空ならOK"""
    problems, used = [], set()
    conds = list(plan.conditions)
    for typ, key, attrs in case["expect"]:
        hit = next((i for i, c in enumerate(conds)
                    if i not in used and c.type == typ and key_ok(key, cond_key(c))), None)
        if hit is None:
            problems.append(f"不足: {typ}:{key}")
            continue
        used.add(hit)
        for k, v in attrs.items():
            got = getattr(conds[hit], k, None)
            if not val_ok(v, got):
                problems.append(f"値違い: {cond_key(conds[hit])}.{k} 期待={v} 実際={got}")
    ok_extra = GLOBAL_OK_EXTRA | case.get("ok_extra", set())
    for i, c in enumerate(conds):
        if i not in used and (c.type, cond_key(c)) not in ok_extra:
            problems.append(f"余計: {c.type}:{cond_key(c)}")
    if case.get("unsupported") and not plan.unsupported:
        problems.append("unsupportedが空（評価できない希望を拾えていない）")
    return problems


def unload(model):
    """評価が終わったモデルをメモリから降ろす（次のモデルのためにGPUを空ける）"""
    try:
        httpx.post(f"{llm.OLLAMA_URL}/api/generate",
                   json={"model": model, "keep_alive": 0}, timeout=60)
    except httpx.HTTPError:
        pass


def run(model):
    llm.MODEL = model                       # chat() は呼ばれるたびにこの値を見る
    print(f"\n===== {model} =====")
    t0 = time.time()
    try:
        parse_text("大手町まで30分")         # ウォームアップ（読み込み時間を計測から除外）
    except Exception as e:
        print("  ウォームアップ失敗:", str(e).splitlines()[0])
    print(f"  (モデル読み込み {time.time() - t0:.0f}秒)")

    rows = []
    for case in CASES:
        t = time.time()
        unsup = []                                   
        try:
            plan = parse_text(case["text"])
            problems, output = judge(case, plan), plan.model_dump_json()
            unsup = plan.unsupported                 
        except Exception as e:
            problems, output = [f"エラー: {str(e).splitlines()[0]}"], ""
        sec = time.time() - t
        ok = not problems
        print(f"{'OK' if ok else 'NG'} {sec:5.1f}秒 [{case['level']}] Q{case['id']:>2} {case['text'][:28]}")
        if unsup:                                    
            print("         評価できない希望:", unsup)
        for p in problems:
            print("        ", p)
        rows.append(dict(model=model, id=case["id"], level=case["level"], ok=ok,
                         sec=round(sec, 1), problems=" / ".join(problems),
                         text=case["text"], output=output))
    unload(model)
    return rows


def main():
    models = sys.argv[1:] or [llm.MODEL]
    all_rows = []
    for m in models:
        all_rows += run(m)

    print("\n===== まとめ =====")
    print(f"{'モデル':<16} {'合計':>6} {'基本':>6} {'応用':>6} {'長文':>6} {'平均秒':>7} {'最大秒':>7}")
    for m in models:
        r = [x for x in all_rows if x["model"] == m]
        def score(level=None):
            sub = [x for x in r if level is None or x["level"] == level]
            return f"{sum(x['ok'] for x in sub)}/{len(sub)}"
        secs = [x["sec"] for x in r]
        print(f"{m:<16} {score():>6} {score('基本'):>6} {score('応用'):>6} {score('長文'):>6} "
              f"{sum(secs) / len(secs):7.1f} {max(secs):7.1f}")

    with open("eval_results.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(all_rows[0]))
        w.writeheader()
        w.writerows(all_rows)
    print("\n詳細は eval_results.csv（Excelで開けます）")


if __name__ == "__main__":
    main()
