"""Publish ordered picture drafts; durable receipts prevent accidental resubmission."""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import tempfile
from pathlib import Path


def prepare(title, content, paths):
    if not isinstance(title, str) or not title.strip() or len(title) > 32:
        raise ValueError('贴图标题须为 1–32 个字符')
    if not isinstance(content, str) or not content.strip() or len(content.encode('utf-8')) > 2048:
        raise ValueError('贴图正文须为非空纯文本，最多 2048 UTF-8 字节')
    if re.search(r'<\s*/?\s*[a-zA-Z][^>]*>', content):
        raise ValueError('贴图正文不支持 HTML')
    if not 1 <= len(paths) <= 20:
        raise ValueError('贴图需要 1–20 张图片')
    from PIL import Image
    images, hashes = [], set()
    for path in paths:
        path = Path(path)
        if not 0 < path.stat().st_size < 10 * 1024 * 1024:
            raise ValueError('每张图片须小于 10 MiB')
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest in hashes:
            raise ValueError('不能重复使用同一图片')
        with Image.open(io.BytesIO(data)) as im:
            fmt = im.format
            if fmt not in ('PNG', 'JPEG'):
                raise ValueError('贴图仅支持 PNG/JPEG')
            im.verify()
        with Image.open(io.BytesIO(data)) as im:
            im.load()
        hashes.add(digest)
        images.append({'data': data, 'sha256': digest, 'filename': 'picture.png' if fmt == 'PNG' else 'picture.jpg'})
    return images


def fingerprint(base_url, account, title, content, images):
    value = [base_url.rstrip('/'), account, title, content, [i['sha256'] for i in images]]
    return hashlib.sha256(json.dumps(value, ensure_ascii=False).encode()).hexdigest()


def save_receipt(path, state):
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.receipt-')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def checked(result):
    if not isinstance(result, dict) or result.get('errcode', 0) != 0 or result.get('ok') is False:
        # Do not print raw proxy errors, which may contain upstream credentials.
        code = result.get('errcode', 'proxy_error') if isinstance(result, dict) else 'invalid_response'
        raise RuntimeError(f'微信请求失败，错误码 {code}')
    return result


def verify_draft(api, base_url, token, account, media_id, title, content, image_ids):
    result = checked(api(base_url, token, '/wechat/draft/get', {'account': account, 'media_id': media_id}))
    items = result.get('news_item', [])
    if len(items) != 1:
        raise RuntimeError('草稿文章数量不匹配')
    article = items[0]
    actual_ids = [i.get('image_media_id') for i in article.get('image_info', {}).get('image_list', [])]
    if (article.get('article_type') != 'newspic' or article.get('title') != title
            or article.get('content') != content or actual_ids != image_ids):
        raise RuntimeError('草稿类型、标题、正文或图片顺序不匹配')
    return {'article_type': 'newspic', 'title': title, 'image_count': len(actual_ids), 'order_verified': True}


def publish(api, base_url, token, account, title, content, images, receipt):
    """A receipt identifies one intent. Known drafts only get read, never recreated."""
    receipt = Path(receipt)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    request_hash = fingerprint(base_url, account, title, content, images)
    lock = receipt.with_name(receipt.name + '.lock')
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise RuntimeError('该回执正在使用或上次进程中断；先核对回执和远程草稿，勿重复提交') from None
    os.close(fd)
    try:
        if receipt.exists():
            state = json.loads(receipt.read_text())
            if state.get('request_hash') != request_hash:
                raise ValueError('回执对应其他账号或内容，请勿复用')
            if not state.get('media_id'):
                raise RuntimeError('上次提交未完成或结果未知；先核对已上传素材及草稿，勿重复创建')
        else:
            state = {'request_hash': request_hash, 'account': account, 'status': 'uploading', 'image_media_ids': []}
            save_receipt(receipt, state)
            for im in images:
                result = checked(api(base_url, token, '/wechat/material/add_material', {
                    'account': account, 'type': 'image', 'filename': im['filename'],
                    'image_base64': base64.b64encode(im['data']).decode(),
                }))
                if not result.get('media_id'):
                    raise RuntimeError('上传图片未返回素材编号')
                state['image_media_ids'].append(result['media_id'])
                save_receipt(receipt, state)
            state['status'] = 'creating_or_unknown'
            save_receipt(receipt, state)
            article = {
                'article_type': 'newspic', 'title': title, 'content': content,
                'need_open_comment': 0, 'only_fans_can_comment': 0,
                'image_info': {'image_list': [{'image_media_id': mid} for mid in state['image_media_ids']]},
            }
            result = checked(api(base_url, token, '/wechat/draft/add', {'account': account, 'articles': [article]}))
            if not result.get('media_id'):
                raise RuntimeError('创建草稿未返回编号，结果未知；请先核对草稿箱')
            state.update(media_id=result['media_id'], status='created_unverified')
            save_receipt(receipt, state)
        summary = verify_draft(api, base_url, token, account, state['media_id'], title, content, state['image_media_ids'])
        state.update(status='verified', verification=summary)
        save_receipt(receipt, state)
        return state
    finally:
        lock.unlink()


def run(args, api):
    if not args.title or not args.content_file or not args.images:
        raise ValueError('--type newspic 需要 --title、--content-file、--images')
    content = Path(args.content_file).read_text(encoding='utf-8').strip()
    images = prepare(args.title, content, args.images)
    if args.dry_run:
        print(json.dumps({'dry_run': True, 'article_type': 'newspic', 'title': args.title,
                          'image_count': len(images), 'api_calls': 0}, ensure_ascii=False))
        return
    base_url = os.environ.get('WECHAT_MP_API_BASE_URL', '').rstrip('/')
    token = os.environ.get('WECHAT_MP_API_TOKEN', '')
    if not base_url or not token:
        raise ValueError('需要配置 WECHAT_MP_API_BASE_URL 和 WECHAT_MP_API_TOKEN')
    if not args.receipt:
        raise ValueError('真实推送必须指定 --receipt，用于核验和防止重复创建')
    state = publish(api, base_url, token, args.account, args.title, content, images, args.receipt)
    print(json.dumps(state, ensure_ascii=False, indent=2))
