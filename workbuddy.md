# WorkBuddy 开发记录

本文件记录「麦麦积分资产管家（mcd-points-steward）」从立项到成品的完整开发过程，保留真实的用户输入、WorkBuddy 的分析与决策、以及实际验证结果。

**参与方**：本项目由参赛者在腾讯 WorkBuddy 智能体中完成开发。WorkBuddy 承担了以下工作：活动规则逆向分析、赛道机会识别、Skill 设计与文档撰写、代码仓库初始化与发布。

**未执行的验证一律写明未验证。** 本次开发中麦当劳 MCP Token 未能完成申请（见文末「未验证项」），因此涉及真实 MCP 调用的部分均如实标注为未验证。

---

## 第一轮：活动规则逆向分析与赛道路线选择

### 用户输入

```text
https://m.mcd.cn/githubRelate/index?hiddenHeader=1&pageSource=Me&envH=r2&iss=https%3A%2F%2Fgithub.com%2Flogin%2Foauth
```

（附一句「你可以帮我参加吗」）

### WorkBuddy 的分析过程

首先抓取页面 HTML 与全部 JS 分包（`0.97a36535.chunk.js` / `1.a6634bfb.chunk.js` / `Index.b7160b7.62263b71.chunk.js`），在压缩代码中定位到活动相关的接口定义：

```js
getGitHubAuthConfig: (t, e) => l.get("/member/api/v1/github-auth/info", { params: t, headers: e }),
receiveCoupon:      (t, e) => l.post("/member/api/v1/github-auth/claim-reward", { params: t, headers: e }),
bindCode:           (t, e) => l.post("/passport/account/github/bind", { params: t, headers: e }),
getSkillRank:      () => l.get("/market/code/mcp/skill/ranking", {}),
```

由此还原出领券流程的四个环节：会员登录取 `sid` → GitHub OAuth 拿 `code` → `bindCode` 绑定 → `receiveCoupon` 领券。

用 HAR 抓包拿到真实请求头，发现接口带 HMAC-SHA256 签名（`hmac-auth-v1` + `x-hmac-dig` 头），且带时效性——直接重放请求会返回 `401 client request can't be validated`，确认必须走真实浏览器页面。

调通网络后拿到 `/github-auth/info` 的真实返回（页面自行生成签名）：

```json
{
  "userStatus": 0,
  "githubClientId": "Ov23lijxoTdTnFyoYUMI",
  "activityRule": "1.活动时间：【2026】年【10】月【23】日至【2026】年【10】月【25】日……",
  "mcpActivityImage": "https://img.mcd.cn/gallery/e6880d47b8cd40ee.png"
}
```

`activityRule` 中「参与渠道：麦当劳官方APP的开发者认证活动页面」以及「禁止通过机器人软件/脚本工具参与活动」两条，被识别为**方案选择的硬约束**：领券环节不宜由自动化代跑。

### 关键发现：页面里藏了第二个活动

`mcpActivityImage` 指向一张 1125×5970 的长图，拆分后读取，得到**「麦当劳程序员创意开发大赛」**的完整规则。这与领券是并列的独立活动，且 `getSkillRank` 接口（`/market/code/mcp/skill/ranking`）对应的排行榜页确实存在。

官方组织确认为 `M-China`，官方仓库 `M-China/mcd-developer-innovation-challenge`。

### 赛道路线决策

从官方仓库取得 `activityGuidelines.md`，确认排名的唯一依据是 **GitHub 公开 Star 数**：

> 对符合要求的参赛项目，麦当劳按照其在 GitHub 平台获得的公开 Star 数量……进行排名，并于活动页面中公布排行榜。

规则要点整理如下：

| 事项 | 规定 |
|------|------|
| 报名截止 | 2026-10-25 23:59（北京时间） |
| 榜单定格 | 2026-10-26 00:00 |
| 仓库创建时间 | 须在 2025-12-25 ~ 2026-10-25 之间 |
| 必交文件 | README.md / CONTEST_DECLARATION.md / MCP_INTEGRATION.md / mcp-config.example.json / workbuddy.md（文件名不可改） |
| 获奖范围 | 前 100 名全员获奖（实体周边 + WorkBuddy 3000 积分），前三名额外获巨无霸兑换券 + 10240 积分 |
| 同账号多项目 | 仅 Star 数最高的计入 |

