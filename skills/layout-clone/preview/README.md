# 公众号样式预览

- **`half-journey-wechat-layout.html`**：示例长文预览（可直接用浏览器打开）。
- **`generate_half_journey.py`**：重新生成该 HTML。

## 分段与加粗

1. 在 `generate_half_journey.py` 里编辑 **`PARAS`**：列表中**每一项 = 一段**（会渲染为一个 `section`）。
2. 段内用 **`**像这样**`** 包住需要加粗的词句；脚本会转成微信常见的 `font-weight: bold` 内联 `span`。
3. 若拿到的是**一大段未分行的文字**：先在编辑器里按语义拆成多条字符串放进 `PARAS`，再为金句、概念、转折补 `**…**`，然后运行 `python3 generate_half_journey.py`。

## 行距 / 字距与真机差异说明

- **字间距**：与原文一致，内层 `letter-spacing: 1px`；外层另有 `letter-spacing: 0.034em`（嵌套后正文以 1px 为准）。
- **行间距**：原文外层为 `font-size: 17px; line-height: 1.6`。在 WebKit/微信里，行盒高度常由 **17×1.6 ≈ 27.2px** 的 strut 撑起；若浏览器按内层 **15×1.6** 算行高，会显得偏紧。生成脚本在内层显式写了 **`line-height: 27.2px`** 以对齐这种行盒。
- **段间距**：`mp` 里多数 `section` **没有**上下 margin；预览里勿再额外加 `section + section { margin-top: … }`，否则会与原文疏密不一致。

修改正文时编辑 `generate_half_journey.py` 里的 `PARAS`，然后执行：

```bash
python3 generate_half_journey.py
```
