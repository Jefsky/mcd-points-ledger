# 全量参赛项目覆盖度分析

> 2026-10-24 · 扫描活动页全部 **1052** 个报名仓库，抓取到 **878** 个项目的
> `MCP_INTEGRATION.md` + `README.md` 全文，逐词统计工具与能力维度的覆盖情况。

这份文档的作用是**让任何人可以复核我的差异化判断**，而不是宣布"我是唯一的"。
所有数字都来自下面的方法，任何人都可以重跑。

---

## 一、方法

### 数据来源

1. 通过 GitHub GraphQL 分页拉取官方仓库 `M-China/mcd-developer-innovation-challenge` 的全部
   OPEN Issue（12 页），从每个 Issue 正则提取参赛仓库地址。
   - 报名 Issue 数：**1049**
   - 去重后仓库数：**1049**
   - 补入已知参赛但可能未提交 Issue 的头部仓库后：**1052**

2. 对每个仓库，用 GraphQL 批量取 `HEAD:MCP_INTEGRATION.md` 与 `HEAD:README.md` 的 blob 文本。
   - 成功抓取：**878** 个（83.5%）
   - 未抓取：仓库已删除、改名、设为私有，或该仓库没有这两个文件

3. 对 35 个官方 MCP 工具名 + 7 个能力维度做正则匹配，统计每个维度被多少个项目提及。

### 复现方式

```python
# 步骤 1：拉全部报名 Issue
query { repository(owner:"M-China", name:"mcd-developer-innovation-challenge") {
  issues(first:100, after:$cursor, states:OPEN) {
    pageInfo{hasNextPage endCursor} nodes{number body} } } }

# 步骤 2：批量取文档（注意单个仓库不存在会导致整批 GraphQL 报错，需拆批 + 降级）
query { r0: repository(owner:"...", name:"...") {
  mcp: object(expression:"HEAD:MCP_INTEGRATION.md"){... on Blob{text}}
  rm:  object(expression:"HEAD:README.md"){... on Blob{text}} } }

# 步骤 3：正则统计
re.search(r'\b' + re.escape(tool) + r'\b', text)
```

> ⚠️ **踩坑记录**：`gh api graphql` 在存在 GraphQL 错误时**退出码为 1**，
> 即使 `data` 部分可用。这会让批处理误判为整体失败并退化成逐个拉取，速度慢一个数量级。
> 正确做法是解析 stdout JSON 而不是依赖退出码。

---

## 二、工具覆盖度（分母 = 878）

| 工具 | 覆盖项目数 | 覆盖率 |
|---|---:|---:|
| `query-meals` | 714 | 81.3% |
| `calculate-price` | 675 | 76.9% |
| `query-nearby-stores` | 651 | 74.1% |
| `create-order` | 599 | 68.2% |
| `list-nutrition-foods` | 545 | 62.1% |
| `query-meal-detail` | 532 | 60.6% |
| `now-time-info` | 511 | 58.2% |
| `query-store-coupons` | 495 | 56.4% |
| `query-my-coupons` | 464 | 52.8% |
| `auto-bind-coupons` | 459 | 52.3% |
| `available-coupons` | 418 | 47.6% |
| `campaign-calendar` | 397 | 45.2% |
| `query-my-account` | 341 | 38.8% |
| `order-list` | 329 | 37.5% |
| `cancel-order` | 295 | 33.6% |
| `delivery-query-stores` | 283 | 32.2% |
| `delivery-query-addresses` | 272 | 31.0% |
| `draw-lottery` | 271 | 30.9% |
| `mall-create-order` | 240 | 27.3% |
| `mall-points-products` | 203 | 23.1% |
| `party-order-create` | 191 | 21.8% |
| `delivery-create-address` | 177 | 20.2% |
| `query-lottery-info` | 162 | 18.5% |
| `query-promotions` | 135 | 15.4% |
| `query-my-prizes` | 129 | 14.7% |
| `mall-product-detail` | 126 | 14.4% |
| `query-meal-assistance` | 120 | 13.7% |
| `query-party-store` | 97 | 11.0% |
| `query-party-city` | 85 | 9.7% |
| `query-survey-coupon` | 84 | 9.6% |
| `query-party-store-date` | 68 | 7.7% |
| `query-party-store-session` | 68 | 7.7% |
| `mall-order-detail` | 53 | 6.0% |

**结论：35 个工具全部有人用，没有"完全无人使用"的工具。**
真正的红海是 `query-meals` / `calculate-price` / `query-nearby-stores` / `create-order`（点餐比价）；
相对稀疏的是 `mall-order-detail`（6.0%）、`query-party-store-*`（7.7%）、`query-survey-coupon`（9.6%）。

---

## 三、能力维度覆盖（分母 = 878）