**空白赛道识别**：编写脚本抓取活动页排行榜前 12 个头部项目的 `MCP_INTEGRATION.md`，统计 33 个麦当劳 MCP 工具的提及率：

| 工具 | 头部提及率 |
|------|:---------:|
| `auto-bind-coupons` | 4/12 |
| `calculate-price` / `create-order` / `query-meals` / `query-my-coupons` / `query-store-coupons` | 3/12 |
| `mall-points-products` / `query-my-account` / `mall-order-list` / `order-list` | 2/12 |
| `draw-lottery` / `mall-create-order` / `mall-order-detail` / `mall-product-detail` / `query-lottery-info` / `query-my-prizes` / `query-order` | 1/12 |
| `mall-order-detail` / `query-party-*` 系列 | 0/12 |

结论明确：省钱点餐、预算比价、优惠券组合三条线已被头部项目密集覆盖（榜首 `mcd-budget-meal` 1209 star、第 4 名 `mcd-saver-strategist` 1139 star、第 6 名 `mcd-coupon-strategist` 998 star 同属此类），而「积分资产运营」这条闭环覆盖稀疏。

### 用户决策

在向用户说明两个活动的收益结构与规则约束后，用户选择主攻 Skill 创意开发大赛（而非价值 20.48 元的领券活动），并确认已有麦当劳会员账号且已登录 APP。

---

## 第二轮：Skill 设计

### 设计出发点

Skill 的一句话定位：

> 把麦当劳积分当成一项需要经营的资产，而不是一个只会递减的数字。

**目标用户**是积分有积累但不知道怎么用的人。**核心洞察**是：积分存在兑换比——同样 10,000 分换不同东西，实际价值能差出一倍，但没人把商城商品换算到同一基准上比较。

**四条工作流**对应四种真实需求：

| 工作流 | 用户意图 | 覆盖的 MCP 工具 |
|--------|---------|----------------|
| 积分体检 | 我有多少积分、能换什么、哪个划算 | `query-my-account` `mall-points-products` `mall-product-detail` |
| 抽奖雷达 | 现在有抽奖吗、值不值得抽 | `now-time-info` `query-lottery-info` `query-my-prizes` `draw-lottery` |
| 商城导购 | 帮我挑一个（送人/自用/囤券） | `mall-points-products` `mall-product-detail` `mall-create-order` |
| 订单复盘 | 我是不是点贵了 | `order-list` `query-order` `query-my-coupons` |

**设计决策及其理由**：

1. **先查余额再承诺** —— 任何「你可以换 X」必须以 `query-my-account` 的实际返回为依据，避免给出无法执行的建议。
2. **抽奖先验时间窗** —— `now-time-info` 是必需调用项。积分抽奖有明确起止窗口，脱离时间校验直接建议「去抽」会产生无效操作。
3. **下单前二次确认** —— 积分兑换不可逆，下单前复述商品、所需积分、兑换后余额，等待用户明确同意。
4. **折算必须标注依据** —— 用「折算 1 分 ≈ X 元」时说明 X 的来源；无法确定时明说「价值待确认」，不编造。
5. **输出决策而非清单** —— 用户要的是「该换哪个」，不是「有什么」。

`SKILL.md` 中同时写入行为准则（必须遵守 / 避免）与隐私约束（积分余额、订单明细、地址等不得写入对外内容）。

---

## 第三轮：文档撰写与合规校验

### 参赛声明

`CONTEST_DECLARATION.md` 直接取自官方仓库原始文件，未做任何修改，并用 `gh api` 拉取官方版本做 diff 校验：

```
✅ CONTEST_DECLARATION.md 与官方完全一致（未修改）
```

### MCP_INTEGRATION.md

该文件是麦当劳核验「参赛项目须真实使用麦当劳 MCP 能力」的主要依据，因此内容包含：

- 官方服务地址、协议、认证方式与官方工具文档链接
- 12 个使用到的工具及其在四条工作流中的具体用途
- 四条工作流的**调用流程图**（工具间箭头关系）
- 每个工具的**选择理由**
- 业务价值说明
- 两种安装方式（WorkBuddy / 其他 MCP Client）

其中「工具选择理由」一节直接引用了第一轮统计出的头部项目提及率数据，把「为什么避开省钱点餐线」这件事量化呈现，而非仅作宣称。

### README.md

