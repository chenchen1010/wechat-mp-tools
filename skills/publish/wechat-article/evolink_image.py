#!/usr/bin/env python3
"""EvoLink async image generation with a durable, resumable local receipt."""
from __future__ import annotations
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import time
import urllib.request
from PIL import Image

API = 'https://api.evolink.ai/v1'
MODEL = 'gemini-3.1-flash-image-preview'

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise RuntimeError('EvoLink redirect refused')

def request(key, method, path, body=None):
    req = urllib.request.Request(API + path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization': 'Bearer ' + key, 'Content-Type': 'application/json'})
    try:
        with urllib.request.build_opener(NoRedirect()).open(req, timeout=60) as resp:
            result = json.load(resp)
    except Exception as exc:
        # Do not log raw upstream errors or authorization headers.
        raise RuntimeError('EvoLink request failed: ' + type(exc).__name__) from None
    if not isinstance(result, dict) or result.get('error'):
        raise RuntimeError('EvoLink returned a business error; inspect the provider task history')
    return json.loads(json.dumps(result).replace(key, '[redacted]'))

def save(path, state):
    tmp = path.with_suffix(path.suffix + '.tmp')
    with os.fdopen(os.open(tmp, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600), 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)

def generate(key, prompt, output, *, receipt=None, size='16:9', quality='1K',
             model=MODEL, image_urls=None, poll=True, max_polls=75, api=request):
    if not key: raise ValueError('EVOLINK_API_KEY is required')
    if not prompt.strip(): raise ValueError('Prompt is required')
    if quality not in ('0.5K', '1K', '2K', '4K'): raise ValueError('Invalid quality')
    if not re.fullmatch(r'(auto|[1-9][0-9]*:[1-9][0-9]*)', size): raise ValueError('Use a ratio such as 16:9')
    refs = image_urls or []
    if len(refs) > 14 or any(not u.startswith('https://') for u in refs): raise ValueError('Use up to 14 HTTPS reference URLs')
    output = Path(output).resolve(); output.parent.mkdir(parents=True, exist_ok=True)
    receipt = Path(receipt).resolve() if receipt else output.with_suffix('.generation.json')
    receipt.parent.mkdir(parents=True, exist_ok=True)
    body = {'model': model, 'prompt': prompt, 'size': size, 'quality': quality, 'n': 1}
    if refs: body['image_urls'] = refs
    fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
    lock = receipt.with_suffix(receipt.suffix + '.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600); os.close(fd)
    try:
        state = json.loads(receipt.read_text()) if receipt.exists() else {'fingerprint': fingerprint, 'status': 'new'}
        if state['fingerprint'] != fingerprint: raise ValueError('Receipt belongs to different image parameters')
        if state.get('status') == 'downloaded' and output.exists():
            if hashlib.sha256(output.read_bytes()).hexdigest() != state['sha256']: raise ValueError('Image changed since receipt')
            return state
        if not state.get('task_id'):
            if state['status'] != 'new': raise RuntimeError('Previous submission outcome unknown; do not resubmit')
            state['status'] = 'submitting'; save(receipt, state)
            result = api(key, 'POST', '/images/generations', body)
            task_id = result.get('id') or result.get('task_id')
            if not isinstance(task_id, str) or not re.fullmatch(r'[a-zA-Z0-9_-]+', task_id):
                raise RuntimeError('No valid task ID; do not resubmit')
            state.update(task_id=task_id, status=result.get('status', 'pending'), model=model,
                         usage_reserved=result.get('usage'), output=str(output),
                         results=result.get('results') or result.get('result_data')); save(receipt, state)
        if not poll: return state
        if state['status'] == 'failed': raise RuntimeError('Generation failed; no automatic retry')
        for _ in range(max_polls):
            if state['status'] == 'completed': break
            result = api(key, 'GET', '/tasks/' + state['task_id'])
            if result.get('id', state['task_id']) != state['task_id']: raise RuntimeError('Task identity mismatch')
            state.update(status=result.get('status', 'unknown'), progress=result.get('progress'),
                         usage=result.get('usage'), results=result.get('results') or result.get('result_data'))
            save(receipt, state)
            if state['status'] == 'failed': raise RuntimeError('Generation failed; no automatic retry')
            if state['status'] == 'completed': break
            if state['status'] not in ('pending', 'processing'): raise RuntimeError('Unknown generation status')
            time.sleep(4)
        if state['status'] != 'completed': raise RuntimeError('Generation still running; resume with the same receipt')
        results = state.get('results') or []
        url = results[0].get('url') if results and isinstance(results[0], dict) else (results[0] if results else '')
        if not isinstance(url, str) or not url.startswith('https://'): raise RuntimeError('No HTTPS image result')
        # Generated media downloads never carry the provider credential.
        with urllib.request.urlopen(url, timeout=60) as resp: data = resp.read(30 * 1024 * 1024 + 1)
        if len(data) > 30 * 1024 * 1024: raise RuntimeError('Generated image exceeds 30 MiB')
        with Image.open(io.BytesIO(data)) as im:
            im.load(); dimensions = list(im.size)
            im.convert('RGB').save(output, format='PNG')
        state.update(status='downloaded', dimensions=dimensions, sha256=hashlib.sha256(output.read_bytes()).hexdigest())
        save(receipt, state)
        return state
    finally:
        lock.unlink()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('prompt'); p.add_argument('--output', required=True)
    p.add_argument('--receipt'); p.add_argument('--model', default=MODEL)
    p.add_argument('--size', default='1:1'); p.add_argument('--quality', default='1K')
    p.add_argument('--n', type=int, choices=[1], default=1, help='One paid task per durable receipt')
    p.add_argument('--image', action='append', default=[])
    p.add_argument('--poll', action='store_true'); p.add_argument('--no-poll', action='store_true')
    a = p.parse_args()
    try:
        result = generate(os.environ.get('EVOLINK_API_KEY', ''), a.prompt, a.output,
                          receipt=a.receipt, size=a.size, quality=a.quality, model=a.model,
                          image_urls=a.image, poll=not a.no_poll)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, RuntimeError, OSError) as exc:
        p.exit(1, str(exc) + '\n')

if __name__ == '__main__': main()