| 能力维度 | 覆盖项目数 | 覆盖率 | 本项目 |
|---|---:|---:|:---:|
| **同名多 spuId 冲突** | 7 | **0.8%** | ✅ |
| **假上架检测**（status × downTime 交叉验证） | 10 | 1.1% | ✅ |
| **隐藏现金成本**（extTradePrice） | 19 | 2.2% | ✅ |
| **可抽次数计算** | 22 | 2.5% | ✅ |
| **净值核算**（折算每分价值） | 26 | 3.0% | ✅ |
| 过期积分沉没成本 | 196 | 22.3% | ✅ |
| 漏报校正（catRuleIds 全量查询） | 217 | 24.7% | ✅ |

**定位关键词分布：**

| 关键词 | 覆盖项目数 | 覆盖率 |
|---|---:|---:|
| 积分相关 | 524 | 59.7% |
| 有效期 / 时间窗 | 468 | 53.3% |
| 资产 / 管家 / 账本 | 262 | 29.8% |
| 验真 / 去伪 / 可信 | 204 | 23.2% |

---

## 四、与直接竞品的逐维度对照

直接竞品：`yurenpai/mc-points-steward`「麦享掌柜」（48 star，10-12 发布）

| 能力维度 | 竞品是否覆盖 | 我的实测结论 |
|---|:---:|---|
| 假上架检测 | ✅ | 竞品说 67%，我实测 **66%**（27 件标上架里 18 件窗口已过）—— 一致 |
| 隐藏现金成本 | ✅ | 竞品说全需另付现金，我实测 **9/9 全部命中 `extTradePrice`** —— 一致 |
| 漏报校正 | ✅ | 我实测漏报 **4 件**（需遍历 10 个 `catRuleIds` 分类规则） |
| 同名多 spuId | ✅ | 我实测 **1 组**（17076=100 分 / 17077=200 分） |
| 过期积分沉没 | ✅ | 我实测 **2077.6 / 7495.6 = 27.7%** |
| **可抽次数计算** | ❌ | 我实测 **52 次**（1249 ÷ 24） |
| **净值核算** | ❌ | 我把"积分=门槛券，真实成本=积分+现金"做成了强制步骤 |

**诚实的结论**：竞品在 5 个维度上与我重叠，而且它的数据深度不弱于我。

我**不主张**"假上架检测没人做过"——事实上 878 个项目里有 10 个在做，竞品也是其中之一。
这一点我第一版文档里写错了（当时样本只有 52 个，且竞品恰好不在样本里）。

我真正的差异只剩下两块：

1. **同名多 spuId 冲突检测**（全网 0.8% 覆盖）
2. **可抽次数 + 净值核算的组合**（竞品未涉及）

因此本项目的差异化不建立在"我发现了一个别人没发现的坑"上，而是建立在
**"我把所有坑做成了一个可复现的验真流程"** 上 —— `scripts/verify_shelf.py`
把这些检测打包成一个任何人都能跑的脚本，而不是散落在文档里的描述。

---

## 五、两次方法论错误（保留记录）

### 错误一：只看头部项目推断整条赛道

最初只统计了活动页排行榜**前 12 名**的工具提及率，得出「积分资产运营 0-2/12 稀疏，是蓝海」。

全量扫描后真相是：**524/878（59.7%）的项目涉及积分，262/878（29.8%）写着"资产/管家/账本"**。

> **教训**：头部项目的提及率不能代表赛道密度。中腰部早就挤满了。

### 错误二：差异化论证的分母漏了直接竞品

第二次扫描样本是 52 个项目，据此写下「假上架检测 0/52 覆盖」。
但**竞品 `yurenpai/mc-points-steward` 根本不在那 52 个样本里** —— 它是在抓取之后才加入榜单的。

如果这句话留在 README 里，就是一个会被评审当场拆穿的假声明。

修正方式：重新抓取全量 1052 个报名仓库，把竞品显式补进样本，重算。

> **教训**：差异化论证的分母必须包含**所有**竞争者，尤其是刚加入的。

---

## 六、这个项目真正想解决的问题

抛开排名，从工程角度看，麦当劳积分商城接口有三处会误导用户：

1. `status=2` 不代表还能换 —— 状态字段不随兑换窗口关闭而更新
2. `point` 是兑换门槛而非价格 —— 真实成本要看 `mall-product-detail` 的 `extTradePrice`
3. 默认查询不完整 —— 不遍历 `catRuleIds` 会漏报

这三点合在一起，会让一个基于官方接口的积分导购**给出用户根本用不了的建议**。

`scripts/verify_shelf.py` 就是为了把这三点变成一段可以随时重跑的检查。

---

*数据抓取时间：2026-10-24 · 样本：1052 个报名仓库 / 878 个成功抓取文档*
*本文档所有数字可用 `scripts/verify_shelf.py` 与本文所述方法复现*
