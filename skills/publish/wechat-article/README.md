# 公众号发布

完整的公众号文章发布流水线：Markdown → Wenyan 真实排版 → 微信草稿箱。

> 公众号与视频号是微信生态下的两个独立产品。公众号发布文章，视频号发布短视频。

## 生产环境推荐用法

优先通过 **Wenyan MCP + mcporter** 直接走真实排版/上传链路：

```bash
mcporter call \
  --stdio "npx -y @wenyan-md/mcp" \
  --env WECHAT_APP_ID="$WECHAT_APP_ID" \
  --env WECHAT_APP_SECRET="$WECHAT_APP_SECRET" \
  publish_article \
  --args '{"file":"/path/to/article.md","theme_id":"default"}'
```

Markdown 顶部建议包含 frontmatter：

```markdown
---
title: 文章标题
author: 作者名
cover: /absolute/path/to/cover.png
---
```

文内图片可直接使用本地绝对路径或网络图片 URL，Wenyan 会在发布时自动按公众号要求上传。

## 前置依赖

```bash
npm install -g @wenyan-md/mcp
npm install -g mcporter
```

## 配置

在 `content-matrix/.env` 中配置：

```env
WECHAT_APP_ID=wx...
WECHAT_APP_SECRET=...
WECHAT_APP_ID_QWJXQN=wx...           # 可选：千万间新青年
WECHAT_APP_SECRET_QWJXQN=...
WECHAT_APP_ID_JSCXBWD=wx...          # 可选：精神持续不稳定
WECHAT_APP_SECRET_JSCXBWD=...
EVOLINK_API_KEY=...                  # 生图时可选

# 可选：优先走固定 IP 的 ECS 发布 API
WECHAT_MP_API_PREFER=1
WECHAT_MP_API_BASE_URL=https://cs.qwjxqn.xyz/wechat-mp
WECHAT_MP_API_TOKEN=...
WECHAT_MP_API_ACCOUNT_DEFAULT=default
WECHAT_MP_API_ACCOUNT_QWJXQN=qwjxqn
WECHAT_MP_API_ACCOUNT_JSCXBWD=jscxbwd
```

当 `WECHAT_MP_API_PREFER=1` 且 `WECHAT_MP_API_BASE_URL / WECHAT_MP_API_TOKEN` 都存在时，当前发布脚本会：

1. **优先**调用 ECS 上的公众号发布 API（固定 IP）
2. 如果 ECS API 未配置、鉴权失败、命中 `40164 invalid ip`，或账号映射不到，再**回落**到本机直连微信接口

这样可以把 IP 白名单尽量稳定在服务器上，而不是依赖本机出口 IP。

## 关于仓库内的 `publish.py`

`publish.py` 目前仍保留作实验/参考脚本，但其中 `render_with_wenyan()` 仍是**模拟渲染**，不是生产级 Wenyan 调用。

**因此：默认不要把 `publish.py` 当成正式发布链路。**

如果要真实排版并入草稿箱，优先使用上面的 `mcporter + wenyan-mcp` 方式。

## 推荐流程

1. 准备 Markdown（含 frontmatter）
2. 准备封面与文内配图（本地路径或 URL）
3. 通过 Wenyan MCP 选择主题并发布到微信公众号草稿箱
4. 记录返回的 `media_id`，用于后续追踪

## HTML 兜底写法（手工发布 / API 回填时）

如果不是走 Wenyan，而是自己拼 HTML 再写入草稿箱，文内图片默认用**纯图片块**：

```html
<section style="margin: 0 0 24px; padding: 0;">
  <img src="https://mmbiz.qpic.cn/..." style="display: block; width: 100%; margin: 0; border-radius: 4px;"/>
</section>
```

注意：
- 图片 `src` 必须先换成微信 CDN 地址
- 默认**不要**给每张图加“示意图 / 配图说明” caption，除非用户明确要求
- 避免叠层遮罩、绝对定位标题、多层卡片容器；这些结构在微信草稿编辑器里容易被改写，导致图片显示异常

## 参考文档

- `references/wenyan-guide.md` — Wenyan 使用指南
- `references/api-guide.md` — 微信公众号 API 参考

## 排错

- **AccessToken 获取失败** — 检查 AppID/AppSecret，确认 IP 白名单
- **Wenyan 调用失败** — 先验证：`mcporter list --stdio "npx -y @wenyan-md/mcp" --schema`
- **草稿上传失败** — 检查公众号账号权限、封面/图片路径是否可访问
