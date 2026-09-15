# wechat-mp-tools

微信公众号工具集：排版复刻 + 文章与贴图草稿 + API 代理。

## 组件

### skills/publish/wechat-article

Markdown → 排版 → 微信草稿箱的完整发布流水线。

- 支持 Wenyan MCP 真实排版
- 共用服务方固定公网 IP：买家将 `8.153.207.214` 加入自己公众号的白名单；自己的 AppID/AppSecret 留在本机，每次调用携带
- 支持多公众号账号
- 支持贴图（小绿书）：按顺序上传图片、推送草稿、回读核对；详见 [发布说明](skills/publish/wechat-article/SKILL.md)

### skills/layout-clone

从任意公众号文章提取内联样式，AI 归纳为可复用的排版主题。

### api-server

部署在 ECS 上的微信 API 代理服务（Node.js），解决本地 IP 不在白名单的问题。

## 配置

```bash
cp .env.example .env
# 填入买家自己的AppID/AppSecret，以及服务方地址和访问凭证
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

买家配置与服务方部署要求见[使用说明](skills/publish/wechat-article/README.md)。买家模式使用每次携带的本地公众号凭证，不需要卖家预存或绑定公众号；服务器须启用 `WECHAT_CREDENTIAL_MODE=request`。