参考头部项目 `mcd-budget-meal` 的结构（README 12.8K / MCP_INTEGRATION 6.5K / workbuddy.md 21K / 含 docs、examples、tests、install.ps1），并结合本项目特点组织：

- 首屏一句话定位 + 价值主张
- **「为什么做这个」**一节，用工具提及率表格说明赛道选择
- 四条工作流各配一段**真实感的示例输出**（金额、积分均为示意）
- MCP 工具清单按能力域分组
- 两种安装方式 + 限流提示
- 目标用户、参赛信息、免责声明

---

## 第四轮：仓库发布

在 `mcd-points-steward/` 目录初始化 Git 仓库，`.gitignore` 排除 `.env`、`mcp-config.json` 等可能含凭证的文件，仅保留 `mcp-config.example.json`（`YOUR_MCP_TOKEN` 占位符）。

创建公开仓库并推送：

```
$ gh repo create Jefsky/mcd-points-steward --public \
    --description "麦麦积分资产管家：基于麦当劳 MCP 的积分体检、抽奖雷达、商城导购与订单复盘 Skill"
$ git push -u origin main
```

推送后核验远端文件清单，确认 5 个必交文件均已就位：

```
.gitignore
CONTEST_DECLARATION.md
MCP_INTEGRATION.md
README.md
mcp-config.example.json
mcp-config.workbuddy.example.json
skills/
```

仓库创建时间为 2026-10-24T08:52:27Z，满足「2025-12-25 ~ 2026-10-25」的创建时间要求。

---

## 未验证项（如实说明）

以下内容在本次开发中**未能实际执行**，如实列出：

| 项目 | 状态 | 原因 |
|------|------|------|
| 麦当劳 MCP Token 申请 | **未完成** | 需在 `open.mcd.cn/mcp` 用手机号验证登录并同意服务协议。开发环境内浏览器标签页无法稳定保持会话（页面加载成功后 `eval` 落到 `about:blank`），自动化操作无法可靠完成该流程，需人工在浏览器中完成。 |
| 12 个 MCP 工具的真实调用 | **未验证** | 依赖上述 Token。工具名、参数、返回结构均依据官方 [M-China/mcd-mcp-server](https://github.com/M-China/mcd-mcp-server) 的工具列表逐条核对，包括：`query-my-account`（我的积分查询，含可用/累计/冻结/即将过期积分）、`mall-points-products`、`mall-product-detail`、`mall-create-order`（积分兑换下单）、`mall-order-list`、`query-lottery-info`（含活动状态、奖品列表、抽奖消耗规则）、`draw-lottery`、`query-my-prizes`、`order-list`（到店/外送历史订单，非商城订单）、`query-order`、`query-my-coupons`、`now-time-info`。工具名与官方文档完全一致，但**尚未发起过真实调用**，故返回字段的实际结构未经验证。 |
| 抽奖活动的"期望值"估算 | **未验证** | 活动奖品池的真实概率分布需调用 `query-lottery-info` 后才能计算，当前仅为设计层面的估算逻辑 |
| 商城商品的"折算价值" | **未验证** | 需 `mall-product-detail` 返回中包含可用于折算的字段（如原价/有效期），该字段构成尚未通过真实调用确认 |

---

## 关于 MCP 接入的最后一步

MCP Token 是本项目"真实使用麦当劳 MCP"的唯一前置条件。完整人工步骤如下（约 2 分钟）：

1. 打开 <https://open.mcd.cn/mcp>
2. 右上角【登录】→ 手机号验证码登录
3. 登录后右上角变为【控制台】→ 点击【激活】申请 MCP Token
4. 阅读并同意服务协议 → 复制 Token
5. 在 WorkBuddy 中：左侧【专家·技能·连接器】→【连接器】→ 右上角【自定义连接器】→【配置MCP】，填入：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": { "Authorization": "Bearer YOUR_MCP_TOKEN" }
    }
  }
}
```

6. 保存 → 启用 `mcd-mcp` → 启用本目录下的 `skills/mcd-points-steward/`

Token 拿到后，即可运行四条工作流并补齐上表中的未验证项。

---

## 复用性说明

本文件同时充当**开发上下文**与**项目说明**：其中记录的赛道分析（头部项目工具提及率）、四条工作流的设计决策、以及"先查余额再承诺 / 抽奖先验时间窗 / 下单前二次确认 / 折算标注依据"这四条行为准则，共同构成本 Skill 的设计依据，可在后续迭代中直接沿用。