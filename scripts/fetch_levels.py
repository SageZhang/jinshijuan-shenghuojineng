# -*- coding: utf-8 -*-
"""按 type 抓 mode=simple 拿真实 nLevel
type 键: cooking=4 medicine=7 tailoring=5 founding=6(锻造)
simple 模式会过滤掉客户端隐藏配方, 拿到的就是制造界面可见的配方
输出 data/levels.json : {"pid_id": level}
"""
import json, os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor

BASE = "https://node.jx3box.com"
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")

TYPES = {"cooking": 4, "medicine": 7, "tailoring": 5, "founding": 6}
MAXID = 1600
BATCH = 20


def get(url, retry=3):
    for i in range(retry):
        try:
            req = urllib.request.Request(url, headers=HDR)
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except Exception:
            time.sleep(0.4 + i * 0.5)
    return None


def fetch(t, ids, tries=3):
    url = f"{BASE}/manufactures?ids={','.join(map(str, ids))}&type={t}&client=std&mode=simple"
    for _ in range(tries):
        d = get(url)
        if d:
            return d
        time.sleep(0.3)
    return []


def job(args):
    t, ids = args
    d = fetch(t, ids)
    if not d and len(ids) > 4:          # 空返回 -> 拆小重试
        half = len(ids) // 2
        d = fetch(t, ids[:half]) + fetch(t, ids[half:])
    return t, d


jobs = [(t, list(range(s, min(s + BATCH, MAXID)))) for t in TYPES for s in range(0, MAXID, BATCH)]
out, seen = {}, {}
with ThreadPoolExecutor(max_workers=6) as ex:
    for t, data in ex.map(job, jobs):
        pid = TYPES[t]
        for r in data:
            lv = r.get("nLevel")
            if isinstance(lv, int) and r.get("ID"):
                out[f"{pid}_{r['ID']}"] = lv
                seen.setdefault(pid, set()).add(r["ID"])

missing = [k for k in TYPES if not seen.get(TYPES[k])]
if missing:
    print("WARN empty:", missing, file=sys.stderr)

json.dump(out, open(os.path.join(DATA, "levels.json"), "w", encoding="utf-8"), ensure_ascii=False)
from collections import Counter
c = Counter(k.split("_")[0] for k in out)
print("levels:", dict(c), "total", len(out), file=sys.stderr)
for pid in sorted(c):
    lv = sorted({v for k, v in out.items() if k.startswith(pid + "_")})
    print("  pid", pid, "n=", c[pid], "level", lv[:5], "...", lv[-5:], file=sys.stderr)
