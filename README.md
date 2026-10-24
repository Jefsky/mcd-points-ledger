<div align="center">

# 麦麦积分资产管家 · mcd-points-steward

**把麦当劳积分当成一项需要经营的资产，而不是一个只会递减的数字。**

基于麦当劳中国官方 MCP Server 的积分资产运营 Skill

[安装](#安装) · [四条工作流](#四条工作流) · [MCP 工具](#使用的-mcp-工具) · [参赛信息](#参赛信息)

</div>

---

## 为什么做这个

大部分人用麦当劳积分的方式是：攒着，等它自然清零。

问题在于——**积分是有兑换比的**。同样是 10,000 分，换成不同的东西，实际价值能差出一倍不止。但没人会告诉你哪个划算，因为没有人把这些东西放到一张表里比较过。

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

```
你当前有 12,480 积分

【积分性价比榜 · Top 5】
1. 麦辣鸡腿堡兑换券   需 8,000 分   折算 1 分 ≈ 0.45 元   ★★★★★
2. 薯条（中）         需 2,500 分   折算 1 分 ≈ 0.52 元   ★★★★☆
3. 早餐麦满分         需 1,800 分   折算 1 分 ≈ 0.58 元   ★★★☆☆

建议：优先兑换 #1，剩余 4,480 分留给 #2。
```

关键在**统一折算基准**——把不同商品都换算成「每 1 分值多少元」，选择才有依据。

### 2️⃣ 抽奖雷达 · 现在有积分抽奖吗，值不值得抽

不靠"活动通常在进行"的猜测，而是先取当前时间对齐活动窗口，再看积分够不够门槛，最后看你的历史中奖记录做运气基线。

| 情况 | 建议 |
|------|------|
| 积分不足门槛 | 先攒，不参与 |
| 期望值 > 门槛积分折算价值 | 建议参与 |
| 奖品折算价值低于积分成本 | 观望 |
| 活动已结束 | 明确告知，并给出下一阶段攒分节奏 |

### 3️⃣ 商城导购 · 帮我挑一个

问清目标（送人 / 自用 / 囤券）→ 核对每个商品的积分与库存 → 验证余额覆盖 → 给出 2–3 个方案 → **你确认后才兑换**。

积分不可逆，所以下单前一定会复述商品名、所需积分和兑换后余额。

### 4️⃣ 订单复盘 · 我是不是点贵了

```
复盘最近 12 单（合计 ¥287.40）

发现 3 个可优化点：
· 10/12 订单漏用了「免配送费券」（当时持有 2 张未用券）→ 约省 ¥12
· 10/18 与 10/19 各下一份麦辣鸡腿堡（¥21.5 ×2），合并套餐可省约 ¥8
· 6 单未使用积分抵扣，当时余额足够抵 ¥34.60

可改进空间：约 ¥54.60 / 月（约 19%）
```

大多数"点贵了"其实不是贵，是**漏叠了券**——所以复盘会把你的持券情况一起拉进来对照。

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

---

## 安装

### 前置条件

需要申请到麦当劳中国的 MCP Token。前往 [麦当劳 MCP 开放平台](https://open.mcd.cn/mcp)：

1. 右上角【登录】→ 手机号验证登录
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
