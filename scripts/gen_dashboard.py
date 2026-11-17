# -*- coding: utf-8 -*-
"""把 recipes.json 注入模板,输出单文件工作台"""
import json, os, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "output")
os.makedirs(OUT, exist_ok=True)

TABS = ("cooking", "medicine", "founding", "tailoring")
d = json.load(open(os.path.join(DATA, "recipes.json"), encoding="utf-8"))
rec = d["recipes"]

slim = {t: [] for t in TABS}
for t in TABS:
    for r in rec.get(t, []):
        slim[t].append({
            "key": r["key"], "name": r["name"], "level": r["level"],
            "exp": r["exp"], "vigor": r["vigor"], "expertise": r["expertise"],
            "belong": r.get("belong") or 0, "q": r.get("quality") or 1,
            "mats": [{"name": m["name"], "count": m["count"]} for m in r["mats"]],
            "prods": [{"name": p["name"], "min": p["min"], "max": p["max"], "prob": p["prob"]} for p in r["prods"]],
        })

payload = {"generatedAt": d["generatedAt"], "recipes": slim}

keys = {}
for t in TABS:
    for r in rec.get(t, []):
        for m in r["mats"]:
            keys.setdefault(m["name"], m["k"])
        for p in r["prods"]:
            keys.setdefault(p["name"], p["k"])
payload["keys"] = keys

preset_path = os.path.join(DATA, "preset_prices.json")
if os.path.exists(preset_path):
    payload["preset"] = json.load(open(preset_path, encoding="utf-8"))

belong_path = os.path.join(DATA, "belongs.json")
if os.path.exists(belong_path):
    payload["belongs"] = json.load(open(belong_path, encoding="utf-8"))

# 物品真实来源：来自魔盒物品描述（"可以在XX商人购买到"）+ 配方表
item_db = {}
ipath = os.path.join(DATA, "items.json")
if os.path.exists(ipath):
    item_db = json.load(open(ipath, encoding="utf-8")).get("items", {})

has_recipe = set()
for t in TABS:
    for r in rec.get(t, []):
        for p in r["prods"]:
            has_recipe.add(p["name"])

RE_SHOP = re.compile(r"(购买到|可以购买|均可出售|均有出售|商店出售|杂货商|货郎)")
RE_MERCHANT = re.compile(r"在([^，。；\n\"]{2,9}?)(?:处|那里)?(?:可以)?购买到")
RE_GATHER = re.compile(r"(采集|神农|庖丁|挖宝|垂钓|钓鱼|剥取|开采|采矿|采药|砍伐|伐木)")
RE_DROP = re.compile(r"(掉落|宝箱|任务奖励|声望|首领|副本)")

sources = {}
stat = {"craft": 0, "shop": 0, "gather": 0, "market": 0}
for k, v in item_db.items():
    name = v["name"]
    desc = v.get("desc") or ""
    shop = bool(RE_SHOP.search(desc))
    gather = bool(RE_GATHER.search(desc)) or bool(RE_DROP.search(desc))
    m = RE_MERCHANT.search(desc)
    merchant = m.group(1).strip() if m else ""
    if name in has_recipe:
        src, avail = "craft", ["craft", "market"]
        stat["craft"] += 1
    elif shop:
        src, avail = "shop", ["shop", "market"]
        stat["shop"] += 1
    elif gather:
        src, avail = "market", ["market"]
        stat["gather"] += 1
    else:
        src, avail = "market", ["market"]
        stat["market"] += 1
    if gather and "self" not in avail and name not in has_recipe:
        avail = avail + ["self"]
    sources[name] = {"src": src, "a": avail, "m": merchant}
payload["sources"] = sources
print("来源分类:", stat)

js = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

tpl = open(os.path.join(ROOT, "templates", "dashboard.html"), encoding="utf-8").read()
html = tpl.replace("__DATA__", js)
p = os.path.join(OUT, "剑三生活技艺工作台.html")
open(p, "w", encoding="utf-8").write(html)
print("saved", p, round(len(html) / 1024, 1), "KB")
print("recipes:", {t: len(slim[t]) for t in TABS})
