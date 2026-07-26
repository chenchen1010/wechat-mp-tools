---
name: wechat-article-publish
slug: wechat-article-publish
displayName: 微信公众号文章发布
version: 1.0.0
summary: 把 Markdown 文章整理并发布到公众号草稿箱，同时处理图片上传、草稿更新和常见编辑器兼容问题。
description: 适用于微信公众号文章发布、草稿更新、正文图片重传、微信编辑器兼容性修复，以及 chenchen1010/wechat-mp-tools 的发布流程。
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
