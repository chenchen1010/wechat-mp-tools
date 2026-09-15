#!/usr/bin/env python3
"""Explicit live acceptance. Creates two test drafts; never publishes/broadcasts."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/publish/wechat-article'))
import publish
import newspic


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--images', nargs=2, required=True)
    parser.add_argument('--run-live', action='store_true', required=True)
    args=parser.parse_args()
    publish.load_env(Path(args.env_file))
    os.environ['WECHAT_MP_CREDENTIAL_MODE']='request'
    appid, _=publish.request_credentials()
    base=os.environ['WECHAT_MP_API_BASE_URL'].rstrip('/')
    token=os.environ['WECHAT_MP_API_TOKEN']
    out=Path(args.output).resolve();out.mkdir(parents=True,exist_ok=True)
    paths=[Path(x).resolve() for x in args.images]
    images=newspic.prepare('公网贴图实测', '公网贴图测试：两张图片按输入顺序展示。',paths)
    run_hash=newspic.fingerprint(base,appid,'public-smoke-v1','',images)
    record=out/'smoke-receipt.json'
    state=json.loads(record.read_text()) if record.exists() else {'request_hash':run_hash,'checks':{},'results':{}}
    if state['request_hash'] != run_hash: raise RuntimeError('Output belongs to another account or input')
    if state.get('inflight'): raise RuntimeError('Previous mutation outcome requires inspection: '+state['inflight'])
    lock=out/'smoke.lock'
    fd=os.open(lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.close(fd)
    def save():newspic.save_receipt(record,state)
    def check(name,value=True):
        if not value: raise RuntimeError('Check failed: '+name)
        state['checks'][name]=True;save();print('PASS '+name,flush=True)
    def call(endpoint,body):return newspic.checked(publish.api_post(base,token,endpoint,body))
    def mutation(name,fn):
        if name in state['results']: return state['results'][name]
        state['inflight']=name;save()
        value=fn()
        state['results'][name]=value;state.pop('inflight');save()
        return value
    def get_draft(mid):
        data=call('/wechat/draft/get',{'media_id':mid})
        if len(data.get('news_item',[])) != 1:raise RuntimeError('Unexpected article count')
        return data['news_item'][0]
    def download_image(url,path):
        if url.startswith('http://mmbiz.qpic.cn/'):url='https://'+url[7:]
        if not url.startswith('https://mmbiz.qpic.cn/'):raise RuntimeError('Unexpected WeChat media host')
        with urllib.request.urlopen(url,timeout=30) as response:data=response.read()
        with Image.open(io.BytesIO(data)) as im:im.load();size=im.size
        path.write_bytes(data)
        return {'file':path.name,'dimensions':list(size),'sha256':hashlib.sha256(data).hexdigest()}
    try:
        check('token_connection',call('/token/test',{}).get('ok') is True)
        # Negative cases are read-only and never carry genuine WeChat credentials.
        for name,extra in [('missing_credentials',{}),('invalid_credentials',{'X-Wechat-Appid':'wx'+'0'*16,'X-Wechat-Appsecret':'0'*32})]:
            req=urllib.request.Request(base+'/token/test',data=b'{}',method='POST',headers={'Authorization':'Bearer '+token,'Content-Type':'application/json',**extra})
            try:
                with urllib.request.build_opener(publish.NoRedirect()).open(req,timeout=30) as resp:result=json.load(resp)
            except urllib.error.HTTPError as exc:result=json.load(exc)
            check(name+'_rejected',result.get('ok') is False or bool(result.get('errcode')))
        body=mutation('body_upload',lambda: {'url':publish.upload_body_image(base,token,'',paths[0])})
        cover=mutation('cover_upload',lambda: {'media_id':publish.upload_cover(base,token,'',paths[0])})
        check('body_upload',bool(body['url']));check('permanent_material_upload',bool(cover['media_id']))
        state['body_image']=download_image(body['url'],out/'body-returned.png');check('body_image_decodes')
        content='<section><h2>公网文章实测</h2><p>用于验证本地凭证、固定IP上传和文章草稿。</p><section style="text-align:center;"><img class="rich_pages wxw-img" src="'+body['url']+'" data-src="'+body['url']+'" style="display:block;width:100%;height:auto !important;"/></section></section>'
        article={'article_type':'news','title':'公网文章实测｜燃烧青年','author':'燃烧青年','content':content,'thumb_media_id':cover['media_id'],'need_open_comment':0,'only_fans_can_comment':0}
        created=mutation('article_create',lambda: publish.create_draft(base,token,'',article))
        got=get_draft(created['media_id'])
        if 'article_update' not in state['results']:check('article_create_readback',got['title']==article['title'] and body['url'] in got['content'])
        changed={**article,'title':'公网文章实测｜已更新','content':content+'<p>草稿更新验证完成。</p>'}
        mutation('article_update',lambda: call('/wechat/draft/update',{'media_id':created['media_id'],'index':0,'articles':changed}))
        got=get_draft(created['media_id']);check('article_update_readback',got['title']==changed['title'] and '草稿更新验证完成' in got['content'] and got['content'].count('<img')==1)
        check('article_editor_compatibility',not any(x in got['content'] for x in ['<pre','<code','code-snippet','js_img_error','上传失败']))
        # The picture publisher owns its durable receipt; use it for all retries.
        pic_receipt=out/'picture-receipt.json'
        if 'picture_created' not in state['results']:
            pic=newspic.publish(publish.api_post,base,token,'appid-sha256:'+hashlib.sha256(appid.encode()).hexdigest(),'公网贴图实测','公网贴图测试：两张图片按输入顺序展示。',images,pic_receipt)
            state['results']['picture_created']=pic;save()
        pic=state['results']['picture_created'];check('picture_create_readback',pic['status']=='verified')
        updated_ids=list(reversed(pic['image_media_ids']))
        changed_pic={'article_type':'newspic','title':'公网贴图实测｜已更新','content':'更新验证：两张图片顺序已交换。','need_open_comment':0,'only_fans_can_comment':0,'image_info':{'image_list':[{'image_media_id':mid} for mid in updated_ids]}}
        mutation('picture_update',lambda: call('/wechat/draft/update',{'media_id':pic['media_id'],'index':0,'articles':changed_pic}))
        newspic.verify_draft(publish.api_post,base,token,'',pic['media_id'],changed_pic['title'],changed_pic['content'],updated_ids)
        check('picture_update_and_order_readback')
        state['status']='verified';save()
    finally:lock.unlink()

if __name__=='__main__':
    try:main()
    except Exception as error:
        # Never dump transport exceptions / credential-bearing URLs or headers.
        print('PUBLIC SMOKE STOPPED: '+type(error).__name__+'; inspect durable receipt, do not repeat uncertain mutations.',file=sys.stderr)
        sys.exit(1)
