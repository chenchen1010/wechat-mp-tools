---
name: wechat-article-publish
slug: wechat-article-publish
displayName: 微信公众号文章与贴图发布
version: 1.2.0
summary: 把文章或多张贴图送入公众号草稿箱，自动上传图片并核对结果，减少逐张上传和手工整理。
description: 适用于微信公众号文章或贴图（newspic、小绿书）草稿发布、多图上传、草稿回读核验、正文图片重传和编辑器兼容性修复。
tags: ["wechat", "公众号", "文章发布", "内容运营"]
license: MIT
homepage: https://github.com/chenchen1010/wechat-mp-tools
---

# 微信公众号文章与贴图发布

面向购买本 Skill 的公众号运营者：在本机准备文章、排版和图片，通过服务方提供的固定公网 IP 推送到**买家自己的公众号草稿箱**，减少反复上传和更换电脑后的白名单配置。

## 买家首次使用：本地配置自己的公众号

1. 引导买家登录自己的公众号后台，在开发配置的 `IP 白名单` 中追加服务方公网 IP **`8.153.207.214`**。保留原有白名单，不填买家电脑的 IP，不填网址或端口。服务方变更出口时同步更新此指南。
2. 买家使用**自己公众号的 AppID 和 AppSecret**。将其保存到买家本机、已被 Git 忽略的私有 env，权限设为600；不要放进 Skill 包、文档、日志或最终回复。没有配置时引导买家在自己电脑上填写，不让他们发送给卖家人工保存。
3. 本地配置：
   - `WECHAT_MP_APP_ID`、`WECHAT_MP_APP_SECRET`：买家自己的公众号凭证。
   - `WECHAT_MP_API_BASE_URL`：服务方提供的 HTTPS 服务地址。
   - `WECHAT_MP_API_TOKEN`：访问该服务的凭证，与公众号 AppSecret 是两回事；按服务方交付配置。
   - `WECHAT_MP_CREDENTIAL_MODE=request`：每次请求携带本地公众号凭证，是买家模式默认值。
4. 明确告知买家：每次调用时，凭证会经 HTTPS 临时交给服务器，用于从固定公网 IP 请求微信；服务器不将它们写入文件、数据库、日志或跨请求缓存。不需要卖家预存、人工绑定公众号，也不依赖 `default` 等服务端账号别名。
5. 每次请求以 `X-Wechat-Appid`、`X-Wechat-Appsecret` 请求头携带本地凭证，不放进 URL。服务端只使用当前请求凭证，缺失或错误就失败，不回退到开发者或其他买家的账号。不要记录请求头或完整上游错误。
6. 客户端先检查 `/health` 返回 `credential_mode: request`，才携带凭证调用。旧服务未启用该模式时停止并告知服务方需更新，不能临时切到 `legacy` 继续买家发布。
7. 初次检查 `/token/test` 后，按买家授权推送测试草稿并回读核验；买家在自己的公众号后台查看。遇到 `40164 invalid ip`，核对当前公众号白名单是否包含服务方出口 IP，不改成本机直连。

## 文章和贴图共用的发布路径

- 文章先完成本地排版，图片和草稿统一通过固定 IP 代理；本机直连微信的 Wenyan `publish_article` 不属于此方案。
- `/wechat/media/uploadimg`：上传文章正文图片。
- `/wechat/material/add_material`：上传封面和贴图永久图片；买家模式传本地文件字节，不让服务器下载任意图片 URL。
- `/wechat/draft/add`、`/wechat/draft/update`、`/wechat/draft/get`：创建、更新、回读草稿。每次都携带本地公众号凭证。
- 公众号由 AppID 决定。不要询问买家 `default` 对应哪个公众号，不使用卖家的个人 env，不要求卖家代存买家 AppSecret。
- 默认只送入草稿箱，不能将草稿成功说成公开发布或群发成功。

## 服务方运行要求

- 服务器设置 `WECHAT_CREDENTIAL_MODE=request`，仅配置服务访问令牌、端口等运行参数；不配置买家的 AppID/AppSecret。
- 该模式通过微信 `stable_token` 使用本次凭证获取调用凭据，不在本服务跨请求缓存公众号凭证或 access_token。请求结束后不保留应用级引用；这不是“服务器完全接触不到凭证”。
- HTTPS 入口、反向代理、监控/APM 都不得记录公众号凭证头、请求正文或含 token 的上游 URL；不要开启包含这些内容的调试抓包或请求日志。
- 旧自用服务兼容模式 `legacy` 保留原逻辑，仅供已有部署过渡；买家入口必须运行 `request` 模式，不能暴露旧账号路由作为降级方案。
- 当前源码和本地测试支持 request 模式；是否已部署须查看实际 `/health`，不能把本地完成说成线上已启用。购买权益验证与计费不是本次公众号凭证转发的实现范围。

## Before Creating Or Updating Drafts

Always sanitize HTML for the WeChat editor:

