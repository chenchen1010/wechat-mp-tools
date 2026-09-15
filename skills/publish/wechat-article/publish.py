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
import hashlib
import json
import os
import re
import sys
import urllib.request
import urllib.parse
from pathlib import Path


def load_env(env_path: Path | None = None):
    """从 .env 文件加载环境变量"""
    if env_path is not None and not env_path.is_file():
        raise ValueError('指定的本地 env 文件不存在')
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
                value = v.strip().strip('"').strip("'")
                if env_path is not None:
                    os.environ[k.strip()] = value
                else:
                    os.environ.setdefault(k.strip(), value)
            return


def request_credentials():
    appid = os.environ.get('WECHAT_MP_APP_ID', '').strip()
    secret = os.environ.get('WECHAT_MP_APP_SECRET', '').strip()
    if not re.fullmatch(r'wx[a-zA-Z0-9]{16}', appid) or not re.fullmatch(r'[a-zA-Z0-9]{32}', secret):
        raise ValueError('请在自己的本地 env 配置有效 WECHAT_MP_APP_ID 和 WECHAT_MP_APP_SECRET')
    return appid, secret


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError('发布服务发生重定向，已停止以避免转发公众号凭证')


def api_post(base_url: str, token: str, endpoint: str, payload: dict, timeout: int = 60) -> dict:
    """Request mode carries local buyer credentials in HTTPS headers, never URLs."""
    mode = os.environ.get('WECHAT_MP_CREDENTIAL_MODE', 'request')
    if mode not in ('request', 'legacy'):
        raise ValueError('未知公众号凭证模式')
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    opener = urllib.request.build_opener(NoRedirect())
    if mode == 'request':
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('携带公众号凭证时必须使用无查询参数的 HTTPS 服务地址')
        # Old servers ignore credential headers and select their stored default.
        # Confirm request mode BEFORE sending credentials or performing any write.
        with opener.open(f'{base_url.rstrip("/")}/health', timeout=timeout) as health:
            capabilities = json.loads(health.read().decode('utf-8'))
        if capabilities.get('credential_mode') != 'request':
            raise RuntimeError('该服务器尚未启用每次携带凭证的买家模式；已停止，未提交到旧服务账号')
        appid, secret = request_credentials()
        headers.update({'X-Wechat-Appid': appid, 'X-Wechat-Appsecret': secret})
        payload = {k: v for k, v in payload.items() if k != 'account'}
    req = urllib.request.Request(f'{base_url}{endpoint}', data=json.dumps(payload).encode('utf-8'),
                                 method='POST', headers=headers)
    with opener.open(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode('utf-8'))
    if mode == 'request':
        # Do not let an upstream error response echo credentials into logs.
        raw = json.dumps(result)
        for sensitive in (secret, appid, token):
            if sensitive:
                raw = raw.replace(sensitive, '[redacted]')
        result = json.loads(raw)
    return result


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
    """Render actual Markdown blocks before WeChat sanitization."""
    import markdown
    return markdown.markdown(body, extensions=['tables', 'fenced_code', 'sane_lists'])


def main():
    parser = argparse.ArgumentParser(description='微信公众号文章发布（ECS 代理）')
    parser.add_argument('--markdown', '-m', help='Markdown 文件路径')
    parser.add_argument('--html', help='已完成排版的本地 HTML')
    parser.add_argument('--cover', help='Agent 已生成的本地封面路径（文章通用）')
    parser.add_argument('--type', choices=['news', 'newspic'], default='news')
    parser.add_argument('--title', help='贴图或 HTML 文章标题')
    parser.add_argument('--content-file', help='贴图纯文本正文文件')
    parser.add_argument('--images', nargs='+', help='按展示顺序列出的本地 PNG/JPEG 图片')
    parser.add_argument('--receipt', help='本次推送的持久回执 JSON 路径')
    parser.add_argument('--dry-run', action='store_true', help='仅校验贴图，不请求网络')
    parser.add_argument('--account', help='服务方为当前使用者绑定的公众号别名；也可从私有 env 读取')
    parser.add_argument('--author', default='', help='文章作者')
    parser.add_argument('--env-file', default=None, help='.env 文件路径')
    parser.add_argument('--cover-prompt', default='', help='缺封面时交给当前 Agent 的提示词；脚本不生图')
    args = parser.parse_args()

    load_env(Path(args.env_file) if args.env_file else None)

    mode = os.environ.get('WECHAT_MP_CREDENTIAL_MODE', 'request')
    if mode not in ('request', 'legacy'):
        parser.error('未知公众号凭证模式')
    if mode == 'request' and not args.dry_run:
        try:
            appid, _ = request_credentials()
        except ValueError as exc:
            parser.error(str(exc))
        if args.account:
            parser.error('买家模式由本地 AppID 确定公众号，不使用 --account 别名')
        args.account = 'appid-sha256:' + hashlib.sha256(appid.encode()).hexdigest()
    else:
        args.account = args.account or os.environ.get('WECHAT_MP_API_ACCOUNT_DEFAULT', '').strip()
        if not args.account and not args.dry_run:
            parser.error('旧服务模式需要显式账号配置，不能自动选择公众号')

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
    if args.html:
        if not args.title or not args.cover or not args.receipt or args.markdown or args.dry_run:
            parser.error('HTML 文章需要 --title --cover --receipt')
        from article_html import run
        run(args, sys.modules[__name__])
        return
    if not args.markdown or args.dry_run or args.images or args.content_file or args.title:
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
    cover_path = str(Path(args.cover).resolve()) if args.cover else meta.get('cover', '')
    if cover_path:
        cover_path = str((md_path.resolve().parent / cover_path).resolve())
    author = args.author or meta.get('author', '')
    from article_html import prepare_html
    rendered_html = markdown_to_html(body)
    prepare_html(rendered_html, md_path.resolve().parent)
    print(f'1/4 解析完成: {title}')

    # Image creation belongs to the user's current Agent, not this publisher.
    if not cover_path or not Path(cover_path).is_file():
        target = cover_path or str(md_path.resolve().with_suffix('.cover.png'))
        print(json.dumps({
            'status': 'needs_image',
            'action': 'generate_with_current_agent',
            'purpose': 'cover',
            'prompt': args.cover_prompt or (
                f'为文章《{title}》制作封面。结合正文选取一个具体视觉主体，'
                '构图简洁，主体集中在画面中部，保留裁切空间，不添加无关文字或水印。'
            ),
            'aspect_ratio': '16:9',
            'output_path': target,
            'next_step': '使用当前 Agent 可用的生图能力，保存并检查实际 PNG/JPEG 图片；'
                         '用 --cover 指定该图片后重新运行。当前 Agent 无法生图时，将提示词交给用户。',
        }, ensure_ascii=False, indent=2))
        sys.exit(2)
    print(f'2/4 使用封面: {cover_path}')

    # Both Markdown and copied-layout HTML use the same upload + durable receipt path.
    rendered_path = md_path.resolve().with_suffix('.rendered.html')
    rendered_path.write_text(rendered_html, encoding='utf-8')
    args.html = str(rendered_path)
    args.cover = cover_path
    args.title = title
    args.author = author
    args.receipt = args.receipt or str(md_path.resolve().with_suffix('.draft.json'))
    from article_html import run
    run(args, sys.modules[__name__])


if __name__ == '__main__':
    main()
