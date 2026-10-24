# 麦当劳 MCP 接入说明

本项目**真实使用**麦当劳中国官方 MCP Server 的能力开发，未使用任何模拟数据或硬编码接口。

- 官方服务：`https://mcp.mcd.cn`
- 官方工具文档：[M-China/mcd-mcp-server](https://github.com/M-China/mcd-mcp-server)
- 协议：Streamable HTTP
- 身份认证：`Authorization: Bearer <用户自己的 MCP Token>`

> ⚠️ 本仓库中所有配置文件仅使用 `YOUR_MCP_TOKEN` 占位符，不含任何真实凭证。

---

## 使用的 MCP 工具清单

本 Skill 依赖以下 **12** 个麦当劳 MCP 工具，覆盖积分、商城、抽奖、订单、券、时间六个能力域。

> 下表描述与参数均取自 `tools/list` 的**实际返回**（2026-10-24 抓取，服务器版本 `mcd-mcp 1.0.0`，工具总数 **35**），非转述文档。

| # | 工具名 | 官方说明 | 入参 | 在本项目中的用途 |
|---|--------|----------|------|------------------|
| 1 | `query-my-account` | 查询用户积分账户详情 | 无 | 积分余额/累计/已用/**已过期**/本月将过期/冻结，作为一切计算的基准 |
| 2 | `mall-points-products` | 查询可兑换餐品券列表 | `catRuleIds`（可选类目筛选） | 列出积分商城可兑换商品（含所需积分 `point` 与状态 `status`） |
| 3 | `mall-product-detail` | 查询积分兑换商品详情 | `spuId` | 获取 SKU 规格、有效期等，用于精确换算积分→实物价值比 |
| 4 | `mall-create-order` | 创建积分兑换订单 | `spuId` `skuId` `count` `spuCategory` `addressId` | 用积分兑换实物并下单（仅支持 shopId=2） |
| 5 | `mall-order-list` | 查询麦麦商城订单列表 | `lastId` `size` | 追踪积分兑换历史（**注意**：`order-list` 不含商城订单） |
| 6 | `query-lottery-info` | 查看当前积分抽奖活动信息 | 无 | 活动状态、起止时间、`drawPoint` 消耗、**剩余可抽次数**、奖品列表 |
| 7 | `draw-lottery` | 参加一次当前积分抽奖并返回结果 | 无 | 参与抽奖（须先展示 `drawDecision.nextConsumption` 并获用户确认） |
| 8 | `query-my-prizes` | 查询积分抽奖获得的奖品 | `pageNum` `pageSize` | 已中奖记录（可用/已使用/已过期/已领取/已失效） |
| 9 | `order-list` | 查询麦当劳历史订单（**非商城订单**） | 无 | 复盘数据源：门店、实付、商品明细 |
| 10 | `query-order` | 查询订单详细信息 | `orderId` | 单笔订单的实付、券抵扣、积分抵扣明细 |
| 11 | `query-my-coupons` | 获取用户卡包中的优惠券资产 | `page` `pageSize` | 识别"漏用券"类浪费（**注意**：不校验当前门店可用性） |
| 12 | `now-time-info` | 获取当前时间信息 | 无 | 校验抽奖活动是否在进行中，计算可抽次数 |

---

## 调用流程

### 流程 A · 积分体检（默认入口）

```
query-my-account                 → 得到积分余额 points
        │
        ├──> mall-points-products   → 得到候选商品列表
        │           │
        │           └──> mall-product-detail  (逐项补齐价值信息)
        │
        └──> 计算兑换比 = 所需积分 / 折算价值
                    → 输出「积分性价比榜」+ 兑换建议
```

**设计意图**：先用 `query-my-account` 锁定基准，避免在不知道余额的情况下给出无法执行的建议。`mall-product-detail` 是按需调用，只对进入候选池的商品拉详情，减少请求数。

### 流程 B · 抽奖雷达

```
now-time-info            → 得到当前时间 now
        │
query-lottery-info       → 得到活动信息（门槛门槛门槛、奖品池、起止时间）
        │
        ├──> 对比 now 与活动起止时间 → 判断活动是否在进行
        ├──> query-my-account        → 判断积分是否达门槛
        └──> query-my-prizes         → 历史中奖记录，评估运气基线
                    → 输出「建议参与 / 建议观望 / 已结束」+ 期望值估算
```

**设计意图**：`now-time-info` 是必需的。积分抽奖活动有明确起止窗口，脱离时间校验直接建议"去抽"会产生无效操作。

### 流程 C · 商城导购

```
query-my-account         → 确认余额是否覆盖目标商品
        │
mall-points-products     → 候选商品
        │
mall-product-detail      → 精确积分与库存
        │
（用户确认）
        │
mall-create-order        → 执行兑换
```

**设计意图**：余额校验前置，避免用户在余额不足时被引导去挑买不起的商品。下单是写操作，必须有用户显式确认。

### 流程 D · 订单复盘

```
order-list               → 历史订单列表
        │
        └──> query-order (逐单)   → 实付 / 券抵扣 / 积分抵扣
                    │
query-my-coupons         → 当时持有的券
                    │
                    → 标注：漏用券 / 积分未抵扣 / 重复下单
                    → 输出可量化的月度改进空间
```

**设计意图**：`order-list` 只给摘要，实付与抵扣细节在 `query-order` 里，因此复盘必须逐单展开。叠加 `query-my-coupons` 是关键——很多"点贵了"其实不是贵，而是漏叠了券。

---

## 实测验证记录

本项目已在真实环境完成 MCP 握手与工具调用，**非文档推断**。以下为 2026-10-24 17:19 的实际调用记录。

### 握手

```json
{"jsonrpc":"2.0","id":1,"result":{
  "capabilities":{"tools":{}},
  "protocolVersion":"2024-11-05",
  "serverInfo":{"name":"mcd-mcp","version":"1.0.0"}
}}
```

`tools/list` 返回 **35 个工具**（官方 README 记录为 33 个，服务端已新增 `query-promotions`、`query-survey-coupon`、`query-party-store-session`）。本项目依赖的 12 个工具**全部存在且已逐一核对**。

### 真实调用结果

| 工具 | 调用结果 |
|------|----------|
| `query-my-account` | ✅ `availablePoint=1249`、`accumulativePoint=7495.6`、`usedPoint=4169`、`expiredPoint=2077.6`、`frozenPoint=0`、`currentMouthExpirePoint=0`、`currency=麦享会积分` |
| `now-time-info` | ✅ `datetime=2026-10-24T17:19:11`、`timezone=GMT+08:00` |
| `mall-points-products` | ✅ 返回 **50** 件在架商品，含 `spuName` / `point` / `selling` / `upTime` / `downTime` / `catName` / `status` / `price` |
| `query-lottery-info` | ✅ 活动「周六麦金喜抽奖」`activityStatusText=进行中`、`drawPoint=24`、`availablePoint=1249`、`drawDecision.resourceEligible=true`、奖品池含积分奖 |
| `query-my-coupons` | ✅ 返回卡包优惠券（如「19.9 元王牌炸鸡任选 2」） |
| `order-list` | ✅ 返回 **10** 笔历史订单，含 `storeName` / `realTotalAmount` / `orderProductList` |
| `mall-order-list` | ✅ 返回积分商城订单记录 |

### 实测暴露的三个关键认知

这些不是设计假设，而是真实数据揭示的、容易做错的地方：

**1. `point=0` 不等于免费。** 商城 50 件商品中大量条目 `point=0`，但其 `price=0` 表示**非积分结算项**（品鉴会、生日派对、读书会等需另付现金的活动权益）。若把 `point=0` 当成"0 分可换"，会给出完全错误的导购结论。

**2. 余额不足时，正确答案是「别换」。** 实测用户可用 1,249 分，而真实积分商品的门槛在数千至数万级（如 Nike Book 2 联名款 8,888 分）——当前余额一件都换不到。此时 Skill 必须如实说明缺口并给出替代出口（24 分/次的小门槛抽奖），而不是硬凑一个买不起的方案。

**3. 钱漏在"静默过期"，不在"单价高"。** 实测账户累计 7,495.6 积分中 **2,077.6 分（27.7%）已过期**，而 10 笔历史订单单价全部正常。复盘的价值因此不在"你点贵了"，而在指出这个更隐蔽、金额更大的漏点。

---

## 工具选择理由

本项目**有意避开**已被大量参赛项目覆盖的赛道，转而深耕积分资产运营这一相对空白的方向。

在活动页公开的排行榜样本中，抽样 12 个头部项目的 `MCP_INTEGRATION.md` 统计工具提及率：

| 工具 | 提及率 | 本项目是否使用 |
|------|-------:|---------------|
| `auto-bind-coupons` | 4/12 | 否 |
| `calculate-price` / `create-order` / `query-meals` | 3/12 | 否 |
| `query-my-coupons` / `query-store-coupons` | 3/12 | 仅 `query-my-coupons`（用于复盘） |
| `mall-points-products` | 2/12 | ✅ |
| `query-my-account` | 2/12 | ✅ |
| `campaign-calendar` | 2/12 | 否 |
| `mall-order-list` | 1/12 | ✅ |
| `mall-product-detail` | 1/12 | ✅ |
| `mall-create-order` | 1/12 | ✅ |
| `query-lottery-info` / `draw-lottery` | 1/12 | ✅ |
| `query-my-prizes` | 1/12 | ✅ |
| `query-order` | 1/12 | ✅ |
| `query-meal-assistance` | 1/12 | 否 |
| `party-order-create` | 1/12 | 否 |

**结论**：本项目使用的 12 个工具中，有 8 个在头部样本中的覆盖率 ≤ 2/12，集中在「积分资产 → 商城 → 抽奖 → 订单复盘」这条闭环上。这条线把用户的积分从"一个会减少的数字"变成"一项可运营的资产"，是本项目区别于省钱点餐类项目的核心设计。

---

## 业务价值

1. **积分闲置可见化** — 大多数人不知道积���能换什么、换哪个划算。本项目把商城商品换算成统一的「每积分折算价值」指标，让选择有依据。
2. **抽奖决策有依据** — 活动窗口、积分门槛、历史中奖记录三要素齐备后再给建议，避免"抽了再说"。
3. **兑换前强制确认** — 积分不可逆，兑换前复述商品、积分与余额后等待确认。
4. **浪费点可量化** — 订单复盘把"你好像没点好"变成"本月约 ¥54.60 / 19% 可改进空间"。

---

## 使用方式

### 在 WorkBuddy 中接入

1. 打开 WorkBuddy → 左侧【专家·技能·连接器】→【连接器】页签
2. 点击右上角【自定义连接器】→【配置MCP】
3. 填入以下 JSON（替换 `YOUR_MCP_TOKEN` 为你的 MCP Token）：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": {
        "Authorization": "Bearer YOUR_MCP_TOKEN"
      }
    }
  }
}
```

4. 保存后在【自定义连接器】中启用 `mcd-mcp`
5. 将 `skills/mcd-points-steward/` 目录放入你的 Skill 目录并启用

### 申请 MCP Token

前往 [麦当劳 MCP 开放平台](https://open.mcd.cn/mcp)：右上角【登录】→ 手机号验证登录 → 【控制台】→ 【激活】申请 Token → 阅读并同意服务协议 → 复制 Token。

> 限流提示：每个 Token 每分钟最多 600 次请求。本 Skill 的默认工作流单次调用通常在 10 次以内。

---

## 声明

本项目为麦当劳程序员节创意开发大赛参赛作品，由参赛者独立开发，**非麦当劳官方产品**。所有餐品信息、积分余额、价格及供应状态均以麦当劳官方渠道的实时结果为准。本项目输出仅供参考，不构成任何专业建议。
