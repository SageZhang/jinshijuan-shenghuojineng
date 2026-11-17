# -*- coding: utf-8 -*-
"""抓取魔盒全量烹饪/医术配方(结构字段),按 ID 合并 simple + 完整模式"""
import json, urllib.request, time, os, sys

BASE = "https://node.jx3box.com"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
os.makedirs(OUT, exist_ok=True)


def get(url, retry=3):
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers=HDR)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except Exception as e:
            if i == retry - 1:
                print("FAIL", url, e, file=sys.stderr)
                return []
            time.sleep(1.2)


def fetch_type(t):
    rows = []
    page = 1
    while page <= 80:
        d = get(f"{BASE}/manufactures?type={t}&client=std&page={page}&per=20")
        if not d:
            break
        rows.extend(d)
        print(f"  {t} p{page} +{len(d)} => {len(rows)}", file=sys.stderr)
        page += 1
    return rows


recs = {}
for t in ["cooking", "medicine"]:
    for r in fetch_type(t):
        rid = r.get("ID")
        if not rid:
            continue
        r["_type"] = t
        recs[(t, rid)] = r

# 同时抓 simple 模式补充 nLevel / 名称
simp = {}
for t in ["cooking", "medicine"]:
    page = 1
    while page <= 80:
        d = get(f"{BASE}/manufactures?type={t}&client=std&mode=simple&page={page}&per=20")
        if not d:
            break
        for x in d:
            simp[(t, x.get("ID"))] = x
        page += 1
print("full:", len(recs), "simple:", len(simp), file=sys.stderr)

out = {"cooking": [], "medicine": []}
for (t, rid), r in recs.items():
    s = simp.get((t, rid), {})
    lvl = s.get("nLevel") or r.get("RequireLevel") or 0
    if not lvl or lvl >= 250:
        lvl = 0  # 255 表示无等级门槛(特殊配方)
    mats, prods = [], []
    for i in range(1, 9):
        idx = r.get(f"RequireItemIndex{i}")
        cnt = r.get(f"RequireItemCount{i}")
        if isinstance(idx, int) and idx > 0 and isinstance(cnt, int) and cnt > 0:
            mats.append([idx, cnt])
        ci = r.get(f"CreateItemIndex{i}")
        if isinstance(ci, int) and ci > 0:
            mn = r.get(f"CreateItemMin{i}") or 1
            mx = r.get(f"CreateItemMax{i}") or mn
            pb = r.get(f"CreateItemProbability{i}")
            prods.append([ci, int(mn), int(mx), round((pb / 1048576 * 100) if isinstance(pb, (int, float)) and pb > 0 else 100, 2)])
    out[t].append({
        "id": rid, "key": f"{t}_{rid}",
        "name": r.get("Name") or s.get("Name"),
        "level": lvl, "exp": r.get("Exp") or 0, "vigor": r.get("CostVigor") or 0,
        "expertise": bool(r.get("SpecialNeedExpertise")),
        "itemId": r.get("ItemID"), "icon": r.get("IconID"),
        "mats": mats, "prods": prods,
    })

for t in out:
    out[t].sort(key=lambda x: (x["level"], x["name"] or ""))

p = os.path.join(OUT, "recipes_raw.json")
with open(p, "w", encoding="utf-8") as f:
    json.dump({"generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"), "recipes": out}, f, ensure_ascii=False, indent=1)
print("saved", p, {k: len(v) for k, v in out.items()}, file=sys.stderr)
