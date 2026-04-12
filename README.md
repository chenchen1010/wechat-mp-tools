# wechat-mp-tools

微信公众号工具集：排版复刻 + 文章发布 + API 代理。

## 组件

### skills/publish/wechat-article

Markdown → 排版 → 微信草稿箱的完整发布流水线。

- 支持 Wenyan MCP 真实排版
- 支持 ECS 固定 IP 代理（绕过 IP 白名单）
- 支持多公众号账号

### skills/layout-clone

从任意公众号文章提取内联样式，AI 归纳为可复用的排版主题。

### api-server

部署在 ECS 上的微信 API 代理服务（Node.js），解决本地 IP 不在白名单的问题。

## 配置

```bash
cp .env.example .env
# 填入你的微信公众号 AppID / AppSecret
```

## 依赖

```bash
# 发布工具
npm install -g @wenyan-md/mcp mcporter

# 排版复刻
pip install beautifulsoup4

# API 代理
node api-server/server.mjs
```
