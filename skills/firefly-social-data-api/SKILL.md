---
name: firefly-social-data-api
slug: firefly-social-data-api
displayName: Firefly 社媒数据助手【星元科技·Firefly·出品】
version: 1.0.3
summary: 一句话查询小红书、公众号、视频号和抖音，把内容、评论、账号和作品直接整理成选题库、达人库和竞品表。
description: 不用再在多个平台来回搜索和复制粘贴。告诉 Agent 你想查的平台、关键词或链接，它会找到相关内容，并按你的目标整理成可筛选、可复用的数据。
tags: ["firefly", "社媒数据", "小红书", "公众号", "视频号", "抖音", "api"]
license: MIT
homepage: https://firefly.qwjxqn.xyz/docs/agent-api
iconUrl: https://skillhub-1388575217.cos.accelerate.myqcloud.com/skill-icons/uploads/604962/daaa2df047ce4b029edcc9b4e7a08e9e.png
---

# Firefly 社媒数据助手【星元科技·Firefly·出品】

**一句话查四个平台，把零散内容直接变成能筛选、能复用的数据。**

做选题、看竞品、筛达人时，最耗时间的往往不是判断，而是在不同平台反复搜索、点开、复制和整理。这个 Skill 可以直接查询小红书、公众号、视频号和抖音，把内容、评论、账号和作品信息整理成表格、选题库、达人库或竞品观察表。

## 你可以直接这样说

- “帮我找小红书最近关于露营装备的热门笔记，整理标题、作者和互动数据。”
- “分析这篇公众号文章的内容和评论，提炼读者最关心的问题。”
- “查这个视频号账号最近发布了什么，整理成选题参考表。”
- “找抖音上做 AI 工具测评的账号，筛一份达人候选名单。”
- “把这些链接的详情统一整理成一张可筛选的竞品表。”

## 最适合这些工作

- **选题调研**：快速找到同类热门内容，减少逐个平台翻找。
- **竞品观察**：统一整理标题、作者、互动和发布时间，方便横向比较。
- **达人筛选**：查看账号资料和历史作品，建立可继续补充的候选库。
- **评论洞察**：把用户反馈归纳成需求、疑问、槽点和购买信号。
- **内容资料库**：把零散链接和搜索结果沉淀成表格或 JSON，方便团队复用。

## 为什么更省事

| 原来的做法               | 使用这个 Skill                   |
| ------------------------ | -------------------------------- |
| 在多个平台来回切换和搜索 | 在一次对话里说明平台和目标       |
| 逐条点开、复制、粘贴     | 自动查询并提取关键内容           |
| 临时记录，过后很难复用   | 直接整理成表格、选题库或达人库   |
| 不清楚每次查询花了多少   | 成功查询后显示本次积分和剩余余额 |

## 三步开始使用

