---
name: firefly-social-data-api
slug: firefly-social-data-api
displayName: Firefly 社媒数据 API
version: 1.0.0
summary: 让 Agent 直接查询小红书、公众号、视频号和抖音内容，把搜索、详情、评论、账号和作品结果整理成可复用数据。
description: 面向内容运营、选题分析、达人筛选和自动化团队的 Firefly 社媒数据 API 调用指南，帮助 Agent 选择正确能力、构造请求、处理积分扣费和错误返回。
tags: ["firefly", "社媒数据", "小红书", "公众号", "视频号", "抖音", "api"]
license: MIT
homepage: https://firefly.qwjxqn.xyz/docs/agent-api
---

# Firefly 社媒数据 API

把社媒内容变成可直接使用的数据表：输入关键词、链接、内容 ID 或账号信息，按需查询小红书、微信公众号、微信视频号和抖音的搜索、详情、评论、账号与作品数据。

## 何时使用

当用户想要完成这些任务时使用本 skill：

- 查询小红书笔记、评论、账号资料或账号作品。
- 采集微信公众号文章详情、评论、账号资料或账号文章列表。
- 查询微信视频号视频、评论、账号资料或账号作品。
- 查询抖音视频、评论、账号资料或账号作品。
- 把社媒数据整理成表格、JSON、竞品分析、达人名单、选题库或运营线索。

不要把本 skill 用于：

- 绕过平台权限、登录态或访问限制。
- 大规模抓取、骚扰、垃圾营销或违反目标平台规则的任务。
- 生图、图像编辑或图片托管。生图应使用独立的 Firefly 生图 skill。

## 业务定位

对用户解释时，不要主打“接口调用”。应表达为：

> 用一个 Firefly Key，把多个社媒平台的搜索、详情、评论和账号数据接进 Agent 工作流。查询结果可直接整理成表格、选题库、达人库或竞品观察表。

| 内部概念 | 用户能理解的说法 | 业务结果 |
| --- | --- | --- |
| REST / MCP API | Agent 可以直接查询社媒数据 | 少复制粘贴，多自动整理 |
| Firefly API Key | 用户自己的查询额度和消费账本 | 团队可统一管理余额和使用记录 |
| credits_charged | 本次成功查询扣除的积分 | 成本透明，便于控制预算 |
| request_id | 同一任务的幂等编号 | 重试不重复扣费 |

## 前置条件

用户需要自己的 Firefly API Key。优先从环境变量读取：

```bash
export FIREFLY_API_KEY="ff_..."
```

也可以使用 Bearer 鉴权。不要把用户的 Firefly API Key 写入 skill 文件、日志、仓库、对话最终回复或公开文档。

## 调用入口

- REST: `https://firefly.qwjxqn.xyz/v1/{platform}/{capability}`
- MCP: `https://firefly.qwjxqn.xyz/v1/mcp` 或 `https://firefly.qwjxqn.xyz/v1/mcp/{platform}`
- 鉴权: `X-API-Key: <Firefly API Key>` 或 `Authorization: Bearer <Firefly API Key>`
- 幂等: 传 `X-Request-Id`，或在 MCP 参数中传 `request_id`

REST 返回统一 Firefly 信封：

```json
{
  "code": 0,
  "msg": "success",
  "request_id": "agent-request-id",
  "credits_charged": 2,
  "balance": 98,
  "data": {}
}
```

## 能力选择

| 任务 | REST 路径 | 方法 | 积分/次 | MCP 工具 |
| --- | --- | --- | --- | --- |
| 小红书笔记搜索 | `/v1/xhs/note_search` | GET | 13 | `xhs_note_search` |
| 小红书笔记详情 | `/v1/xhs/note_detail` | GET | 10 | `xhs_note_detail` |
| 小红书笔记评论 | `/v1/xhs/note_comments` | GET | 13 | `xhs_note_comments` |
| 小红书账号信息 | `/v1/xhs/user_info` | GET | 13 | `xhs_user_info` |
| 小红书账号作品 | `/v1/xhs/user_notes` | GET | 13 | `xhs_user_notes` |
| 公众号文章详情 | `/v1/wechat_mp/article_detail` | POST | 10 | `wechat_mp_article_detail` |
| 公众号文章评论 | `/v1/wechat_mp/article_comments` | POST | 13 | `wechat_mp_article_comments` |
| 公众号账号信息 | `/v1/wechat_mp/account_profile` | POST | 13 | `wechat_mp_account_profile` |
| 公众号账号文章 | `/v1/wechat_mp/account_articles` | POST | 13 | `wechat_mp_account_articles` |
| 视频号视频搜索 | `/v1/wechat_channels/video_search` | POST | 13 | `wechat_channels_video_search` |
| 视频号视频详情 | `/v1/wechat_channels/video_detail` | POST | 10 | `wechat_channels_video_detail` |
| 视频号视频评论 | `/v1/wechat_channels/video_comments` | POST | 13 | `wechat_channels_video_comments` |
| 视频号账号信息 | `/v1/wechat_channels/user_profile` | POST | 13 | `wechat_channels_user_profile` |
| 视频号账号作品 | `/v1/wechat_channels/user_videos` | POST | 13 | `wechat_channels_user_videos` |
| 抖音视频搜索 | `/v1/douyin/video_search` | POST | 13 | `douyin_video_search` |
| 抖音视频详情 | `/v1/douyin/video_detail` | GET | 10 | `douyin_video_detail` |
| 抖音视频评论 | `/v1/douyin/video_comments` | GET | 2 | `douyin_video_comments` |
| 抖音账号信息 | `/v1/douyin/user_info` | GET | 2 | `douyin_user_info` |
| 抖音账号作品 | `/v1/douyin/user_videos` | GET | 2 | `douyin_user_videos` |