- Do not send `<pre>`, `<code>`, or `code-snippet__*` blocks. The mobile editor may render them as “暂不支持完整展示代码”.
- Convert code-like blocks into plain HTML:
  - outer `<section style="background:#f7f7f7; border:1px solid #eeeeee; padding:13px 14px;">`
  - inner `<p>` plus `<span>` lines separated by `<br/>`
- Keep images as plain image blocks:
  - `<section style="text-align:center;"><img class="rich_pages wxw-img" src="..." data-src="..." style="display:block;width:100%;height:auto !important;"/></section>`
- Avoid overlay wrappers, mini-program link wrappers, absolute positioning, and nested cards around images.

## Re-Uploading One Body Image

When the user says they manually edited the article and only one image is broken:

1. First call `draft/get` and use the latest remote draft content. Do not use stale local HTML, because it may overwrite the user's manual edits.
2. Upload only the requested local image through `media/uploadimg`.
3. Replace only the target image area.
4. Preserve all current fields from `draft/get`: `title`, `author`, `digest`, `content_source_url`, `show_cover_pic`, `need_open_comment`, `only_fans_can_comment`.
5. If `thumb_media_id` is empty but `thumb_url` exists, re-upload the current `thumb_url` as permanent material and use the new `thumb_media_id`; otherwise `draft/update` may fail with `40007 invalid media_id`.

## Important: Broken Image Containers

WeChat may save a failed image not as an `<img>`, but as an error container:

```html
<section class="img_wrapper js_img_error js_all_error img_fail_mask">
  ...
  上传失败，网络异常。
  重试
  ...
</section>
```

If this appears:

- Replace the entire outer error block, not only an image `src`.
- The outer block can be:
  - `<section style="text-align: center;"><section class="img_wrapper js_img_error ...">...</section></section>`
- Replace it with a clean image block using the newly uploaded WeChat CDN URL.
- Verify after `draft/update`:
  - no `img_wrapper js_img_error`
  - no `上传失败`
  - no `网络异常`
  - expected image count
  - first image domain is `mmbiz.qpic.cn`

## Verification Checklist

After every create/update:

- Call `draft/get`.
- Verify title still matches the user-edited title when the user edited it manually.
- Verify image count.
- Verify no `<pre`, `<code`, or `code-snippet`.
- Verify no `img_wrapper js_img_error`, `上传失败`, or `网络异常`.
- Save only sanitized logs under the project `OPS/wechat-publish-runs/`; never save tokens or secrets.


## 贴图 / 小绿书草稿（newspic）

给出标题、短文案和按顺序排列的图片，即可放入公众号草稿箱供预览。适合图片卡片、作品集和简短分享；文章仍走上面的文章排版流程。

1. 首次使用先完成上面的本地凭证和白名单配置；已有配置直接复用买家本机 env，不询问服务端账号别名。
2. 若需要创作新图，先使用用户指定的生图工具；付费前遵守该工具的报价和授权要求。也可直接复用用户已有图片。本脚本只负责上传，不触发生图。
3. 用本目录 `requirements.txt` 安装 Pillow；准备纯文本正文文件和 1–20 张 PNG/JPEG。每张小于 10 MiB；标题 1–32 个字符，正文采用保守上限 2048 UTF-8 字节。图片全部通过本地解码、大小和重复检查后才允许上传。
4. 先 `--dry-run`；检查图片预览及顺序，再按用户授权执行真实推送：

```bash
python3 publish.py --type newspic \
  --title '本周的三张灵感卡片' --content-file /absolute/path/content.txt \
  --images /absolute/path/01.png /absolute/path/02.jpg \
  --dry-run

python3 publish.py --type newspic \
  --env-file /absolute/path/private.env \
  --title '本周的三张灵感卡片' --content-file /absolute/path/content.txt \
  --images /absolute/path/01.png /absolute/path/02.jpg \
  --receipt /absolute/path/private-output/picture-draft.json
```

5. 每张图片通过 `/wechat/material/add_material` 上传为永久素材；按输入顺序写入 `image_info.image_list[].image_media_id`。首张作为贴图封面，不额外上传文章封面，不把图片塞进 HTML。
6. `/wechat/draft/add` 只提交一条 `article_type: newspic` 草稿。成功后必须 `/wechat/draft/get`，验证类型、标题、纯文本正文、图片数量及素材编号顺序。只有回执 `status: verified` 才能报告核验通过。
7. 回执保留已上传图片编号、草稿编号及状态，不存凭证。将回执放在仓库外或已忽略的目录；同一次任务始终复用同一路径。再次运行有草稿编号的回执只回读，不重建。
8. 上传失败、创建超时或结果未知时停止；不要换回执路径重新提交。先查回执和公众号素材/草稿箱。读草稿失败可重跑同一命令，仅继续回读。若进程被强制终止而遗留 `.lock`，先确认没有运行中的进程并核对远程状态，再由操作者处理锁文件。
9. 这是推送到草稿箱，不是公开发布或群发。浏览器预览不可用时，分别报告 API 核验和视觉验收的实际状态。

本地回归：在仓库根目录运行 `python3 -m unittest discover -s tests -v` 和 `node --test tests/request-credentials.test.mjs`。
