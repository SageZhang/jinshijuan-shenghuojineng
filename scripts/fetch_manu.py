# -*- coding: utf-8 -*-
"""全量抓取 manufactures(按 type 过滤, 避免跨技能截断)
type 键: cooking=4(Cooking) medicine=7 tailoring=5 founding=6(锻造)
注意:
  - 配方 ID 空间按技能独立编号, 同一 ID 在不同技能下是不同配方
  - 接口单次最多返回 20 条 -> 带 type 时一次取 20 个 id 正好不截断
  - 新版配方(含本赛季「苍生铸世」)ID 一直排到 1498, 所以 MAXID 必须 > 1500
输出 data/manu_all.json
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://node.jx3box.com"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")

TYPES = {"cooking": 4, "tailoring": 5, "founding": 6, "medicine": 7}
MAXID = 1600          # 实测最大 1498(缝纫玄元系列), 留余量
BATCH = 20            # 接口单次最多返回 20 条


def get(url, retry=4):
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers=HDR)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except Exception:
            time.sleep(0.5 + i * 0.4)
    return None


def batch(t, ids, mode=""):
    url = f"{BASE}/manufactures?ids={','.join(map(str, ids))}&type={t}&client=std{mode}"
    for _ in range(3):
        d = get(url)
        if d is not None:
            return d
    return []


jobs = [(t, pid, list(range(s, min(s + BATCH, MAXID))))
        for t, pid in TYPES.items() for s in range(0, MAXID, BATCH)]

full = {}
with ThreadPoolExecutor(max_workers=8) as ex:
    for (t, pid, _ids), d in zip(jobs, ex.map(lambda j: batch(j[0], j[2]), jobs)):
        for r in d:
            if r.get("ProfessionID") in (None, pid):
                if r.get("ProfessionID") is None:
                    r["ProfessionID"] = pid
                full[(r.get("ProfessionID"), r["ID"])] = r
print("full", len(full), file=sys.stderr)

simp = {}
with ThreadPoolExecutor(max_workers=8) as ex:
    for (t, pid, _ids), d in zip(jobs, ex.map(lambda j: batch(j[0], j[2], "&mode=simple"), jobs)):
        for r in d:
            p = r.get("ProfessionID") or pid
            simp[(p, r["ID"])] = r
print("simple", len(simp), file=sys.stderr)

res = []
for (pid, i), r in sorted(full.items(), key=lambda kv: (kv[0][0] or 0, kv[0][1])):
    s = simp.get((pid, i)) or {}
    r["nLevel"] = s.get("nLevel")
    r["nName"] = s.get("nName") or s.get("Name")
    res.append(r)

json.dump({"generatedAt": time.strftime("%Y-%m-%d %H:%M:%S"), "list": res},
          open(os.path.join(DATA, "manu_all.json"), "w", encoding="utf-8"), ensure_ascii=False)

from collections import Counter
c = Counter(r.get("ProfessionID") for r in res)
print("profession:", sorted(c.items(), key=lambda x: -x[1]), file=sys.stderr)
for pid in sorted(c):
    ids = sorted(r["ID"] for r in res if r.get("ProfessionID") == pid)
    names = [r.get("Name") for r in res if r.get("ProfessionID") == pid][-6:]
    print("  pid", pid, "n=", c[pid], "maxid", ids[-1], names, file=sys.stderr)
