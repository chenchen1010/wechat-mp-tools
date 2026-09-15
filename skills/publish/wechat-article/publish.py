#!/usr/bin/env python3
"""
微信公众号文章发布脚本（通过 ECS 代理 API）

用法:
  python publish.py -m article.md
  python publish.py -m article.md --account qwjxqn --author 作者名
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path


def load_env(env_path: Path | None = None):
    """从 .env 文件加载环境变量"""
    candidates = [env_path] if env_path else [
        Path.cwd() / '.env',
        Path(__file__).resolve().parents[3] / '.env',
    ]
    for p in candidates:
        if p and p.exists():
            for line in p.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            return


def api_post(base_url: str, token: str, endpoint: str, payload: dict, timeout: int = 60) -> dict:
    """调用 ECS 代理 API"""
    url = f"{base_url}{endpoint}"
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, method='POST', headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}',
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode('utf-8'))


def upload_body_image(base_url: str, token: str, account: str, image_path: Path) -> str:
    """上传正文图片，返回微信 CDN URL"""
    b64 = base64.b64encode(image_path.read_bytes()).decode('ascii')
    result = api_post(base_url, token, '/wechat/media/uploadimg', {
        'account': account,
        'image_base64': b64,
        'filename': f'upload{image_path.suffix.lower()}',
    })
    if 'url' not in result:
        raise RuntimeError(f'上传图片失败 {image_path.name}: {json.dumps(result, ensure_ascii=False)}')
    return result['url']


def upload_cover(base_url: str, token: str, account: str, image_path: Path) -> str:
    """上传封面（永久素材），返回 media_id"""
    b64 = base64.b64encode(image_path.read_bytes()).decode('ascii')
    result = api_post(base_url, token, '/wechat/material/add_material', {
        'account': account,
        'type': 'image',
        'image_base64': b64,
        'filename': f'cover{image_path.suffix.lower()}',
    })
    if 'media_id' not in result:
        raise RuntimeError(f'上传封面失败: {json.dumps(result, ensure_ascii=False)}')
    return result['media_id']


def create_draft(base_url: str, token: str, account: str, article: dict) -> dict:
    """创建草稿"""
    result = api_post(base_url, token, '/wechat/draft/add', {
        'account': account,
        'articles': [article],
    })
    if 'media_id' not in result:
        raise RuntimeError(f'创建草稿失败: {json.dumps(result, ensure_ascii=False)}')
    return result


def generate_cover_image(evolink_key: str, prompt: str, output_path: str) -> bool:
    """用 Evolink 生成封面图"""
    req = urllib.request.Request(
        'https://api.evolink.io/v1/images/generations',
        data=json.dumps({
            'model': 'z-image-turbo',
            'prompt': prompt,
            'size': '16:9',
            'nsfw_check': False,
        }).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {evolink_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
        if 'data' not in data or not data['data']:
            print(f'生图失败: {data}', file=sys.stderr)
            return False
        with urllib.request.urlopen(data['data'][0]['url'], timeout=60) as img:
            Path(output_path).write_bytes(img.read())
        return True
    except Exception as e:
        print(f'生图异常: {e}', file=sys.stderr)
        return False


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """解析 YAML frontmatter"""
    meta = {}
    body = content
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            for line in parts[1].strip().split('\n'):
                if ':' not in line:
                    continue
                k, v = line.split(':', 1)
                meta[k.strip()] = v.strip().strip('"').strip("'")
            body = parts[2].strip()
    return meta, body


def markdown_to_html(body: str) -> str:
    """简易 Markdown → HTML（仅用于无 Wenyan 时的兜底）"""
    html = body
    html = re.sub(r'^###\s+(.+)$', r'<h3>\1</h3>', html, flags=re.M)
    html = re.sub(r'^##\s+(.+)$', r'<h2>\1</h2>', html, flags=re.M)
    html = re.sub(r'^#\s+(.+)$', r'<h1>\1</h1>', html, flags=re.M)
    html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
    html = re.sub(r'!\[.*?\]\((.+?)\)', r'<img src="\1" style="display:block;width:100%;"/>', html)
    html = re.sub(r'\[(.+?)\]\((.+?)\)', r'<a href="\2">\1</a>', html)
    html = html.replace('\n\n', '</p><p>')
    return f'<p>{html}</p>'


def main():
    parser = argparse.ArgumentParser(description='微信公众号文章发布（ECS 代理）')
    parser.add_argument('--markdown', '-m', help='Markdown 文件路径')
    parser.add_argument('--type', choices=['news', 'newspic'], default='news')
    parser.add_argument('--title', help='贴图标题')
    parser.add_argument('--content-file', help='贴图纯文本正文文件')
    parser.add_argument('--images', nargs='+', help='按展示顺序列出的本地 PNG/JPEG 图片')
    parser.add_argument('--receipt', help='本次推送的持久回执 JSON 路径')
    parser.add_argument('--dry-run', action='store_true', help='仅校验贴图，不请求网络')
    parser.add_argument('--account', help='服务方为当前使用者绑定的公众号别名；也可从私有 env 读取')
    parser.add_argument('--author', default='', help='文章作者')
    parser.add_argument('--env-file', default=None, help='.env 文件路径')
    parser.add_argument('--cover-prompt', default='', help='Evolink 封面生成提示词')
    args = parser.parse_args()

    load_env(Path(args.env_file) if args.env_file else None)

    args.account = args.account or os.environ.get('WECHAT_MP_API_ACCOUNT_DEFAULT', '').strip()
    if not args.account and not args.dry_run:
        parser.error('需要 --account 或私有配置 WECHAT_MP_API_ACCOUNT_DEFAULT；不能自动选择公众号')

    if args.type == 'newspic':
        from newspic import run
        try:
            run(args, api_post)
        except Exception as exc:
            # Avoid exposing credentials embedded in upstream exception text.
            print(f'贴图未完成（{type(exc).__name__}）；检查参数和回执，勿自动重提。', file=sys.stderr)
            if isinstance(exc, (ValueError, RuntimeError)):
                print(str(exc), file=sys.stderr)
            sys.exit(1)
        return
    if not args.markdown or args.dry_run or args.images or args.content_file or args.title or args.receipt:
        parser.error('文章模式需要 -m；贴图参数和 --dry-run 仅用于 --type newspic')

    base_url = os.environ.get('WECHAT_MP_API_BASE_URL', '')
    api_token = os.environ.get('WECHAT_MP_API_TOKEN', '')
    if not base_url or not api_token:
        print('错误: 需要设置 WECHAT_MP_API_BASE_URL 和 WECHAT_MP_API_TOKEN', file=sys.stderr)
        sys.exit(1)

    # 1. 解析 Markdown
    md_path = Path(args.markdown)
    content = md_path.read_text(encoding='utf-8')
    meta, body = parse_frontmatter(content)
    title = meta.get('title', md_path.stem)
    cover_path = meta.get('cover', '')
    author = args.author or meta.get('author', '')
    print(f'1/4 解析完成: {title}')

    # 2. 封面
    temp_cover = None
    if not cover_path or not Path(cover_path).exists():
        evolink_key = os.environ.get('EVOLINK_API_KEY', '')
        if evolink_key:
            print('2/4 生成封面...')
            temp_cover = f'/tmp/cover_{int(time.time())}.jpg'
            prompt = args.cover_prompt or f'Professional cover for: {title}, modern digital art, 16:9'
            if not generate_cover_image(evolink_key, prompt, temp_cover):
                sys.exit(1)
            cover_path = temp_cover
        else:
            print('2/4 警告: 无封面且无 EVOLINK_API_KEY，跳过', file=sys.stderr)
            sys.exit(1)
    else:
        print(f'2/4 使用封面: {cover_path}')

    thumb_media_id = upload_cover(base_url, api_token, args.account, Path(cover_path))
    print(f'  ✓ 封面 media_id: {thumb_media_id}')

    # 3. 渲染 HTML（简易兜底，生产建议用 Wenyan MCP）
    print('3/4 渲染 HTML...')
    html_content = markdown_to_html(body)

    # 4. 创建草稿
    print('4/4 创建草稿...')
    result = create_draft(base_url, api_token, args.account, {
        'title': title,
        'author': author,
        'content': html_content,
        'thumb_media_id': thumb_media_id,
        'show_cover_pic': 1,
        'need_open_comment': 1,
        'only_fans_can_comment': 0,
    })

    if temp_cover and Path(temp_cover).exists():
        Path(temp_cover).unlink()

    print(f'\n✅ 草稿创建成功!')
    print(f'   media_id: {result["media_id"]}')


if __name__ == '__main__':
    main()
