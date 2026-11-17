# -*- coding: utf-8 -*-
"""抓取配方涉及的全部物品属性（名称/描述/基准价/品质/可交易），用于判断真实来源。"""
import json, os, sys, re, time, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

BASE = "https://node.jx3box.com/item_merged/id/"
HDR = {"User-Agent": "Mozilla/5.0"}
DATA = os.path.join(os.path.dirname(__file__), "..", "data")
DATA = os.path.abspath(DATA)


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=HDR)
            return json.loads(urllib.request.urlopen(req, timeout=30).read())
        except Exception as e:
            if i == tries - 1:
                print("ERR", url, e, file=sys.stderr)
                return None
            time.sleep(1.2)


def main():
    rec = json.load(open(os.path.join(DATA, "recipes.json"), encoding="utf-8"))
    keys = []
    seen = set()
    for t in ("cooking", "medicine"):
        for r in rec["recipes"][t]:
            for x in r["mats"] + r["prods"]:
                k = x.get("k")
                if k and k not in seen:
                    seen.add(k)
                    keys.append(k)
    print(f"待抓 {len(keys)} 个物品", file=sys.stderr)

    out = {}
    chunk = 50
    groups = [keys[i:i + chunk] for i in range(0, len(keys), chunk)]

    def job(g):
        return get(BASE + ",".join(g) + "?per=50")

    with ThreadPoolExecutor(max_workers=5) as ex:
        for n, res in enumerate(ex.map(job, groups), 1):
            for x in (res or {}).get("list", []):
                did = str(x.get("id") or "")
                if "_" not in did:
                    continue
                desc = re.sub(r"<[^>]+>", "", x.get("Desc") or "")
                desc = re.sub(r'text="', "", desc).replace("</text>", "")
                desc = re.sub(r"\s+", " ", desc).strip()
                out[did] = {
                    "k": did,
                    "name": x.get("Name"),
                    "desc": desc,
                    "price": x.get("Price"),
                    "quality": x.get("Quality"),
                    "canTrade": bool(x.get("CanTrade")),
                }
            if n % 3 == 0:
                print(f"  {n}/{len(groups)} 批，已收 {len(out)}", file=sys.stderr)

    p = os.path.join(DATA, "items.json")
    json.dump({"fetchedAt": time.strftime("%Y-%m-%d %H:%M:%S"), "items": out},
              open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"物品 {len(out)} -> {p}", file=sys.stderr)


if __name__ == "__main__":
    main()