## 执行流程

1. 明确用户要查的平台和目标：搜索、详情、评论、账号信息或账号作品。
2. 判断最小可用输入：关键词、内容链接、内容 ID、账号 ID、分页参数等。缺关键参数时只问必要问题。
3. 选择上表中最匹配的能力。能用详情接口解决时，不要先搜索再详情，避免多扣积分。
4. 生成稳定 `request_id`，建议包含任务名、平台、目标 ID 和时间戳。
5. 调用 Firefly API。GET 请求把参数放在 query string；POST 请求发送 JSON body。
6. 检查返回信封：`code === 0` 才使用 `data`；同时向用户说明 `credits_charged` 和 `balance`。
7. 按用户目标整理结果，而不是原样倾倒 JSON。默认输出“关键字段 + 可复制表格 + 原始 JSON 保存位置或片段”。

## REST 示例

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

## 输出格式

面向运营和团队交付时，优先整理为表格：

| 字段 | 说明 |
| --- | --- |
| 标题/内容摘要 | 便于快速判断价值 |
| 作者/账号 | 便于追踪来源 |
| 链接/ID | 便于复查和再次查询 |
| 点赞/评论/收藏/发布时间 | 便于排序和筛选 |
| 采集时间/request_id | 便于审计和复跑 |

默认提醒用户：

- 本次成功查询扣除多少积分。
- 当前剩余余额是多少。
- 哪些字段来自平台公开可查询数据。
- 如遇上游暂不可用，建议稍后用相同 `request_id` 或新 `request_id` 重试。

## 错误处理

| HTTP | code | 处理 |
| --- | --- | --- |
| 400 | 1001 | 参数错误。检查必填参数、ID、链接格式和分页参数。 |
| 401 | 1401 | API Key 无效。让用户重新在 Firefly 控制台创建或确认环境变量。 |
| 402 | 1402 | 积分不足。提示用户充值或换用有余额的 key。 |
| 404 | 1404 | 能力不存在。检查路径、平台名和能力名。 |
| 429 | 1429 | 请求过于频繁。降低并发，稍后重试。 |
| 404 | 2404 | 内容不存在或未收录。让用户确认链接/ID 是否有效。 |
| 502 | 1502 | 上游数据源暂不可用。稍后重试，保留 request_id。 |
| 503 | 1503 | 服务繁忙。稍后重试。 |
| 504 | 1504 | 上游超时。减少范围或稍后重试。 |

## 安全与合规

- 不要替用户保存、传播或展示完整 Firefly API Key。
- 不要把一次查询结果扩大成未授权的大规模采集。
- 不要承诺 100% 实时或 100% 覆盖；社媒数据会受平台状态、内容可见性和上游稳定性影响。
- 用户要求批量任务时，先确认范围、频率、用途和预算，再执行。
- 失败返回不应伪造成空结果；必须说明错误码、可重试性和下一步。

## 参考

- Firefly 社媒数据 API 文档: https://firefly.qwjxqn.xyz/docs/agent-api
- 小红书 API: https://firefly.qwjxqn.xyz/docs/agent-api/xiaohongshu
- 微信公众号 API: https://firefly.qwjxqn.xyz/docs/agent-api/wechat-mp
- 微信视频号 API: https://firefly.qwjxqn.xyz/docs/agent-api/wechat-channels
- 抖音 API: https://firefly.qwjxqn.xyz/docs/agent-api/douyin