1. 在 [Firefly](https://firefly.qwjxqn.xyz) 注册账号，并在后台创建自己的 API Key。
2. 把 Key 保存到运行环境的 `FIREFLY_API_KEY`，只需配置一次。
3. 告诉 Agent 你想查的平台、关键词、链接或账号，以及希望整理成什么结果。

## 费用说明

- Skill 免费安装。
- 查询使用用户自己的 Firefly 余额，仅成功返回数据时扣积分。
- 不同查询消耗不同积分；Agent 应优先选择能直接完成任务的最小能力，避免重复查询。
- 每次完成后都应告诉用户本次扣除积分和剩余余额。

## 使用边界

- 数据可见性会受到平台状态、内容权限和上游稳定性影响，不承诺 100% 实时或完整覆盖。
- 不支持绕过登录、权限、验证码或平台访问限制。
- 不用于大规模骚扰、垃圾营销或违反目标平台规则的采集。
- 生图、图片编辑和图片托管不属于本 Skill，应使用独立的 Firefly 图片能力。

---

## Agent 执行指南

### 何时触发

用户提出以下需求时使用本 Skill：

- 查询小红书笔记、评论、账号资料或账号作品。
- 查询公众号文章详情、评论、账号资料或账号文章列表。
- 查询视频号视频、评论、账号资料或账号作品。
- 根据视频号作品 ID 生成可点击的微信分享链接。
- 查询抖音视频、评论、账号资料或账号作品。
- 把社媒结果整理成表格、JSON、竞品分析、达人名单、选题库或运营线索。

### 与用户沟通

| 内部概念        | 对用户的说法               | 用户得到的结果         |
| --------------- | -------------------------- | ---------------------- |
| REST / MCP API  | Agent 可以直接查询社媒内容 | 少复制粘贴，多自动整理 |
| Firefly API Key | 用户自己的查询账户         | 余额和使用记录统一管理 |
| Credits         | 每次成功查询消耗的积分     | 用多少付多少，成本可见 |
| Request ID      | 本次任务的查询编号         | 重试时避免重复扣费     |

### 鉴权与调用入口

优先从环境变量读取用户自己的 Firefly API Key：

```bash
export FIREFLY_API_KEY="ff_..."
```

也可以使用 Bearer 鉴权。不要把用户的 Firefly API Key 写入 skill 文件、日志、仓库、对话最终回复或公开文档。

- REST: `https://firefly.qwjxqn.xyz/v1/{platform}/{capability}`
- MCP: `https://firefly.qwjxqn.xyz/v1/mcp` 或 `https://firefly.qwjxqn.xyz/v1/mcp/{platform}`
- 鉴权: `X-API-Key: <Firefly API Key>` 或 `Authorization: Bearer <Firefly API Key>`
- 幂等: 传 `X-Request-Id`，或在 MCP 参数中传 `request_id`

成功请求的正文包含任务编号和数据；扣费信息优先从响应头读取：

```json
{
  "code": 0,
  "request_id": "agent-request-id",
  "data": {}
}
```

```text
X-Firefly-Credits-Charged: 2
X-Firefly-Balance: 98
```

部分能力也会在正文返回扣费字段。若响应头和正文同时存在，以响应头为准。

### 能力选择

| 任务               | REST 路径                             | 方法 | 积分/次 | MCP 工具                          |
| ------------------ | ------------------------------------- | ---- | ------- | --------------------------------- |
| 小红书笔记搜索     | `/v1/xhs/note_search`                 | GET  | 13      | `xhs_note_search`                 |
| 小红书笔记详情     | `/v1/xhs/note_detail`                 | GET  | 10      | `xhs_note_detail`                 |
| 小红书笔记评论     | `/v1/xhs/note_comments`               | GET  | 13      | `xhs_note_comments`               |
| 小红书账号信息     | `/v1/xhs/user_info`                   | GET  | 13      | `xhs_user_info`                   |
| 小红书账号作品     | `/v1/xhs/user_notes`                  | GET  | 13      | `xhs_user_notes`                  |
| 公众号文章详情     | `/v1/wechat_mp/article_detail`        | POST | 10      | `wechat_mp_article_detail`        |
| 公众号文章评论     | `/v1/wechat_mp/article_comments`      | POST | 13      | `wechat_mp_article_comments`      |
| 公众号账号信息     | `/v1/wechat_mp/account_profile`       | POST | 13      | `wechat_mp_account_profile`       |
| 公众号账号文章     | `/v1/wechat_mp/account_articles`      | POST | 13      | `wechat_mp_account_articles`      |
| 视频号视频搜索     | `/v1/wechat_channels/video_search`    | POST | 13      | `wechat_channels_video_search`    |
| 视频号视频详情     | `/v1/wechat_channels/video_detail`    | POST | 10      | `wechat_channels_video_detail`    |
| 视频号视频评论     | `/v1/wechat_channels/video_comments`  | POST | 13      | `wechat_channels_video_comments`  |
| 视频号作品分享链接 | `/v1/wechat_channels/video_share_url` | POST | 13      | `wechat_channels_video_share_url` |
| 视频号账号信息     | `/v1/wechat_channels/user_profile`    | POST | 13      | `wechat_channels_user_profile`    |
| 视频号账号作品     | `/v1/wechat_channels/user_videos`     | POST | 13      | `wechat_channels_user_videos`     |
| 抖音视频搜索       | `/v1/douyin/video_search`             | POST | 13      | `douyin_video_search`             |
| 抖音视频详情       | `/v1/douyin/video_detail`             | GET  | 10      | `douyin_video_detail`             |
| 抖音视频评论       | `/v1/douyin/video_comments`           | GET  | 2       | `douyin_video_comments`           |
| 抖音账号信息       | `/v1/douyin/user_info`                | GET  | 2       | `douyin_user_info`                |
| 抖音账号作品       | `/v1/douyin/user_videos`              | GET  | 2       | `douyin_user_videos`              |

### 执行流程

1. 明确用户要查的平台和目标：搜索、详情、评论、账号信息或账号作品。
2. 判断最小可用输入：关键词、内容链接、内容 ID、账号 ID、分页参数等。缺关键参数时只问必要问题。
3. 选择上表中最匹配的能力。能用详情接口解决时，不要先搜索再详情，避免多扣积分。
4. 生成稳定 `request_id`，建议包含任务名、平台、目标 ID 和时间戳。
5. 调用 Firefly API。GET 请求把参数放在 query string；POST 请求发送 JSON body。
6. 检查响应：`code === 0` 才使用 `data`；从 `X-Firefly-Credits-Charged` 和 `X-Firefly-Balance` 读取本次扣费与剩余余额。
7. 按用户目标整理结果，而不是原样倾倒 JSON。默认输出“关键字段 + 可复制表格 + 原始 JSON 保存位置或片段”。

### 视频号可点击链接流程

当用户要求“拉某个视频号博主的作品链接”时，账号作品列表本身只保证返回作品 ID、媒体字段和分页信息，不等同于微信可点击分享短链。需要按下面的最小链路执行：

1. 用户给单条视频号分享链接时，先调用 `wechat_channels_video_detail`，从作品详情里定位博主 `username`。
2. 调用 `wechat_channels_user_videos` 拉该博主作品列表，记录每条作品的 `id` 或 `object_id`。
3. 若用户需要可点击的 `https://weixin.qq.com/sph/...` 链接，再对需要导出的每条作品调用 `wechat_channels_video_share_url`。
4. 汇总时明确说明本次总积分：详情 10 积分 + 账号作品 13 积分 + 每条分享链接 13 积分。

### REST 示例

抖音评论查询：

```bash
curl "https://firefly.qwjxqn.xyz/v1/douyin/video_comments?aweme_id=AWEME_ID" \
  -H "X-API-Key: $FIREFLY_API_KEY" \
  -H "X-Request-Id: demo-001"
```

公众号文章详情：

```bash
curl -X POST "https://firefly.qwjxqn.xyz/v1/wechat_mp/article_detail" \
  -H "X-API-Key: $FIREFLY_API_KEY" \
  -H "X-Request-Id: mp-article-001" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://mp.weixin.qq.com/s/xxxx"}'
```

小红书笔记搜索：

```bash
curl "https://firefly.qwjxqn.xyz/v1/xhs/note_search?keyword=%E9%9C%B2%E8%90%A5&page=1" \
  -H "X-API-Key: $FIREFLY_API_KEY" \
  -H "X-Request-Id: xhs-search-camping-001"
```

视频号作品分享链接：

```bash
curl -X POST "https://firefly.qwjxqn.xyz/v1/wechat_channels/video_share_url" \
  -H "X-API-Key: $FIREFLY_API_KEY" \
  -H "X-Request-Id: channels-share-url-001" \
  -H "Content-Type: application/json" \
  -d '{"object_id":"14990093036440061965"}'
```

### 输出格式

面向运营和团队交付时，优先整理为表格：

| 字段                    | 说明               |
| ----------------------- | ------------------ |
| 标题/内容摘要           | 便于快速判断价值   |
| 作者/账号               | 便于追踪来源       |
| 链接/ID                 | 便于复查和再次查询 |
| 点赞/评论/收藏/发布时间 | 便于排序和筛选     |
| 采集时间/request_id     | 便于审计和复跑     |

默认提醒用户：

- 本次成功查询扣除多少积分。
- 当前剩余余额是多少。
- 哪些字段来自平台公开可查询数据。
- 如遇上游暂不可用，建议稍后用相同 `request_id` 或新 `request_id` 重试。

### 错误处理

| HTTP | code | 处理                                                          |
| ---- | ---- | ------------------------------------------------------------- |
| 400  | 1001 | 参数错误。检查必填参数、ID、链接格式和分页参数。              |
| 401  | 1401 | API Key 无效。让用户重新在 Firefly 控制台创建或确认环境变量。 |
| 402  | 1402 | 积分不足。提示用户充值或换用有余额的 key。                    |
| 404  | 1404 | 能力不存在。检查路径、平台名和能力名。                        |
| 429  | 1429 | 请求过于频繁。降低并发，稍后重试。                            |
| 404  | 2404 | 内容不存在或未收录。让用户确认链接/ID 是否有效。              |
| 502  | 1502 | 上游数据源暂不可用。稍后重试，保留 request_id。               |
| 503  | 1503 | 服务繁忙。稍后重试。                                          |
| 504  | 1504 | 上游超时。减少范围或稍后重试。                                |

### 安全与合规

- 不要替用户保存、传播或展示完整 Firefly API Key。
- 不要把一次查询结果扩大成未授权的大规模采集。
- 不要承诺 100% 实时或 100% 覆盖；社媒数据会受平台状态、内容可见性和上游稳定性影响。
- 用户要求批量任务时，先确认范围、频率、用途和预算，再执行。
- 失败返回不应伪造成空结果；必须说明错误码、可重试性和下一步。

### 参考

- Firefly 社媒数据 API 文档: https://firefly.qwjxqn.xyz/docs/agent-api
- 小红书 API: https://firefly.qwjxqn.xyz/docs/agent-api/xiaohongshu
- 微信公众号 API: https://firefly.qwjxqn.xyz/docs/agent-api/wechat-mp
- 微信视频号 API: https://firefly.qwjxqn.xyz/docs/agent-api/wechat-channels
- 抖音 API: https://firefly.qwjxqn.xyz/docs/agent-api/douyin
