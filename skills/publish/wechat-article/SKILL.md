---
name: wechat-article-publish
slug: wechat-article-publish
displayName: 微信公众号文章与贴图发布
version: 1.1.0
summary: 把文章或多张贴图送入公众号草稿箱，自动上传图片并核对结果，减少逐张上传和手工整理。
description: 适用于微信公众号文章或贴图（newspic、小绿书）草稿发布、多图上传、草稿回读核验、正文图片重传和编辑器兼容性修复。
tags: ["wechat", "公众号", "文章发布", "内容运营"]
license: MIT
homepage: https://github.com/chenchen1010/wechat-mp-tools
---

# 微信公众号文章发布

Use this skill for公众号文章发布、草稿更新、正文图片重传、微信编辑器兼容性修复。Prefer the ECS proxy from `chenchen1010/wechat-mp-tools/skills/publish/wechat-article` instead of local direct WeChat API calls, because the ECS has the stable IP configured in the公众号后台白名单.

## First-Time Account Setup

If the user has not configured this公众号 before, guide them to微信公众号后台获取并配置：

1. In 微信公众平台, go to `设置与开发` -> `基本配置`.
2. Copy `开发者ID(AppID)` and `开发者密码(AppSecret)`.
3. Add the ECS fixed public IP to `IP 白名单`:
   - `8.153.207.214`
4. Store AppID/AppSecret only in private env such as `~/.codex/secrets/wechat_mp.env` or the ECS service `.env`. Never write them into project docs, article drafts, logs, or skill files.
5. If WeChat returns `40164 invalid ip`, tell the user to confirm `8.153.207.214` is in the公众号 IP 白名单 and retry through the ECS proxy, not local direct API.

## Core Route

1. Read credentials from local/private env only, never project docs:
   - `~/.codex/secrets/wechat_mp.env`
   - ECS service env on server if needed
2. Prefer ECS proxy:
   - `WECHAT_MP_API_BASE_URL=https://cs.qwjxqn.xyz/wechat-mp`
   - `WECHAT_MP_API_TOKEN` from private env or server `.env`
   - `WECHAT_MP_API_ACCOUNT_DEFAULT=default`
3. Use these ECS endpoints:
   - `/wechat/media/uploadimg` for body images
   - `/wechat/material/add_material` for cover/permanent image material
   - `/wechat/draft/add` for draft creation
   - `/wechat/draft/update` for draft edits
   - `/wechat/draft/get` for verification
4. Do not assume `/wechat/freepublish/submit` exists on the ECS proxy. If direct official `freepublish/submit` returns `48001 api unauthorized`, report that API publishing is not authorized and leave the article in草稿箱.

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

1. 确认公众号账号别名与用户指定的名称对应，不能猜测 `default` 是哪个号。
2. 若需要创作新图，先使用用户指定的生图工具；付费前遵守该工具的报价和授权要求。也可直接复用用户已有图片。本脚本只负责上传，不触发生图。
3. 用本目录 `requirements.txt` 安装 Pillow；准备纯文本正文文件和 1–20 张 PNG/JPEG。每张小于 10 MiB；标题 1–32 个字符，正文采用保守上限 2048 UTF-8 字节。图片全部通过本地解码、大小和重复检查后才允许上传。
4. 先 `--dry-run`；检查图片预览及顺序，再按用户授权执行真实推送：

```bash
python3 publish.py --type newspic --account default \
  --title '本周的三张灵感卡片' --content-file /absolute/path/content.txt \
  --images /absolute/path/01.png /absolute/path/02.jpg \
  --dry-run

python3 publish.py --type newspic --account default \
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
