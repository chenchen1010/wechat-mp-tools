---
name: wechat-article-publish
slug: wechat-article-publish
displayName: 微信公众号文章与贴图发布
version: 1.1.1
summary: 把文章或多张贴图送入公众号草稿箱，自动上传图片并核对结果，减少逐张上传和手工整理。
description: 适用于微信公众号文章或贴图（newspic、小绿书）草稿发布、多图上传、草稿回读核验、正文图片重传和编辑器兼容性修复。
tags: ["wechat", "公众号", "文章发布", "内容运营"]
license: MIT
homepage: https://github.com/chenchen1010/wechat-mp-tools
---

# 微信公众号文章与贴图发布

面向购买本 Skill 的公众号运营者：在本机准备文章、排版和图片，通过服务方提供的固定公网 IP 推送到**买家自己的公众号草稿箱**，减少反复上传和更换电脑后的白名单配置。

## 买家首次使用：绑定自己的公众号

1. 告知买家：共用的是服务方服务器的公网出口 IP；文章和图片将由该服务器转交微信，目标是买家自己绑定的公众号。
2. 引导买家登录自己的微信公众号后台，在开发配置中找到 `IP 白名单`（常见入口为 `设置与开发 → 基本配置`；以当前后台为准），**追加服务方服务器公网 IP `8.153.207.214`**。保留原有白名单，不填买家电脑的 IP，也不把网址或端口填进去。服务方变更出口时必须更新本指南。
3. 引导买家获取自己公众号的 AppID、AppSecret。首次绑定涉及将公众号凭证交给服务方服务器，应先向买家说明用途，再通过服务方提供的私密配置渠道完成；凭证仅进受保护配置，不进聊天回复、Skill 包、Git、日志或公开表单。
4. 服务方为该买家完成账号绑定并提供**仅能访问其公众号**的服务地址、访问凭证和账号别名。当前仓库没有自动购买/开户/绑定入口，不能编造已开通；尚未开通就明确告知需服务方完成绑定。
5. 将该买家的配置保存到他自己的、已忽略且权限为600的本地 env 文件：
   - `WECHAT_MP_API_BASE_URL`：服务方为该买家开通的地址。
   - `WECHAT_MP_API_TOKEN`：该买家专用访问凭证。
   - `WECHAT_MP_API_ACCOUNT_DEFAULT`：该买家已绑定的账号别名。
6. 记录本机配置中的公众号名称与别名对应关系（不记录秘密值）。`default` 只是别名，不代表任何固定公众号；不能继承开发者机器上的个人账号、env路径或共享管理凭证，也不能从别名推断公众号名称。
7. 首次使用先通过 `/token/test` 验证连接，再按买家授权推送测试草稿，回读核验并请买家在自己的公众号后台查看。遇到 `40164 invalid ip`，引导买家检查是否已将服务方出口 IP 加入**该公众号**白名单；切勿改成本机直连。

## 文章和贴图共用的发布路径

- 从买家指定的私有 env 读取上述三项配置；账号必须显式指定或来自买家配置，缺失时不能回退到开发者的 `default`。
- 文章先完成本地排版，图片上传和草稿写入统一走服务方代理；不要以本机直连微信的 Wenyan `publish_article` 作为共享 IP 方案的默认路径。
- `/wechat/media/uploadimg`：上传文章正文图片。
- `/wechat/material/add_material`：上传封面和贴图永久图片。
- `/wechat/draft/add`、`/wechat/draft/update`、`/wechat/draft/get`：创建、更新、回读草稿。
- 默认只送入草稿箱，不能将草稿成功说成公开发布或群发成功。

## 服务方交付边界

当前 `api-server/server.mjs` 使用进程级共享 `API_TOKEN` 和静态账号列表，不具备按买家鉴权的账号隔离。**不能把现有自用服务的同一个令牌发给所有买家**，也不能仅靠客户端的 `account` 参数隔离公众号。

在同一公网 IP 下，可由服务方给每位买家部署独立实例、独立令牌，仅配置其自己的公众号；或先实现并验收服务端“买家凭证 → 允许访问的账号”绑定。公网 IP 可以共用，公众号凭证、访问权限和草稿必须隔离。当前开发者自用测试通过，不等于第三方开户与隔离已上线。

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

1. 首次使用先完成上面的买家绑定流程；已有绑定直接复用该买家配置，不反复询问名称，不猜测别名对应关系。
2. 若需要创作新图，先使用用户指定的生图工具；付费前遵守该工具的报价和授权要求。也可直接复用用户已有图片。本脚本只负责上传，不触发生图。
3. 用本目录 `requirements.txt` 安装 Pillow；准备纯文本正文文件和 1–20 张 PNG/JPEG。每张小于 10 MiB；标题 1–32 个字符，正文采用保守上限 2048 UTF-8 字节。图片全部通过本地解码、大小和重复检查后才允许上传。
4. 先 `--dry-run`；检查图片预览及顺序，再按用户授权执行真实推送：

```bash
python3 publish.py --type newspic --account BUYER_ACCOUNT \
  --title '本周的三张灵感卡片' --content-file /absolute/path/content.txt \
  --images /absolute/path/01.png /absolute/path/02.jpg \
  --dry-run

python3 publish.py --type newspic --account BUYER_ACCOUNT \
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

本地回归：在仓库根目录运行 `python3 -m unittest discover -s tests -v`。
