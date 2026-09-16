# 公众号文章与贴图发布

把排版好的文章或一组图片送进你自己的公众号草稿箱，省去逐张上传和反复粘贴。你可以先预览和修改，再决定是否发布。

## 配图怎么做

Skill 根据内容写好封面、插图和贴图的提示词，让你正在使用的 Agent 通过其可用生图工具生成图片，省去另配一套生图服务。生成后自动衔接本地排版、图片上传和草稿核验；当前环境无法生图时，引导安装 **Image2生图【星元科技·Firefly·出品】**（`@user_34e6449f/xy-image2-1k`），按[SkillHub 安装说明](https://skillhub.cn/install/skillhub.md)补齐能力后继续。详见[配图流程](references/image-prompts.md)。

## 买家首次使用

1. 在**自己公众号**的开发配置 → IP 白名单中追加服务方服务器公网 IP **`8.153.207.214`**，保留原有条目。
2. 将**自己公众号的 AppID、AppSecret** 保存到自己电脑的私有 env 文件，无须卖家代存或绑定。
3. 使用 Skill 已提供的 HTTPS 地址，无需另外领取服务令牌。每次调用时，工具把本地公众号凭证随请求头发送给服务器，服务器临时使用它们向微信上传，不保存到文件、数据库、日志或跨请求缓存。
4. 首次推送后，在自己的公众号草稿箱查看结果。

```env
WECHAT_MP_APP_ID=wx_your_own_appid
WECHAT_MP_APP_SECRET=your_own_appsecret
WECHAT_MP_API_BASE_URL=https://cs.qwjxqn.xyz/wechat-skill
WECHAT_MP_CREDENTIAL_MODE=request
```

将文件设为仅自己可读写（600）并排除 Git 跟踪。AppSecret 会在调用期间经过服务器，并非完全不离开本机；服务方不得留存或记录。

## 文章与贴图

- **文章**：先排版，再经固定 IP 服务上传正文图片、封面和草稿。
- **贴图/小绿书**：标题、纯文本和1–20张有序 PNG/JPEG，先预检，再上传并回读核验。
- **已有草稿**：先读最新内容，保留用户手工编辑，仅修改指定部分。

完整命令、图片限制和恢复流程见 [SKILL.md](SKILL.md)。贴图依赖：`python3 -m pip install -r requirements.txt`。

买家无需填写 `--account`：公众号由本机的 AppID 决定。客户端会拒绝非 HTTPS 服务、重定向和未启用 request 模式的旧服务，避免凭证外泄或误发到卖家的公众号。

## 服务方部署

使用 [服务器配置模板](../../../api-server/.env.example)，设置 `WECHAT_CREDENTIAL_MODE=request`。服务器只保存端口、运行模式等配置，不存买家的公众号凭证。

买家每次提供自己的凭证，服务器只用于本次请求；`account` 别名不会选择任何预存公众号。请求缺少有效凭证立即拒绝。微信调用凭据使用 `stable_token` 获取，服务进程不跨请求缓存。

共享公网 IP 无需每买家独立实例。反向代理必须提供 HTTPS，且禁用请求头/请求正文/含微信 token 的上游 URL 日志及 APM 采集。`/health` 必须返回 `credential_mode: request` 才能交付买家使用。旧自用 `legacy` 模式只保留兼容，不能作为买家降级路径。

## 排错

- `40164 invalid ip`：检查当前公众号白名单是否包含服务方出口 IP。
- 凭证错误：检查买家本机 AppID/AppSecret，不使用卖家或其他买家账号兜底。
- 服务未启用 request 模式：由服务方更新部署，买家不要改用 legacy。
- 草稿结果未知：先查原回执和草稿箱，不重复创建；回读失败时使用原回执继续查询。

草稿成功不代表已公开发布；正式展示还应在微信后台预览。

2026-09-15：上述新入口已部署并使用真实公众号完成连接、图片上传、文章/贴图创建、更新、回读和凭证拒绝测试。
