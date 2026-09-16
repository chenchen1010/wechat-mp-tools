"""Publish locally composed HTML with local images and a durable draft receipt."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import re
from bs4 import BeautifulSoup
from PIL import Image

ALLOWED = {'section','p','span','h1','h2','h3','h4','strong','b','em','i','u','s','a','img','br','hr','blockquote','ul','ol','li','table','thead','tbody','tr','th','td'}

def prepare_html(content, directory):
    """Sanitize active content, normalize code blocks and collect local image files."""
    soup = BeautifulSoup(content, 'html.parser')
    for el in soup.find_all(['script','style','iframe','object','embed','form','input','button','link','meta','head']): el.decompose()
    for el in soup.find_all(['pre','code']):
        el.name = 'section' if el.name == 'pre' else 'span'
        el['style'] = 'background-color:#f5f5f5;white-space:pre-wrap;line-height:1.7;'
    files = {}
    for el in list(soup.find_all(True)):
        if el.name not in ALLOWED: el.unwrap(); continue
        for attr in list(el.attrs):
            if attr not in ('style','href','src','data-src','alt','colspan','rowspan'): del el[attr]
        style = el.get('style', '')
        if re.search(r'url\s*\(|expression|@import|behavior|-moz-binding', style, re.I): del el['style']
        if el.name == 'a' and not re.match(r'^https://', el.get('href','')): el.attrs.pop('href',None)
        if el.name == 'img':
            source = el.get('data-src') or el.get('src', '')
            if source.startswith(('http://mmbiz.qpic.cn/', 'https://mmbiz.qpic.cn/')):
                source = source.replace('http://','https://',1)
            else:
                if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', source) or source.startswith('//'):
                    raise ValueError('Download generated/reference images locally before publishing')
                path = (Path(directory) / source).resolve()
                if not path.is_file(): raise ValueError('Local article image is missing: ' + path.name)
                if path.stat().st_size > 10 * 1024 * 1024: raise ValueError('Article image too large')
                with Image.open(path) as im:
                    if im.format not in ('PNG','JPEG'): raise ValueError('Use PNG/JPEG images')
                    im.load()
                files[source] = path
            el['src'] = source; el['data-src'] = source
            el['class'] = ['rich_pages','wxw-img']
            el['style'] = 'display:block;width:100%;height:auto !important;'
    return soup, files

def run(args, publisher):
    from newspic import save_receipt, checked
    if not args.title.strip(): raise ValueError('Article title is required')
    html_path = Path(args.html).resolve()
    soup, files = prepare_html(html_path.read_text(), html_path.parent)
    cover = Path(args.cover).resolve()
    with Image.open(cover) as im: im.load()
    base = os.environ['WECHAT_MP_API_BASE_URL']; token = os.environ.get('WECHAT_MP_API_TOKEN', '')
    intent = {'html':str(soup), 'title':args.title, 'author':args.author, 'account':args.account,
              'base':base, 'cover':hashlib.sha256(cover.read_bytes()).hexdigest(),
              'images':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in files.items()}}
    fingerprint = hashlib.sha256(json.dumps(intent,sort_keys=True).encode()).hexdigest()
    receipt = Path(args.receipt).resolve(); receipt.parent.mkdir(parents=True,exist_ok=True)
    lock = receipt.with_suffix('.lock'); fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
    try:
        state = json.loads(receipt.read_text()) if receipt.exists() else {'fingerprint':fingerprint,'results':{}}
        if state['fingerprint'] != fingerprint: raise ValueError('Receipt belongs to another article')
        if state.get('inflight'): raise RuntimeError('Previous write outcome unknown; inspect receipt before resubmitting')
        def mutation(name, fn):
            if name not in state['results']:
                state['inflight']=name;save_receipt(receipt,state)
                state['results'][name]=fn();state.pop('inflight');save_receipt(receipt,state)
            return state['results'][name]
        for source,path in files.items():
            url=mutation('image:'+source,lambda p=path:publisher.upload_body_image(base,token,args.account,p))
            for el in soup.find_all('img'):
                if el.get('src')==source: el['src']=url;el['data-src']=url
        thumb=mutation('cover',lambda:publisher.upload_cover(base,token,args.account,cover))
        content=str(soup)
        payload={'article_type':'news','title':args.title,'author':args.author,'content':content,
                 'thumb_media_id':thumb,'need_open_comment':1,'only_fans_can_comment':0}
        created=mutation('draft',lambda:publisher.create_draft(base,token,args.account,payload))
        result=checked(publisher.api_post(base,token,'/wechat/draft/get',{'media_id':created['media_id']}))
        got=result['news_item'][0];returned=BeautifulSoup(got['content'],'html.parser')
        expected=[x.get('data-src') or x.get('src') for x in soup.find_all('img')]
        actual=[x.get('data-src') or x.get('src') for x in returned.find_all('img')]
        def identity(url):return re.sub(r'/[0-9]+(?:\?.*)?$', '',url.replace('http://','https://'))
        if got['title']!=args.title or list(map(identity,expected))!=list(map(identity,actual)):
            raise RuntimeError('Draft readback does not match article')
        for text in soup.stripped_strings:
            if text not in returned.get_text(): raise RuntimeError('Article text missing from readback')
        state.update(status='verified',media_id=created['media_id'],image_count=len(actual))
        save_receipt(receipt,state)
        receipt.with_suffix('.readback.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
        receipt.with_suffix('.submitted.html').write_text(content)
        print(json.dumps({'status':state['status'],'media_id':state['media_id'],'image_count':len(actual)},ensure_ascii=False))
        return state
    finally: lock.unlink()
