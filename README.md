<div align="center">

# 麦麦积分资产管家 · mcd-points-steward

**把麦当劳积分当成一项需要经营的资产，而不是一个只会递减的数字。**

基于麦当劳中国官方 MCP Server 的积分资产运营 Skill

[先看效果](#先看效果) · [四条工作流](#四条工作流) · [MCP 工具](#使用的-mcp-工具) · [安装](#安装) · [参赛信息](#参赛信息)

</div>

---

## 先看效果

**不用装、不用 Token、浏览器直接打开就能看到完整成品 —— 而且里面全是真实数据。**

[![离线演示](https://img.shields.io/badge/演示-真实%20MCP%20数据-brightgreen)](./demo/index.html)
[![MCP 官方数据](https://img.shields.io/badge/MCP-官方%20Server%2035%20个工具-blue)](https://github.com/M-China/mcd-mcp-server)
[![MIT](https://img.shields.io/badge/license-MIT-green)]

> **[→ 打开演示页](./demo/index.html)** — 四个 Tab 覆盖积分体检、抽奖雷达、商城导购、订单复盘
>
> 演示页数据于 2026-10-24 通过麦当劳官方 MCP **实际抓取**：会员积分账户、50 件商城商品、进行中的积分抽奖活动、卡包优惠券、10 笔历史订单。个人标识与门店信息已做部分脱敏。

评审同学如果不想申请 Token，点上面那个链接就能看到 Skill 基于真实数据的完整输出效果。

### 演示页里有什么

| Tab | 展示内容 | 真实数据看点 |
|-----|---------|------------|
| ① 积分体检 | 可用/累计/已用/已过期/将过期五项拆解 | 2,077.6 分已过期，占累计 27.7%——**钱漏在积分静默过期** |
| ② 抽奖雷达 | 活动状态、消耗、剩余次数、奖品池 | 「周六麦金喜抽奖」24 分/次，可抽 52 次，奖品含积分奖可回流 |
| ③ 商城导购 | 余额与商品门槛的匹配 | 50 件商品里积分门槛动辄数千，1,249 分**一件都换不到** → 正确答案是"别换" |
| ④ 订单复盘 | 10 笔订单、跨 5 家门店的可优化点 | 单价都正常，但积分过期 + 券未核销 = 更隐蔽的漏点 |

---

## 为什么做这个

大部分人用麦当劳积分的方式是：攒着，等它自然清零。

问题在于——**积分是有有效期的，也有兑换比的**。真实案例里，一位用户累计获得 7,495.6 积分，其中 **2,077.6 分（27.7%）已过期归零**，而同期 10 笔订单的单价全部正常。钱不是花贵的，是**漏掉的**。

这个 Skill 做的事情很朴素：**把散落在积分、商城、抽奖、订单里的信息拼成一张可决策的表，然后给出建议。**

它覆盖的是一条在本次大赛中少有人走的路。抽样活动页排行榜前 12 个头部项目统计，其 `MCP_INTEGRATION.md` 提及率：

| 能力域 | 头部项目提及率 | 本项目 |
|--------|--------------:|:-----:|
| 省钱点餐 / 预算比价 | 3–4 / 12 密集覆盖 | 不做 |
| 优惠券组合优化 | 3–4 / 12 密集覆盖 | 不做 |
| **积分 → 商城 → 抽奖 → 订单复盘** | **0–2 / 12 稀疏** | ✅ 主线 |

---

## 四条工作流

### 1️⃣ 积分体检 · 我有多少积分，能换什么

以下为**真实账户**的输出：

```
你的积分账户全貌
可用 1,249 ｜ 累计 7,495.6 ｜ 已用 4,169 ｜ 已过期 2,077.6 ｜ 本月将过期 0

⚠️ 已过期 2,077.6 分，占累计积分的 27.7% —— 每 4 枚积分里有 1 枚是白扔的

建议：当前余额在商城里换不到东西，优先投入 24 分/次的抽奖。
```

关键在**把"沉没积分"算出来**——`expiredPoint` 和 `currentMouthExpirePoint` 是用户最看不到的部分，也是最该先说的。

### 2️⃣ 抽奖雷达 · 现在有积分抽奖吗，值不值得抽

不靠"活动通常在进行"的猜测，而是先取当前时间对齐活动窗口，再看积分够不够门槛，最后看历史中奖记录做运气基线。

真实接口返回的判断依据：

| 字段 | 用途 |
|------|------|
| `status.code` / `activityStatusText` | 活动是否存在、进行中还是已结束 |
| `beginTime` / `endTime` | 与 `now-time-info` 比对，确认在窗口内 |
| `drawPoint` | 单次消耗（实测 24 分） |
| `drawDecision.resourceEligible` | 你是否够资格 |
| `prizes[].typeText` | 是「优惠券」还是「积分奖」——积分奖意味着积分可回流 |

真实案例：可用 1,249 分 ÷ 24 分 = **可抽 52 次**，奖品池含积分奖。

### 3️⃣ 商城导购 · 帮我挑一个

问清目标（送人 / 自用 / 囤券）→ 核对每个商品的积分与库存 → 验证余额覆盖 → 给出方案 → **你确认后才兑换**。

**但真实情况往往是"别换"**。实测 50 件在架商品里，积分门槛普遍在数千至数万级（Nike Book 2 联名款 8,888 分），而账户只有 1,249 分——一件都换不到。这时 Skill 会如实说明缺口，并指出 24 分/次的抽奖才是当前余额真正用得掉的通道。

> ⚠️ 这里有个容易踩的坑：商城里大量商品 `point=0`，但那是**需另付现金的活动权益**（品鉴会、生日派对），不是"0 分免费"。Skill 会区分两者，不做错误换算。

### 4️⃣ 订单复盘 · 我是不是点贵了

以下为**真实订单**的输出：

```
复盘最近 10 单（合计 ¥301.5，跨 5 家门店）

发现 3 个可优化点：
· 积分静默过期 2,077.6 分，占累计 27.7% —— 最被忽视的一项
· 持有「19.9 元王牌炸鸡任选 2」等券未核销 → 约省 ¥19.9
· 2026-06-21 同店两笔合计 ¥138.9，若用「人气经典随心配」组合可省约 ¥15

可改进空间：约 ¥55 / 半年（约 18%）
```

大多数"点贵了"其实不是贵，是**积分和券在静默过期**——所以复盘会把你的持券与积分明细一起拉进来对照。

---

## 使用的 MCP 工具

全部来自麦当劳中国官方 MCP Server（`https://mcp.mcd.cn`），共 12 个：

| 能力域 | 工具 |
|--------|------|
| 积分 | `query-my-account` |
| 商城 | `mall-points-products` · `mall-product-detail` · `mall-create-order` · `mall-order-list` |
| 抽奖 | `query-lottery-info` · `draw-lottery` · `query-my-prizes` |
| 订单 | `order-list` · `query-order` |
| 券 | `query-my-coupons` |
| 时间 | `now-time-info` |

调用流程详见 [MCP_INTEGRATION.md](./MCP_INTEGRATION.md)。

### ✅ 已完成真实调用验证

本项目不是"照着文档写的"，而是**实际连上了麦当劳 MCP Server 并调用成功**（2026-10-24）：

```json
{"protocolVersion":"2024-11-05",
 "serverInfo":{"name":"mcd-mcp","version":"1.0.0"}}
```

`tools/list` 返回 **35 个工具**，本项目依赖的 **12 个全部存在**。实际调用记录：

| 工具 | 实际返回 |
|------|----------|
| `query-my-account` | `availablePoint=1249` `accumulativePoint=7495.6` `expiredPoint=2077.6` |
| `mall-points-products` | 50 件在架商品，含 `point` / `status` / `selling` / 起止时间 |
| `query-lottery-info` | 「周六麦金喜抽奖」进行中 `drawPoint=24` `resourceEligible=true` |
| `order-list` | 10 笔历史订单，跨 5 家门店 |
| `query-my-coupons` | 卡包优惠券（如「19.9 元王牌炸鸡任选 2」） |

> 未执行的是**有副作用的写操作**（`mall-create-order` 真实扣积分下单、`draw-lottery` 真实抽奖）——避免在你不知情时消耗积分。Skill 本身已内置「下单前强制二次确认」约束。

---

## 安装

### 前置条件

需要申请到麦当劳中国的 MCP Token。前往 [麦当劳 MCP 开放平台](https://open.mcd.cn/mcp)：

1. 右上角【登录】→ **微信扫码**确认登录
2. 点击【控制台】→【激活】申请 MCP Token
3. 阅读并同意服务协议 → 复制 Token

### 方式一 · WorkBuddy（推荐）

1. 打开 WorkBuddy → 左侧【专家·技能·连接器】→【连接器】页签
2. 右上角【自定义连接器】→【配置MCP】
3. 填入以下 JSON，把 `YOUR_MCP_TOKEN` 替换为你的 Token：

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

4. 保存 → 在【自定义连接器】中启用 `mcd-mcp`
5. 把 `skills/mcd-points-steward/` 放入你的 Skill 目录并启用

### 方式二 · 其他 MCP Client

本 Skill 兼容任何支持 Streamable HTTP 的 MCP Client（Cherry Studio、Cursor、Trae、VS Code 等），配置同上。参考[官方接入文档](https://github.com/M-China/mcd-mcp-server#2-快速开始)。

> 限流：每个 Token 每分钟最多 600 次请求。本 Skill 单次工作流通常在 10 次以内。

---

## 使用示例

```
「我有多少麦当劳积分，帮我算算怎么花最划算」
「现在有积分抽奖活动吗？我该参与还是继续攒」
「积分商城里有什么？帮我挑个送人的」
「复盘我最近的麦当劳订单，看看哪里能省」
```

---

## 项目结构

```
mcd-points-steward/
├── README.md                        # 本文件
├── CONTEST_DECLARATION.md           # 参赛声明（官方模板，原文）
├── MCP_INTEGRATION.md               # MCP 接入与调用流程说明
├── mcp-config.example.json          # MCP 配置示例（环境变量占位符）
├── mcp-config.workbuddy.example.json
├── workbuddy.md                     # WorkBuddy 开发对话上下文
├── demo/
│   └── index.html                   # 离线演示页（免 Token，浏览器直接打开）
└── skills/
    └── mcd-points-steward/
        └── SKILL.md                 # Skill 定义
```

---

## 设计原则

- **先查余额再承诺** — 任何"你可以换 X"都以 `query-my-account` 的实际返回为依据
- **不编造商品与价格** — 商城数据一律来自 MCP 返回，拿不到就说拿不到
- **下单前二次确认** — 积分兑换不可逆，务必复述并等待明确同意
- **抽奖先验活动状态** — 用 `now-time-info` 校验时间窗，不凭感觉推断
- **折算标注依据** — 说明价值来源，无法确定时明说"价值待确认"

---

## 目标用户

- 麦当劳会员，积分余额有一定积累但不知道怎么用
- 习惯囤券、囤积分，希望把"资产"算清楚的人
- 想用 AI 管理日常消费决策的开发者

---

## 参赛信息

本项目是 **麦当劳程序员节创意开发大赛** 参赛作品。

- 活动主页：[m.mcd.cn/githubRelate](https://m.mcd.cn/githubRelate/index)
- 官方仓库：[M-China/mcd-developer-innovation-challenge](https://github.com/M-China/mcd-developer-innovation-challenge)
- 官方组织：[M-China](https://github.com/M-China)
- MCP 工具文档：[M-China/mcd-mcp-server](https://github.com/M-China/mcd-mcp-server)

> 本项目由参赛者独立开发，**非麦当劳官方产品**。所有餐品信息、积分余额、价格及供应状态均以麦当劳官方渠道的实时结果为准。本项目输出仅供参考，不构成任何专业建议。

## License

MIT
