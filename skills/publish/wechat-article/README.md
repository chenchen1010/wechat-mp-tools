# 公众号文章与贴图发布

把文章或按顺序整理的图片送入公众号草稿箱，省去逐张上传和反复粘贴。文章使用 Wenyan 排版；贴图可直接使用本目录的发布脚本。

> 公众号与视频号是微信生态下的两个独立产品。公众号发布文章，视频号发布短视频。

Codex skill 入口见同目录 `SKILL.md`。如果把本目录安装为 skill，本地 skill 名称应为 `wechat-article-publish`。

## 首次配置公众号

如果是新公众号，先到微信公众号后台：

1. 进入 `设置与开发` -> `基本配置`
2. 获取 `开发者ID(AppID)` 和 `开发者密码(AppSecret)`
3. 把 ECS 固定公网 IP 加入 `IP 白名单`：
   - `8.153.207.214`

AppID/AppSecret 只能放在私有环境变量或服务器 `.env`，不要写进项目文档、文章草稿、日志或 skill 文件。遇到 `40164 invalid ip`，优先确认上面的 IP 白名单，然后通过 ECS 代理重试，不要继续用本机直连。

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

当 `WECHAT_MP_API_BASE_URL / WECHAT_MP_API_TOKEN` 都存在时，优先走 ECS 上的公众号 API（固定 IP）：

- `/wechat/media/uploadimg`：正文图片，返回微信 CDN URL
- `/wechat/material/add_material`：封面/永久图片素材
- `/wechat/draft/add`：创建草稿
- `/wechat/draft/update`：更新草稿
- `/wechat/draft/get`：读取草稿并校验

这样可以把 IP 白名单尽量稳定在服务器上，而不是依赖本机出口 IP。

不要默认假设 ECS 已支持 `/wechat/freepublish/submit`。如果官方 `freepublish/submit` 返回 `48001 api unauthorized`，说明账号没有 API 群发权限，应保留在草稿箱，由用户在公众号后台确认发布。

## 关于仓库内的 `publish.py`

`publish.py --type newspic` 支持贴图草稿：上传前校验、逐图上传、保存回执、回读核验。需要 `python3 -m pip install -r requirements.txt`。完整命令和失败恢复见同目录 `SKILL.md` 的“贴图 / 小绿书草稿”一节。

文章模式默认 `--type news -m article.md`，保留简易 Markdown 兜底；正式文章排版仍优先 Wenyan。脚本不会自动公开发布或群发。

## 推荐流程

1. 准备 Markdown（含 frontmatter）
2. 准备封面与文内配图（本地路径或 URL）
3. 通过 Wenyan MCP 选择主题并发布到微信公众号草稿箱
4. 记录返回的 `media_id`，用于后续追踪

## HTML 兜底写法（手工发布 / API 回填时）

如果不是走 Wenyan，而是自己拼 HTML 再写入草稿箱，文内图片默认用**纯图片块**：

```html
<section style="text-align:center;"><img class="rich_pages wxw-img" src="https://mmbiz.qpic.cn/..." data-src="https://mmbiz.qpic.cn/..." style="display:block;width:100%;height:auto !important;"/></section>
```

注意：
- 图片 `src` 必须先换成微信 CDN 地址
- 默认**不要**给每张图加“示意图 / 配图说明” caption，除非用户明确要求
- 避免叠层遮罩、绝对定位标题、多层卡片容器；这些结构在微信草稿编辑器里容易被改写，导致图片显示异常
- 不要输出 `<pre>`、`<code>` 或 `code-snippet__*`。代码/公式/流程块要转为普通灰底 `<section><p><span>`，用 `<br/>` 换行，否则移动端编辑器可能显示“暂不支持完整展示代码”。

## 只重传一张正文图

用户已经手工改过草稿、只要求修一张坏图时：

1. 先调用 `/wechat/draft/get` 读取线上最新草稿内容，不要用本地旧 HTML 覆盖用户手工修改。
2. 只通过 `/wechat/media/uploadimg` 上传目标图片。
3. 只替换目标图片区域。
4. 保留 `draft/get` 返回的 `title`、`author`、`digest`、`content_source_url`、`show_cover_pic`、`need_open_comment`、`only_fans_can_comment`。
5. 如果 `thumb_media_id` 为空但 `thumb_url` 存在，要先把当前封面重新上传为永久素材，否则 `/wechat/draft/update` 可能返回 `40007 invalid media_id`。

## 图片错误容器修复

微信可能把失败图片保存成错误容器，而不是普通 `<img>`：

```html
<section class="img_wrapper js_img_error js_all_error img_fail_mask">
  上传失败，网络异常。
  重试
</section>
```

修复时要替换整个外层错误块，而不是只替换 `src`。更新后必须再次 `/wechat/draft/get` 校验：

- 没有 `img_wrapper js_img_error`
- 没有 `上传失败`
- 没有 `网络异常`
- 图片数量符合预期
- 重传图片 URL 是 `mmbiz.qpic.cn` 域名

## 参考文档

- `references/wenyan-guide.md` — Wenyan 使用指南
- `references/api-guide.md` — 微信公众号 API 参考

## 排错

- **AccessToken 获取失败** — 检查 AppID/AppSecret，确认 IP 白名单
- **Wenyan 调用失败** — 先验证：`mcporter list --stdio "npx -y @wenyan-md/mcp" --schema`
- **草稿上传失败** — 检查公众号账号权限、封面/图片路径是否可访问
