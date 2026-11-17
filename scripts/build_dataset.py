# -*- coding: utf-8 -*-
"""补全材料/成品名称,生成最终 recipes.json"""
import json, urllib.request, time, os, sys
from concurrent.futures import ThreadPoolExecutor

BASE = "https://node.jx3box.com"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")


def get(url, retry=3):
    for _ in range(retry):
        try:
            req = urllib.request.Request(url, headers=HDR)
            with urllib.request.urlopen(req, timeout=25) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except Exception:
            time.sleep(0.7)
    return {}


raw = json.load(open(os.path.join(DATA, "recipes_raw.json"), encoding="utf-8"))
recipes = raw["recipes"]

# 只保留有效等级(1-100)的配方
clean = {"cooking": [], "medicine": []}
for t in ("cooking", "medicine"):
    for r in recipes[t]:
        lv = r.get("level") or 0
        if not (1 <= lv <= 100):
            continue
        if not r.get("name"):
            continue
        clean[t].append(r)
print("clean:", {k: len(v) for k, v in clean.items()}, file=sys.stderr)

# 收集所有需要命名的 key
keys = set()
for t in clean:
    for r in clean[t]:
        for m in r["mats"]:
            keys.add(f"5_{m[0]}")
        for p in r["prods"]:
            keys.add(f"5_{p[0]}")
keys = sorted(keys)
print("keys:", len(keys), file=sys.stderr)

batches = [keys[i:i + 10] for i in range(0, len(keys), 10)]
names = {}


def job(b):
    d = get(f"{BASE}/item_merged/id/{','.join(b)}")
    return {x["id"]: x.get("Name") for x in (d.get("list") or [])}


with ThreadPoolExecutor(max_workers=5) as ex:
    for i, d in enumerate(ex.map(job, batches)):
        names.update(d)
        if i % 20 == 0:
            print(f"{i}/{len(batches)} names={len(names)}", file=sys.stderr)

print("names:", len(names), file=sys.stderr)


def nm(k):
    n = names.get(k) or k
    return n.replace("【印象】", "").replace("【声望】", "")


out = {"cooking": [], "medicine": []}
for t in clean:
    for r in clean[t]:
        mats = [{"k": f"5_{m[0]}", "name": nm(f"5_{m[0]}"), "count": m[1]} for m in r["mats"]]
        prods = [{"k": f"5_{p[0]}", "name": nm(f"5_{p[0]}"), "min": p[1], "max": p[2], "prob": p[3]} for p in r["prods"]]
        out[t].append({
            "key": r["key"], "id": r["id"], "name": r["name"],
            "level": r["level"], "exp": r["exp"], "vigor": r["vigor"],
            "expertise": r["expertise"],
            "mats": mats, "prods": prods,
        })

for t in out:
    out[t].sort(key=lambda x: (x["level"], x["name"]))

payload = {"generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"), "source": "node.jx3box.com/manufactures", "recipes": out}
json.dump(payload, open(os.path.join(DATA, "recipes.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)

for t in out:
    lv = sorted({r["level"] for r in out[t]})
    print(t, len(out[t]), "levels:", lv[:5], "...", lv[-5:] if len(lv) > 5 else "", file=sys.stderr)
    print("  lv50 count:", sum(1 for r in out[t] if r["level"] == 50), file=sys.stderr)
print("saved recipes.json", os.path.getsize(os.path.join(DATA, "recipes.json")), "bytes", file=sys.stderr)
