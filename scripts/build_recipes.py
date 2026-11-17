# -*- coding: utf-8 -*-
"""由 manu_all.json + levels.json 构建四系配方 dataset
  ProfessionID: 4=烹饪(cooking) 5=缝纫(tailoring) 6=锻造(founding) 7=医术(medicine)
等级口径: nLevel > levels.json > RequireLevel(≠255) ; 都取不到 = None(无等级要求/旧配方)
同时抓取涉及物品的名称/描述/可交易 → items.json
"""
import json, os, re, sys, time, html, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://node.jx3box.com"
HDR = {"User-Agent": "Mozilla/5.0"}
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")
TABS = {4: "cooking", 5: "tailoring", 6: "founding", 7: "medicine"}


def get(url, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HDR)
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except Exception as e:
            if i == tries - 1:
                print("ERR", url[-60:], e, file=sys.stderr)
                return None
            time.sleep(1.0 + i)
    return None


manu = json.load(open(os.path.join(DATA, "manu_all.json"), encoding="utf-8"))["list"]
levels = json.load(open(os.path.join(DATA, "levels.json"), encoding="utf-8"))


def level_of(r):
    n = r.get("nLevel")
    if isinstance(n, int) and 0 < n <= 100:
        return n
    v = levels.get(f"{r['ProfessionID']}_{r['ID']}")
    if isinstance(v, int) and 0 < v <= 100:
        return v
    rl = r.get("RequireLevel")
    if isinstance(rl, int) and 0 < rl < 255:
        return rl
    return None


raw = []
for r in manu:
    tab = TABS.get(r.get("ProfessionID"))
    if not tab or r.get("bHide"):
        continue
    lv = level_of(r)
    if lv is None and not (r.get("Exp") or 0) > 0:
        continue
    mats, prods = [], []
    for i in range(1, 9):
        ri, ci = r.get(f"RequireItemIndex{i}"), r.get(f"CreateItemIndex{i}")
        rt = r.get(f"RequireItemType{i}") or 5
        ct = r.get(f"CreateItemType{i}") or 5
        rc = r.get(f"RequireItemCount{i}")
        if isinstance(ri, int) and ri > 0 and isinstance(rc, int) and rc > 0:
            mats.append([rt, ri, rc])
        if isinstance(ci, int) and ci > 0:
            mn = r.get(f"CreateItemMin{i}") if isinstance(r.get(f"CreateItemMin{i}"), int) else 1
            mx = r.get(f"CreateItemMax{i}") if isinstance(r.get(f"CreateItemMax{i}"), int) else mn
            pb = r.get(f"CreateItemProbability{i}")
            prods.append([ct, ci, max(mn, 1), max(mx, mn, 1),
                          round(pb / 1048576 * 100, 2) if isinstance(pb, (int, float)) and pb > 0 else 100])
    if not mats or not prods:
        continue
    raw.append({
        "tab": tab, "id": r["ID"], "key": f"{tab}_{r['ID']}", "name": r.get("Name"),
        "level": lv, "exp": r.get("Exp") or 0, "vigor": r.get("CostVigor") or 0,
        "expertise": bool(r.get("SpecialNeedExpertise") or r.get("NeedExpertise")),
        "belong": r.get("Belong") or 0, "quality": r.get("Quality") or 0,
        "mats": mats, "prods": prods,
    })

print("recipes:", len(raw), {t: sum(1 for x in raw if x['tab'] == t) for t in TABS.values()}, file=sys.stderr)

# ---------- 抓物品名称/描述 ----------
# 物品键 = "{ItemType}_{ItemIndex}"；普通材料=5，装备(衣/鞋/武器)=7，忽略类型会查不到新版装备
keys = sorted({f"{m[0]}_{m[1]}" for r in raw for m in r["mats"]} |
              {f"{p[0]}_{p[1]}" for r in raw for p in r["prods"]})
print("items:", len(keys), file=sys.stderr)
groups = [keys[i:i + 40] for i in range(0, len(keys), 40)]


def job(g):
    return get(f"{BASE}/item_merged/id/{','.join(g)}?per=40") or {}


items = {}
with ThreadPoolExecutor(max_workers=6) as ex:
    for n, res in enumerate(ex.map(job, groups), 1):
        for x in res.get("list", []) or []:
            k = str(x.get("id") or "")
            if "_" not in k:
                continue
            desc = html.unescape(x.get("Desc") or "")
            desc = re.sub(r"<[^>]+>", "", desc)          # 去标签
            desc = re.sub(r'"?\s*font=\d+"?', " ", desc)  # 去残留属性
            desc = re.sub(r"\btext=", "", desc).replace('">', " ")
            items[k] = {"name": x.get("Name"), "desc": re.sub(r"\s+", " ", desc).replace('"', "").strip(),
                        "price": x.get("Price"), "q": x.get("Quality"),
                        "trade": bool(x.get("CanTrade"))}
        if n % 10 == 0:
            print(f"  {n}/{len(groups)} 已收 {len(items)}", file=sys.stderr)

print("items got:", len(items), file=sys.stderr)


def nm(k):
    v = items.get(k)
    return ((v or {}).get("name") or k).replace("【印象】", "").replace("【声望】", "")


out = {"cooking": [], "tailoring": [], "founding": [], "medicine": []}
for r in raw:
    out[r["tab"]].append({
        "key": r["key"], "id": r["id"], "name": r["name"],
        "level": r["level"], "exp": r["exp"], "vigor": r["vigor"],
        "expertise": r["expertise"], "belong": r["belong"], "quality": r["quality"],
        "mats": [{"k": f"{m[0]}_{m[1]}", "name": nm(f"{m[0]}_{m[1]}"), "count": m[2]} for m in r["mats"]],
        "prods": [{"k": f"{p[0]}_{p[1]}", "name": nm(f"{p[0]}_{p[1]}"), "min": p[2], "max": p[3], "prob": p[4]} for p in r["prods"]],
    })
for t in out:
    out[t].sort(key=lambda x: (x["level"] or 999, x["name"] or ""))

json.dump({"generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"), "source": "node.jx3box.com/manufactures",
           "recipes": out}, open(os.path.join(DATA, "recipes.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
json.dump({"fetchedAt": time.strftime("%Y-%m-%d %H:%M:%S"), "items": items},
          open(os.path.join(DATA, "items.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

for t in out:
    lv = sorted({x["level"] for x in out[t] if x["level"]})
    print(t, len(out[t]), "levels", lv[:3], "...", lv[-3:], "tradeable items",
          sum(1 for x in out[t] for p in x["prods"] if (items.get(p["k"]) or {}).get("trade")), file=sys.stderr)
