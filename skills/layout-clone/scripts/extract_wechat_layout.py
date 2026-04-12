#!/usr/bin/env python3
"""
从微信公众号文章页提取 #js_content 区域的排版信号（内联 style + 结构标签），
输出 JSON 供 LLM 生成「主题配置」——与「curl UA + js_content + 抽样式 + AI 归纳」链路一致。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from html import unescape
from typing import Any

try:
    from bs4 import BeautifulSoup, Tag
except ImportError:
    print("请先安装依赖: pip install -r requirements.txt", file=sys.stderr)
    sys.exit(1)

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

_VERIFY_MARKERS = ("环境异常", "请在微信客户端打开", "secitptpage", "risk_redirect")


def fetch_html(url: str, timeout: int = 30) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    for enc in ("utf-8", "gb18030", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def looks_like_wechat_block(html: str) -> bool:
    return any(m in html for m in _VERIFY_MARKERS)


def normalize_style(style: str) -> str:
    s = unescape(style or "").strip()
    s = re.sub(r"\s*;\s*", "; ", s)
    s = re.sub(r"\s*:\s*", ": ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip().rstrip(";")


def walk_collect_styles(root: Tag, max_elements: int) -> tuple[list[dict[str, Any]], Counter[tuple[str, str]]]:
    rows: list[dict[str, Any]] = []
    pair_counts: Counter[tuple[str, str]] = Counter()

    def visit(node: Tag, depth: int) -> None:
        nonlocal rows
        if len(rows) >= max_elements:
            return
        name = node.name.lower() if node.name else ""
        if name in ("script", "style", "noscript"):
            return
        st = node.get("style")
        if isinstance(st, str) and st.strip():
            ns = normalize_style(st)
            # 微信懒加载常见占位，对「学排版」无意义且占满样本配额
            if re.search(r"visibility:\s*hidden", ns, re.I) and re.search(
                r"opacity:\s*0", ns, re.I
            ):
                for child in node.children:
                    if isinstance(child, Tag):
                        visit(child, depth + 1)
                return
            if ns:
                pair_counts[(name, ns)] += 1
                if len(rows) < max_elements:
                    rows.append(
                        {
                            "tag": name,
                            "style": ns,
                            "class": node.get("class"),
                            "depth": depth,
                            "text_preview": (node.get_text(strip=True) or "")[:80],
                        }
                    )
        for child in node.children:
            if isinstance(child, Tag):
                visit(child, depth + 1)

    visit(root, 0)
    return rows, pair_counts


def aggregate_by_tag(pair_counts: Counter[tuple[str, str]]) -> dict[str, list[dict[str, Any]]]:
    by_tag: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for (tag, style), cnt in pair_counts.items():
        by_tag[tag].append((style, cnt))
    out: dict[str, list[dict[str, Any]]] = {}
    for tag, pairs in by_tag.items():
        pairs.sort(key=lambda x: -x[1])
        out[tag] = [{"style": s, "count": c} for s, c in pairs[:12]]
    return out


def strip_scripts(soup: BeautifulSoup) -> None:
    for el in soup.find_all(["script", "style"]):
        el.decompose()


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract WeChat article layout signals from #js_content")
    ap.add_argument("url_or_path", help="mp.weixin.qq.com 文章 URL，或本地 .html 文件路径")
    ap.add_argument("-o", "--output", help="写入 JSON 文件（默认只打印 stdout）")
    ap.add_argument("--max-elements", type=int, default=220, help="最多采集多少条带 style 的节点样本")
    ap.add_argument("--snippet-chars", type=int, default=12000, help="sample_html 最大字符数")
    args = ap.parse_args()

    path = args.url_or_path
    if path.startswith("http://") or path.startswith("https://"):
        try:
            html = fetch_html(path)
        except urllib.error.URLError as e:
            print(json.dumps({"ok": False, "error": f"fetch_failed: {e}", "source": path}, ensure_ascii=False))
            sys.exit(2)
    else:
        with open(path, encoding="utf-8", errors="replace") as f:
            html = f.read()

    bundle: dict[str, Any] = {
        "ok": True,
        "source_url": path if path.startswith("http") else None,
        "local_file": path if not path.startswith("http") else None,
        "verification_or_risk_page": looks_like_wechat_block(html),
    }

    if bundle["verification_or_risk_page"]:
        bundle["ok"] = False
        bundle["hint"] = (
            "页面疑似风控/验证页。请用微信内打开该链接另存为 HTML，"
            "再对本脚本传入本地文件路径；或使用 wechat-article-for-ai（Camoufox）抓取后再提取。"
        )
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
        sys.exit(3)

    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.select_one("#activity-name")
    author_el = soup.select_one("#js_name")
    bundle["article_title"] = title_el.get_text(strip=True) if title_el else ""
    bundle["author"] = author_el.get_text(strip=True) if author_el else ""

    content = soup.select_one("#js_content")
    if not content:
        bundle["ok"] = False
        bundle["error"] = "未找到 #js_content（可能不是图文页或 HTML 不完整）"
        print(json.dumps(bundle, ensure_ascii=False, indent=2))
        sys.exit(4)

    samples, pair_counts = walk_collect_styles(content, args.max_elements)
    bundle["inline_style_samples"] = samples
    bundle["style_frequency_by_tag"] = aggregate_by_tag(pair_counts)

    strip_scripts(soup)
    content2 = soup.select_one("#js_content")
    raw_html = str(content2) if content2 else ""
    bundle["sample_html"] = raw_html[: args.snippet_chars]
    if len(raw_html) > args.snippet_chars:
        bundle["sample_html_truncated"] = True

    bundle["llm_task"] = (
        "根据 style_frequency_by_tag 与 inline_style_samples，归纳："
        "1) 主题英文名 id（小写、简短）；2) 中文说明；"
        "3) 正文/各级标题/引用/代码/链接/强调 的 CSS 规则（可映射到 markdown-to-html 模板）；"
        "4) 与原文风格差异的免责声明（微信编辑器会吞部分样式）。"
    )

    text = json.dumps(bundle, ensure_ascii=False, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
    print(text)


if __name__ == "__main__":
    main()
