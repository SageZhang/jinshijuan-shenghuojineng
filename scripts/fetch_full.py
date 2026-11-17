# -*- coding: utf-8 -*-
"""魔盒 manufactures 接口分页失效,改用 ids 批量(每批20,带type过滤)全量抓取"""
import json, urllib.request, time, os, sys
from concurrent.futures import ThreadPoolExecutor

BASE = "https://node.jx3box.com"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
OUT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
os.makedirs(OUT, exist_ok=True)


def get(url, retry=3):
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers=HDR)
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except Exception:
            time.sleep(0.8)
    return []


def chunk_batch(t, ids):
    url = f"{BASE}/manufactures?ids={','.join(map(str, ids))}&type={t}&client=std"
    return t, get(url)


MAXID = 1500
BATCH = 15
jobs = [(t, list(range(s, min(s + BATCH, MAXID))))
        for t in ("cooking", "medicine")
        for s in range(0, MAXID, BATCH)]

res = {"cooking": {}, "medicine": {}}
with ThreadPoolExecutor(max_workers=6) as ex:
    done = 0
    for t, data in ex.map(lambda j: chunk_batch(*j), jobs):
        done += 1
        for r in data or []:
            if r.get("ID"):
                res[t][r["ID"]] = r
        if done % 40 == 0:
            print(f"{done}/{len(jobs)} cooking={len(res['cooking'])} medicine={len(res['medicine'])}", file=sys.stderr)

# simple 模式补 nLevel(同样用 ids 批)
simp = {"cooking": {}, "medicine": {}}
jobs2 = [(t, list(range(s, min(s + BATCH, MAXID)))) for t in ("cooking", "medicine") for s in range(0, MAXID, BATCH)]


def chunk_simple(t, ids):
    url = f"{BASE}/manufactures?ids={','.join(map(str, ids))}&type={t}&client=std&mode=simple"
    return t, get(url)


with ThreadPoolExecutor(max_workers=6) as ex:
    for t, data in ex.map(lambda j: chunk_simple(*j), jobs2):
        for r in data or []:
            if r.get("ID"):
                simp[t][r["ID"]] = r

print("full:", {k: len(v) for k, v in res.items()}, "simple:", {k: len(v) for k, v in simp.items()}, file=sys.stderr)

out = {"cooking": [], "medicine": []}
for t in res:
    for rid, r in res[t].items():
        s = simp[t].get(rid, {})
        lvl = s.get("nLevel") or r.get("RequireLevel") or 0
        if lvl >= 250:
            lvl = 0
        mats, prods = [], []
        for i in range(1, 9):
            idx = r.get(f"RequireItemIndex{i}")
            cnt = r.get(f"RequireItemCount{i}")
            if isinstance(idx, int) and idx > 0 and isinstance(cnt, int) and cnt > 0:
                mats.append([idx, cnt])
            ci = r.get(f"CreateItemIndex{i}")
            if isinstance(ci, int) and ci > 0:
                mn = r.get(f"CreateItemMin{i}") if isinstance(r.get(f"CreateItemMin{i}"), int) else 1
                mx = r.get(f"CreateItemMax{i}") if isinstance(r.get(f"CreateItemMax{i}"), int) else mn
                pb = r.get(f"CreateItemProbability{i}")
                prods.append([ci, max(mn, 1), max(mx, mn, 1),
                              round(pb / 1048576 * 100, 2) if isinstance(pb, (int, float)) and pb > 0 else 100])
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
json.dump({"generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"), "recipes": out},
          open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("saved", p, {k: len(v) for k, v in out.items()}, file=sys.stderr)
# 材料索引集合
mids = sorted({m[0] for t in out for r in out[t] for m in r["mats"]})
print("mat idx count", len(mids), mids[:80], file=sys.stderr)
