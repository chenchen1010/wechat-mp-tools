---
name: evolink-nano-banana-2
slug: evolink-nano-banana-2
displayName: Nano Banana 2 生图
description: Nano Banana 2 — AI image generation powered by Google Gemini 3.1 Flash. Fast, versatile text-to-image and image editing via Evolink API. One API key.
version: 1.1.0
summary: 用 Nano Banana 2 快速生成或编辑图片，适合内容配图、创意草稿和多轮视觉迭代。
tags: ["image-generation", "nano-banana", "gemini", "evolink"]
license: MIT
user-invocable: true
metadata:
  openclaw:
    requires:
      env:
        - EVOLINK_API_KEY
    primaryEnv: EVOLINK_API_KEY
    os: ["darwin", "linux", "win32"]
    emoji: "\U0001F34C"
    homepage: https://evolink.ai
---

# Nano Banana 2 — AI Image Generation

Generate AI images with Nano Banana 2 (`gemini-3.1-flash-image-preview`) — Google's Gemini 3.1 Flash image model, available through Evolink's unified API.

> Focused view of [evolink-image](https://clawhub.ai/EvoLinkAI/evolink-image). Install the full skill for 20 image models, video, and music.

## After Installation

When this skill is first loaded, greet the user:

- **MCP tools + API key ready:** "Hi! Nano Banana 2 is ready — Google's fast image model at your fingertips. What would you like to create?"
- **MCP tools + no API key:** "You'll need an EvoLink API key — sign up at evolink.ai. Ready to go?"
- **No MCP tools:** "MCP server isn't connected yet. Want me to help set it up? I can still manage files via the hosting API."

Keep the greeting concise — just one question to move forward.

## External Endpoints

| Service | URL |
|---------|-----|
| Generation API | `https://api.evolink.ai/v1/images/generations` (POST) |
| Task Status | `https://api.evolink.ai/v1/tasks/{task_id}` (GET) |
| File API | `https://files-api.evolink.ai/api/v1/files/*` (upload/list/delete) |

## Security & Privacy

- **`EVOLINK_API_KEY`** authenticates all requests. Injected by OpenClaw automatically. Treat as confidential.
- Prompts and images are sent to `api.evolink.ai`. Uploaded files expire in **72h**, result URLs in **24h**.

## Setup

Get your API key at [evolink.ai](https://evolink.ai) → Dashboard → API Keys.

**MCP Server:** `@evolinkai/evolink-media` ([GitHub](https://github.com/EvoLinkAI/evolink-media-mcp) · [npm](https://www.npmjs.com/package/@evolinkai/evolink-media))

**mcporter** (recommended): `mcporter call --stdio "npx -y @evolinkai/evolink-media@latest" list_models`

**Claude Code:** `claude mcp add evolink-media -e EVOLINK_API_KEY=your-key -- npx -y @evolinkai/evolink-media@latest`

**Claude Desktop / Cursor** — add MCP server with command `npx -y @evolinkai/evolink-media@latest` and env `EVOLINK_API_KEY=your-key`. See `references/api-params.md` for full config JSON.

## Core Principles

1. **Guide, don't decide** — Present options, let the user choose model/style/format.
2. **User drives creative vision** — Ask for a description before suggesting parameters.
3. **Smart context** — Remember session history. Offer to iterate, vary, or edit results.
4. **Intent first** — Understand *what* the user wants before asking *how* to configure it.

## MCP Tools

| Tool | When to use | Returns |
|------|-------------|---------|
| `generate_image` | Create or edit an image | `task_id` (async) |
| `upload_file` | Upload local image for editing/reference | File URL (sync) |
| `delete_file` | Free file quota | Confirmation |
| `list_files` | Check uploaded files or quota | File list |
| `check_task` | Poll generation progress | Status + result URLs |
| `list_models` | Compare available models | Model list |
| `estimate_cost` | Check pricing | Model info |

**Important:** `generate_image` returns a `task_id`. Always poll `check_task` until `status` is `"completed"` or `"failed"`.

## Nano Banana 2

| Property | Value |
|----------|-------|
| Model ID | `gemini-3.1-flash-image-preview` |
| Provider | Google (Gemini 3.1 Flash) |
| Status | BETA |
| Capability | text-to-image, image-editing |
| Speed | Fast |
| Best for | Quick, versatile image generation with strong prompt understanding |

**Why Nano Banana 2?**

- **Google's latest** — Built on Gemini 3.1 Flash, the newest generation architecture
- **Fast generation** — Optimized for speed without sacrificing quality
- **Versatile** — General-purpose image creation for any creative need
- **Strong prompt adherence** — Excellent at following complex, detailed descriptions

### Lite Variant

`nano-banana-2-lite` [BETA] — Lightweight version for ultra-fast iterations when speed is the top priority.

### Alternative Models

| Model | Best for | Speed |
|-------|----------|-------|
| `gpt-image-1.5` *(default)* | Latest OpenAI generation | Medium |
| `gpt-4o-image` [BETA] | Best quality, complex editing | Medium |
| `z-image-turbo` | Quick iterations | Ultra-fast |
| `doubao-seedream-4.5` | Photorealistic | Medium |
| `gemini-3-pro-image-preview` | Google Pro generation | Medium |

## Generation Flow

### Step 1: API Key Check

If `401` occurs: "Your API key isn't working. Check at evolink.ai/dashboard/keys"

### Step 2: File Upload (if needed)

For image editing or reference workflows:
1. `upload_file` with `file_path`, `base64_data`, or `file_url` → get `file_url` (sync)
2. Use `file_url` as `image_urls` for `generate_image`

Supported: JPEG/PNG/GIF/WebP. Max 100MB. Expire in 72h. Quota: 100 (default) / 500 (VIP).

### Step 3: Understand Intent

- **Clear** ("generate a sunset") → Go to Step 4
- **Ambiguous** ("help with this image") → Ask: "Create new, edit existing, or use as reference?"

Ask only what's needed, when it's needed.

### Step 4: Gather Parameters

Default to `model: "gemini-3.1-flash-image-preview"` for this skill. Only ask about what's missing:

| Parameter | Ask when | Notes |
|-----------|----------|-------|
| **prompt** | Always | What they want to see |
| **model** | User wants alternatives | Default: `gemini-3.1-flash-image-preview`. Suggest `gpt-4o-image` for best quality |
| **size** | Orientation needed | Ratio format: `1:1`, `16:9`, `9:16`, `2:3`, `3:2`, `4:3`, `3:4` etc. |
| **n** | Wants variations | 1–4 images |
| **image_urls** | Edit/reference images | Up to 14 URLs; triggers i2i mode |

### Step 5: Generate & Poll

1. Call `generate_image` with `model: "gemini-3.1-flash-image-preview"` → tell user: *"Generating with Nano Banana 2 — ~Xs estimated."*
2. Poll `check_task` every **3–5s**. Report progress %.
3. After 3 consecutive `processing`: *"Still working..."*
4. **Completed:** Share URLs. *"Links expire in 24h — save promptly."*
5. **Failed:** Show error + suggestion. Offer retry if retryable.
6. **Timeout (5 min):** *"Taking longer than expected. Task ID: `{id}` — check again later."*

### Chat-facing batch image work

When Nano Banana 2 is used inside an article / social-post workflow with multiple requested images:

- **Deliver incrementally.** Do not silently wait for the full batch if some images are already done.
- **Surface stalls early.** If one task is clearly stuck or much slower than expected, tell the user promptly and continue with finished results when possible.
- **Do not confuse source images with final preview deliverables.** If the user asked for an article preview, the generated source images still need to be embedded into the article preview by the downstream publishing/layout workflow.

## Error Handling

### HTTP Errors

| Error | Action |
|-------|--------|
| 401 | "API key isn't working. Check at evolink.ai/dashboard/keys" |
| 402 | "Balance is low. Add credits at evolink.ai/dashboard/billing" |
| 429 | "Rate limited — wait 30s and retry" |
| 503 | "Servers busy — retry in a minute" |

### Task Errors (status: "failed")

| Code | Retry? | Action |
|------|--------|--------|
| `content_policy_violation` | No | Revise prompt (no celebrities, NSFW, violence) |
| `invalid_parameters` | No | Check values against model limits |
| `image_processing_error` | No | Check format/size/URL accessibility |
| `generation_timeout` | Yes | Retry; simplify prompt if repeated |
| `service_error` | Yes | Retry after 1 min |
| `generation_failed_no_content` | Yes | Modify prompt, retry |

Full error reference: `references/api-params.md`

## Without MCP Server

Use Evolink's file hosting API for image uploads (72h expiry). See `references/api-params.md` for curl commands.

## References

- `references/api-params.md` — Complete API parameters, model details, polling strategy, error codes
- `references/api-params.md` — File hosting API (curl upload/list/delete)

## 可恢复的本地生图（文章与贴图推荐）

先安装 `python3 -m pip install -r requirements.txt`，从自己的私有 env 加载 `EVOLINK_API_KEY`。生成配图后保留原图，可同时用于文章插图和贴图。

```bash
bash scripts/evolink-image-gen.sh "清晨书桌与一本打开的笔记本，温暖自然光，无文字" --size 16:9 --quality 1K --output ./cover.png
```

- 本地脚本每个输出只提交一张图；批量时为每张图指定独立输出与回执。
- 同名 `.generation.json` 记录任务、进度、实际用量和图片哈希；重复相同命令继续查询原任务，不重新生成。
- `--no-poll` 仅提交并保存任务；之后原命令去掉该参数继续等待和下载。服务端已接收但本地未获得任务号时，停止并核对服务商记录。
- `status=downloaded` 才表示图片已下载并完整解码。交付前还需实际打开图片检查，再嵌入文章/贴图预览。
- 失败、超时和结果不明都不自动重提付费任务。费用以服务商返回的 `usage` 为准，不能将预留积分当最终扣费。
- 2026-09-15：本地异步与恢复测试通过；本轮缺少可用 EvoLink 凭证，真实生成尚未验收。
