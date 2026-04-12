# Wenyan MCP 使用指南

## 简介

Wenyan (文颜) 是一款专业的 Markdown 排版工具，支持将 Markdown 一键转换并发布至微信公众号。

## 安装

```bash
npm install -g @wenyan-md/mcp
```

## 运行模式

### 1. stdio 模式（默认）
```bash
wenyan-mcp
```

### 2. SSE 模式（HTTP 服务）
```bash
wenyan-mcp --sse
```

## 环境变量

```bash
export WECHAT_APP_ID="your_app_id"
export WECHAT_APP_SECRET="your_app_secret"
```

## Markdown 格式

### FrontMatter
```markdown
---
title: 文章标题
cover: /path/to/cover.jpg
---
```

### 支持的语法
- 标准 Markdown
- 代码块高亮
- 数学公式
- 图片（本地或网络）

## 主题列表

- `default` - 默认主题
- `orangeheart` - 橙心主题
- `phycat` - 物理猫主题

## 更多信息

- GitHub: https://github.com/caol64/wenyan-mcp
- 官网: https://wenyan.yuzhi.tech
