---
name: image-prompt-reverse
description: 通过 Gemini 视觉模型反推图片的生成提示词，支持本地图片和 URL
---

# 图片提示词反推

调用 Gemini 3 Pro（通过 AICodeWith 中转）分析图片，反推出可能的生成提示词。

## 何时使用

当用户说"反推提示词"、"这张图的 prompt 是什么"、"分析这张图怎么生成的"、"提取图片提示词"时使用此 skill。

## 前置条件

AICodeWith API key 已配置：
```bash
test -f ~/.content-matrix/config.json && jq -r '.aicodewith.api_key // empty' ~/.content-matrix/config.json | grep -q 'sk-' && echo "OK" || echo "MISSING"
```
如输出 `MISSING`，提示用户提供 API key 并写入 `~/.content-matrix/config.json`。

## 工作流程

### Step 1: 获取图片

向用户确认图片来源：
- **本地文件路径**：如 `~/Downloads/image.png`
- **图片 URL**：如 `https://example.com/image.jpg`

如果用户已经在消息中提供了图片路径或 URL，直接使用，无需再问。

### Step 2: 调用 Gemini 分析

读取配置：
```bash
ACW_KEY=$(jq -r '.aicodewith.api_key' ~/.content-matrix/config.json)
GEMINI_URL="https://api.aicodewith.com/gemini_cli/v1beta/models/gemini-3-pro:generateContent"
```

系统提示词（固定，所有请求共用）：
```
PROMPT_TEXT="你是一个专业的 AI 图片逆向工程专家。仔细分析这张图片，完成以下任务：

**重要：如果图片中包含任何文字内容（标题、标语、水印、UI 文字等），必须完整识别并体现在提示词中。**

请输出：

1. **反推提示词（中文）**：最可能用于生成这张图片的完整提示词。用中文书写，采用主流 AI 绘图工具（Midjourney/DALL-E/Stable Diffusion/Flux）的提示词风格。必须包含：主体、风格、光影、构图、色彩、氛围、细节。如图中有文字，提示词中必须包含该文字内容及其排版方式。

2. **反推提示词（English）**：同一提示词的英文版本，可直接用于图片生成工具。

3. **负面提示词**：如适用，给出建议的负面提示词（中英双语）。

4. **图片文字识别**：列出图片中所有可见的文字内容（如无文字则注明"无文字内容"）。

5. **视觉分析**：简要说明你从哪些视觉线索得出这个提示词——风格特征、构图模式、渲染特点等。

6. **推测生成模型**：最可能使用的图片生成模型/工具（Midjourney、DALL-E 3、Stable Diffusion XL、Flux 等），以及判断依据。

请尽量具体和详细。"
```

**情况 A：本地图片**

将图片转为 base64 后调用 Gemini 原生 API：
```bash
IMG_BASE64=$(base64 -i "<图片路径>")
MIME_TYPE="image/png"  # 根据实际扩展名判断：.jpg/.jpeg→image/jpeg, .png→image/png, .webp→image/webp

curl -s "${GEMINI_URL}" \
  -H "x-goog-api-key: ${ACW_KEY}" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg img "$IMG_BASE64" \
    --arg mime "$MIME_TYPE" \
    --arg prompt "$PROMPT_TEXT" \
    '{
      "contents": [
        {
          "parts": [
            {
              "inline_data": {
                "mime_type": $mime,
                "data": $img
              }
            },
            {
              "text": $prompt
            }
          ]
        }
      ]
    }')" | jq -r '.candidates[0].content.parts[-1].text'
```

**情况 B：图片 URL**

通过 fileUri 传 URL（如果 fileUri 不支持，则先下载图片再走情况 A）：
```bash
# 先下载图片到临时文件，再转 base64
TMP_IMG=$(mktemp /tmp/img_reverse_XXXXXX)
curl -sL "<图片URL>" -o "${TMP_IMG}"
MIME_TYPE=$(file --mime-type -b "${TMP_IMG}")
IMG_BASE64=$(base64 -i "${TMP_IMG}")
rm -f "${TMP_IMG}"

curl -s "${GEMINI_URL}" \
  -H "x-goog-api-key: ${ACW_KEY}" \
  -H "Content-Type: application/json" \
  -d "$(jq -n \
    --arg img "$IMG_BASE64" \
    --arg mime "$MIME_TYPE" \
    --arg prompt "$PROMPT_TEXT" \
    '{
      "contents": [
        {
          "parts": [
            {
              "inline_data": {
                "mime_type": $mime,
                "data": $img
              }
            },
            {
              "text": $prompt
            }
          ]
        }
      ]
    }')" | jq -r '.candidates[0].content.parts[-1].text'
```

### Step 3: 整理输出

将 Gemini 的返回结果整理后展示给用户，格式：

```
## 反推结果

### 反推提示词（中文）
<中文提示词>

### 反推提示词（English）
<英文提示词>

### 负面提示词
<中英双语负面提示词（如适用）>

### 图片文字识别
<图中所有文字内容>

### 视觉分析
<分析说明>

### 推测生成模型
<模型判断>
```

### Step 4: 可选 — 保存到素材库

询问用户是否需要将结果保存到 Obsidian 素材库的 `素材库/9-提示词库/` 目录下，文件名格式：`YYYY-MM-DD-<简短描述>.md`。
