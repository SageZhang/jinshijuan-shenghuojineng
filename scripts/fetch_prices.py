# -*- coding: utf-8 -*-
"""从魔盒交易行接口抓取可交易物品的价格(四系全量)
用法: python scripts/fetch_prices.py --server 梦江南 [--mode low|median] [--refresh]
带本地缓存 data/price_cache_<server>.json, 重复跑只补新增物品
"""
import json, os, sys, time, argparse, urllib.request, urllib.parse
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "output")
HDR = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json"}
API = "https://next2.jx3box.com/api/item-price/{key}/detail?server={server}"


def get(url, retry=2):
    for i in range(retry + 1):
        try:
            req = urllib.request.Request(url, headers=HDR)
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except Exception:
            if i == retry:
                return None
            time.sleep(0.6)


def pick(key, server, mode):
    """返回 (价格金, 流动性) ；流动性判断"有价无市" """
    d = get(API.format(key=key, server=urllib.parse.quote(server)))
    if not d:
        return None, None
    prices = (d.get("data") or {}).get("prices") or []
    rows = [(float(x["unit_price"]), int(x.get("n_count") or 0)) for x in prices if x.get("unit_price")]
    if not rows:
        return None, None
    vals = sorted(v for v, c in rows)
    if mode == "median":
        total = sum(c for v, c in rows) or len(rows)
        acc, v = 0, vals[0]
        for vv, c in sorted(rows):
            acc += max(c, 1)
            if acc >= total / 2:
                v = vv
                break
    else:
        v = vals[0]
    stat = {"n": sum(c for _, c in rows), "t": len(rows),
            "lo": round(vals[0] / 10000, 2), "hi": round(vals[-1] / 10000, 2)}
    return v / 10000.0, stat


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="梦江南")
    ap.add_argument("--mode", default="low", choices=["low", "median"])
    ap.add_argument("--refresh", action="store_true", help="忽略缓存全量重抓")
    args = ap.parse_args()

    items = json.load(open(os.path.join(DATA, "items.json"), encoding="utf-8"))["items"]
    rec = json.load(open(os.path.join(DATA, "recipes.json"), encoding="utf-8"))["recipes"]
    used = {m["k"] for rs in rec.values() for r in rs for m in r["mats"] + r["prods"]}

    key2name = {k: v["name"] for k, v in items.items()}
    # 不能用 CanTrade 过滤: 新版生活技艺产物(苍生·磨石/熔锭/玄元装备)CanTrade 标记为 false,
    # 但交易行实际有大量挂单。一律查,查不到自然回 0。
    todo = sorted(used)
    print(f"可交易 {len(todo)} 项, 区服 {args.server}, 口径 {args.mode}", file=sys.stderr)

    cache_p = os.path.join(DATA, f"price_cache_{args.server}.json")
    cache = {}
    if os.path.exists(cache_p) and not args.refresh:
        cache = json.load(open(cache_p, encoding="utf-8"))
        print(f"缓存命中 {len(cache)} 项", file=sys.stderr)
    batch = [k for k in todo if args.refresh or k not in cache]

    done = 0

    def job(k):
        v, st = pick(k, args.server, args.mode)
        return k, v, st

    with ThreadPoolExecutor(max_workers=10) as ex:
        for k, v, st in ex.map(job, batch):
            done += 1
            cache[k] = {"p": round(v, 4) if v else 0, "d": st}
            if done % 100 == 0:
                print(f"  {done}/{len(batch)} 有价 {sum(1 for x in cache.values() if x['p']>0)}", file=sys.stderr)
            if done % 300 == 0:
                json.dump(cache, open(cache_p, "w", encoding="utf-8"), ensure_ascii=False)

    json.dump(cache, open(cache_p, "w", encoding="utf-8"), ensure_ascii=False)

    res, depth = {}, {}
    for k, v in cache.items():
        name = key2name.get(k)
        if not name or not isinstance(v, dict) or not (v.get("p") or 0) > 0:
            continue
        res[name] = v["p"]
        if v.get("d"):
            depth[name] = v["d"]

    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, f"prices_{args.server}.json")
    payload = {"server": args.server, "mode": args.mode,
               "fetchedAt": time.strftime("%Y-%m-%d %H:%M:%S"), "prices": res, "depth": depth}
    json.dump(payload, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    slim = os.path.join(DATA, "preset_prices.json")
    json.dump(payload, open(slim, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(f"有价 {len(res)}/{len(todo)} -> {p}", file=sys.stderr)


if __name__ == "__main__":
    main()
