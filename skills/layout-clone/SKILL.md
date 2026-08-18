---
name: wechat-layout-clone
slug: wechat-layout-clone
displayName: 公众号排版复刻
version: 1.0.0
summary: 把公众号文章的排版风格整理成可复用主题，减少手工拆样式和反复调版。
description: 从微信公众号图文提取正文结构、内联样式和 HTML 样本，帮助运营者把喜欢的文章版式归纳成可复用的排版主题。
tags: ["wechat", "公众号", "排版", "内容运营"]
license: MIT
homepage: https://github.com/chenchen1010/wechat-mp-tools
---

# 公众号排版复刻（Layout Clone）

把任意微信公众号图文的**视觉特征**抽成结构化数据，再由 LLM **归纳成可复用的主题配置**（名称 + CSS/内联规则）。对应链路：**取文 → 定位 `#js_content` → 收集内联 `style` → AI 分析 → 写入你的排版工具**。

## 何时使用

用户给出 `mp.weixin.qq.com` 文章链接（或本地保存的图文 HTML），并说「复刻这篇排版」「学这个公众号样式」「抽主题」「layout clone」时使用。

## 前置条件

- Python 3.10+
- 建议使用本目录虚拟环境（避免系统 Python PEP 668 限制）：

在本 skill 目录运行：

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## 工作流程（与「一键复刻」文章描述对齐）

### Step 1：获取 HTML

1. **首选**：命令行抓取（伪装桌面 Chrome UA，多数情况下可拿到正文区域）。
2. **若返回验证/风控页**（`verification_or_risk_page: true`）：
   - 让用户在微信内打开文章 → **另存为完整网页**，再对脚本传入**本地 `.html` 路径**；或
   - 使用仓库内 **`wechat-article-for-ai`**（Camoufox，`--no-headless` 可过验证码）先导出 HTML，再跑本 skill 的提取脚本。

### Step 2：定位正文并抽取样式

运行提取脚本（对 URL 或本地文件均可）：

```bash
cd /path/to/wechat-layout-clone
# 已按上文创建并激活 .venv 后：
python3 scripts/extract_wechat_layout.py "https://mp.weixin.qq.com/s/xxxx" -o /tmp/layout-bundle.json

# 本地保存的图文 HTML（推荐在风控严重时）
python3 scripts/extract_wechat_layout.py "/path/to/article.html" -o /tmp/layout-bundle.json
```

脚本会输出 JSON，核心字段：

| 字段 | 含义 |
|------|------|
| `article_title` / `author` | 页面元信息 |
| `inline_style_samples` | 带 `style` 的节点样本（标签、归一化后的 style、class、文本预览） |
| `style_frequency_by_tag` | 按标签聚合的高频内联样式（便于 AI 归纳「H2/H3/引用/代码」） |
| `sample_html` | `#js_content` 截断 HTML，供对照结构 |
| `llm_task` | 给模型的固定任务说明（可直接贴进对话） |

### Step 3：AI 归纳主题

将 **`layout-bundle.json` 全文**（或 stdout）交给模型，要求其：

1. 生成主题 **id**（短英文小写）与 **中文名**；
2. 输出 **可落地** 的规则：正文、`h2`/`h3`、引用、代码、链接、强调 —— 以 **内联 style 或 CSS 变量表** 形式（需说明：公众号后台会过滤部分属性，与原文 100% 一致不保证）；
3. 若项目里有 `markdown-to-wechat` / 自有 HTML 模板，说明**应改哪个文件、哪几个选择器**。

### Step 4：一键应用（由你项目决定）

- 把模型生成的主题 **合并进** 现有排版工具的配置（例如主题 JSON、`<style>` 块、或 md2wechat 类工具的主题目录）。
- **不要**自动 `git commit`，除非用户明确要求；变更前应展示 diff 摘要。

## 微信发布兼容输出约束

当本 skill 的产物要进入微信公众号草稿箱时，排版层必须输出微信编辑器友好的 HTML：

- 不输出 `<pre>`、`<code>`、`code-snippet__*`。代码/公式/流程块改成普通灰底 `<section><p><span>` 文本块，用 `<br/>` 换行。
- 图片只输出干净图片块：`<section style="text-align:center;"><img class="rich_pages wxw-img" src="..." data-src="..." style="display:block;width:100%;height:auto !important;"/></section>`。
- 不给图片包叠层遮罩、错误占位、小程序链接容器、绝对定位标题、多层卡片容器。
- 如果只是复刻参考文里的代码块样式，也只能复刻视觉，不复刻微信代码块 DOM。
- 发布前的最终兜底和线上草稿修复属于 `wechat-article-publish` skill，但本 skill 应避免生成明显会触发兜底的结构。

## Agent 自检清单

- [ ] 若 `ok: false` 或 `verification_or_risk_page: true`，已提示「本地 HTML 或 Camoufox」路径，而不是反复空跑 curl。
- [ ] 已向用户说明：微信编辑器对 `style` / 标签有过滤，复刻是 **近似还原**，不是像素级镜像。
- [ ] 主题配置写入位置与命名符合用户现有工具（避免新建一堆无关文件）。
- [ ] 若产物用于公众号发布，已确认没有 `<pre>`、`<code>`、`code-snippet__*`，图片块没有复杂 wrapper。

## 与内置工具的关系

| 能力 | 本 skill | `wechat-article-for-ai` |
|------|----------|-------------------------|
| 抓文 | curl + UA（轻量） | 浏览器渲染（更强，可过部分验证） |
| 抽 `#js_content` 内联样式 | ✅ 专用脚本 | 可走 Markdown 管线，非「主题克隆」 |
| 产出 | **主题归纳用的 JSON** | **干净 Markdown + 图片** |

需要「全文迁移」用 **wechat-article-for-ai**；需要「学排版」用 **本 skill**。

## 限制

- 仅适用于 **图文** 页；视频号、纯卡片页可能无 `#js_content`。
- 部分文章样式在 **外链 CSS** 或微信私有类名上，仅靠内联 style 可能不完整，需在 Step 3 让模型结合 `sample_html` 推断。
- 请遵守版权与平台规则：复刻指**样式学习**，勿盗用他人商标与付费素材。
