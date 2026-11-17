# 剑网3 生活技艺工作台

面向《剑网3》「苍生铸世」赛季（50 级）的**生活技艺收益测算台**。覆盖 **烹饪 / 医术 / 锻造 / 缝纫** 四系技艺：自动抓取全部配方与梦江南交易行行情，算出单次工本、净收益、单精力收益、升级路径，并支持 BOM 逐层拆解与自制/采购切换。

产物是一个**单文件 HTML**，双击即可打开，无需服务器、无需构建。

```
output/剑三生活技艺工作台.html
```

## 功能

| 模块 | 说明 |
|---|---|
| ① 收益排行 | 按成品算「工本 / 净收入 / 单次净利 / 利润率 / 单精力 / 在售件数」，表头可排序，支持技艺、产出定位、等级、区服筛选 |
| ② 生产计划 | 输入生产次数，汇总总成本、总收益、总精力、总经验（含自制中间件递归折算） |
| ③ 升级路径 | 逐等级给出「做哪个配方最省 / 最赚」，自动跳过无等级门槛的秘籍配方 |
| ④ 材料与价格 | 按真实来源分组（自制 / 商店 / 交易行 / 自采），可逐个改价，价格存 localStorage |
| BOM 展开 | 点成品名逐层展开材料树，每层显示单价与小计，可把任意节点从「自制」切成「采购」 |
| 交易行手续费 | 默认 5%，可调，收入一律按税后算 |

### 几个关键设计

- **来源判定不猜**：按物品 `Desc` 字段（「小提示：可以在菜贩商购买到」等）+ 配方产物表判定自制 / 商店 / 采集 / 交易行，商店价与交易行价分开存，切换来源时价格同步切换。
- **钓鱼价过滤**：挂单价 > 工本 50 倍视为占位价，标「价疑」沉底并排除出 KPI 与路径规划。
- **等级口径**：`nLevel`（界面可见）> `RequireLevel`；都取不到 = 秘籍/旧配方，按 1 级参与可做性判断、显示「—」、**不参与升级路径**。
- **产出定位**按魔盒 `manufacture/belong` 的真实分类判定：小吃 / 小药 / 宴席 / 消耗 / 装备 / 半成品 / 杂项。

## 数据管线

```
fetch_manu.py     → data/manu_all.json    全量配方（4 系，含材料与产物）
fetch_levels.py   → data/levels.json      配方真实等级（mode=simple）
build_recipes.py  → data/recipes.json     合成数据集 + data/items.json 物品元数据
fetch_prices.py   → data/preset_prices.json / output/prices_<区服>.json   交易行行情
gen_dashboard.py  → output/剑三生活技艺工作台.html                        注入数据出页面
```

重新生成全流程：

```bash
python scripts/fetch_manu.py
python scripts/fetch_levels.py
python scripts/build_recipes.py
python scripts/fetch_prices.py --server 梦江南
python scripts/gen_dashboard.py
```

行情带本地缓存（`data/price_cache_<区服>.json`），重复跑只补新增物品。

### 数据来源（魔盒 JX3BOX）

| 接口 | 用途 |
|---|---|
| `node.jx3box.com/manufactures?ids=&type=&client=std` | 配方本体（材料、产物、精力、经验、分类） |
| `node.jx3box.com/manufactures?...&mode=simple` | 同上但带 `nLevel`，会滤掉客户端隐藏配方 |
| `node.jx3box.com/manufacture/belong?client=std` | 产物分类字典（剑 / 帽子 / 席 / 制品 / 消耗品…） |
| `node.jx3box.com/item_merged/id/<type>_<index>?per=40` | 物品名称、描述、回收价、是否可交易 |
| `next2.jx3box.com/api/item-price/{key}/detail?server=` | 交易行挂单档位（单位铜，1 金 = 10000 铜） |

### 踩过的坑（改代码前必读）

1. **锻造的 type 键是 `founding`**，不是 `forging`，拼错返回空数组。
2. **配方 ID 按技能独立编号**：同一个 ID 在四系里是四个不同配方（如 394 = 风语·毛血旺 / 拼布紫2补充包 / 五气归元丹）。不带 `type` 查询时同一批 ids 会返回多技能记录，且**单次响应上限 20 条**，必须带 type 每批 20 个 id。
3. **ID 空间远超 1200**：缝纫最大 1498、锻造 1343。上限设 1200 会把「苍生铸世」整段新配方全丢掉（MAXID 现设 1600）。
4. **物品键要带类型**：`CreateItemType` 为 `5` 是材料、`7` 是装备。硬编码 `5_{index}` 会让玄元衫/鞋/护腕这类装备名称与价格全部查不到。
5. **`CanTrade` 不可信**：苍生·磨石/熔锭、玄元装备标记为不可交易，但交易行有大量挂单，抓价不能按它过滤。

## 部署

`deploy/craft/` 是静态部署目录（`index.html` + 行情快照），可直接丢进任意静态托管（Nginx / GitHub Pages / Vercel）。

```bash
cp output/剑三生活技艺工作台.html deploy/craft/index.html
cp output/prices_梦江南.json deploy/craft/
```

## 当前数据规模

| 技艺 | 配方数 | 可交易产物 |
|---|---|---|
| 烹饪 | 430 | 461 |
| 医术 | 377 | 246 |
| 锻造 | 1256 | 1357 |
| 缝纫 | 1261 | 1446 |

物品元数据 4877 项；梦江南有价 1315 项。

## 免责

数据来自魔盒公开接口，行情为抓取时点快照，交易行价格波动大，收益测算仅供参考。等级经验曲线为估算（`60 × 1.075^(L-1)`），页面支持逐级修正。
