import test from 'node:test';
import assert from 'node:assert/strict';
import { once } from 'node:events';
import { createWechatServer } from '../api-server/server.mjs';

const idA = 'wx' + 'A'.repeat(16), idB = 'wx' + 'B'.repeat(16);
const secretA = 'a'.repeat(32), secretB = 'b'.repeat(32);
const response = (data) => new Response(JSON.stringify(data), { status: 200 });

async function setup(t, fetchImpl) {
  const server = createWechatServer({credentialMode:'request',apiToken:'service-access',fetchImpl});
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  t.after(() => new Promise(resolve => {server.close(resolve);server.closeAllConnections();}));
  const base = `http://127.0.0.1:${server.address().port}`;
  const call = (path, body, id=idA, secret=secretA) => fetch(base+path, {
    method:'POST', headers:{'Content-Type':'application/json', Authorization:'Bearer service-access',
      ...(id ? {'X-Wechat-Appid':id} : {}), ...(secret ? {'X-Wechat-Appsecret':secret} : {})},
    body:JSON.stringify(body),
  });
  return {base,call};
}

test('requires credentials every request, never falls back to default account', async t => {
  let calls=0;
  const {call,base}=await setup(t,async()=>{calls++;return response({access_token:'token'});});
  const health=await (await fetch(base+'/health')).json();
  assert.equal(health.credential_mode,'request');assert.equal(health.accounts,undefined);
  assert.equal((await call('/token/test',{account:'default'},null,null)).status,400);
  assert.equal((await call('/token/test',{})).status,200);
  assert.equal((await call('/token/test',{account:'default'},null,null)).status,400);
  assert.equal(calls,1);
});

test('two buyers remain isolated during concurrent requests, no cross-request token cache', async t => {
  const tokenCalls=[], draftCalls=[];
  const {call}=await setup(t, async (url,opts) => {
    if(url.endsWith('/stable_token')) {
      const body=JSON.parse(opts.body);tokenCalls.push(body);
      assert.equal(body.force_refresh,false);assert.ok(!url.includes('secret'));
      if(body.appid===idA) {assert.equal(body.secret,secretA);await new Promise(r=>setTimeout(r,10));}
      else assert.equal(body.secret,secretB);
      return response({access_token:body.appid===idA?'token-A':'token-B'});
    }
    const body=JSON.parse(opts.body);draftCalls.push({url,body});
    const expected=body.articles[0].title==='A'?'token-A':'token-B';
    assert.equal(new URL(url).searchParams.get('access_token'),expected);
    assert.equal(body.account,undefined);
    return response({media_id:'draft-'+expected});
  });
  const [a,b]=await Promise.all([
    call('/wechat/draft/add',{account:'other-buyer',articles:[{title:'A'}]},idA,secretA),
    call('/wechat/draft/add',{account:'default',articles:[{title:'B'}]},idB,secretB),
  ]);
  assert.equal(a.status,200);assert.equal(b.status,200);
  await call('/wechat/draft/add',{articles:[{title:'A'}]},idA,secretA);
  assert.equal(tokenCalls.length,3);assert.equal(draftCalls.length,3);
});

test('invalid buyer credentials never reach draft creation or reuse another buyer token', async t => {
  let drafts=0;
  const {call}=await setup(t,async(url)=>{
    if(url.endsWith('/stable_token')) return response({errcode:40013,errmsg:secretA});
    drafts++;return response({media_id:'bad'});
  });
  const r=await call('/wechat/draft/add',{articles:[]});
  const body=await r.text();
  assert.equal(r.status,500);assert.ok(body.includes('40013'));
  assert.ok(!body.includes(secretA));assert.equal(drafts,0);
});

test('request-mode errors and upstream echoes do not expose credentials or tokens', async t => {
  const {call}=await setup(t,async(url)=>{
    if(url.endsWith('/stable_token')) return response({access_token:'private-access-token'});
    return response({errcode:40007,errmsg:[idA,secretA,'private-access-token','service-access'].join(' ')});
  });
  const body=await (await call('/wechat/draft/get',{media_id:'unknown'})).text();
  for(const secret of [idA,secretA,'private-access-token','service-access']) assert.ok(!body.includes(secret));
  assert.ok(body.includes('40007'));
});

test('material uploads preserve local bytes and reject remote fetch inputs', async t => {
  let uploads=0;
  const {call}=await setup(t,async(url,opts)=>{
    if(url.endsWith('/stable_token')) return response({access_token:'token'});
    uploads++;
    assert.equal(new URL(url).pathname,'/cgi-bin/material/add_material');
    assert.equal(await opts.body.get('media').text(),'image bytes');
    return response({media_id:'picture'});
  });
  assert.equal((await call('/wechat/material/add_material',{image_base64:Buffer.from('image bytes').toString('base64'),filename:'1.png'})).status,200);
  assert.equal((await call('/wechat/material/add_material',{image_url:'http://127.0.0.1/private'})).status,500);
  assert.equal(uploads,1);
});

test('request mode refuses startup without service authorization',()=>{
  assert.throws(()=>createWechatServer({credentialMode:'request',apiToken:''}),/requires API_TOKEN/);
});


test('release symlink starts the actual HTTP server', async t => {
  const { mkdtemp, symlink, rm } = await import('node:fs/promises');
  const { tmpdir } = await import('node:os');
  const { join } = await import('node:path');
  const { fileURLToPath } = await import('node:url');
  const { spawn } = await import('node:child_process');
  const dir=await mkdtemp(join(tmpdir(),'wechat-release-'));
  t.after(()=>rm(dir,{recursive:true,force:true}));
  const link=join(dir,'current.mjs');
  await symlink(fileURLToPath(new URL('../api-server/server.mjs',import.meta.url)),link);
  const child=spawn(process.execPath,[link],{env:{...process.env,PORT:'0',API_TOKEN:'test',WECHAT_CREDENTIAL_MODE:'request'}});
  t.after(()=>child.kill());
  await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(new Error('server did not start')),3000);
    child.stdout.once('data',data=>{clearTimeout(timer);assert.match(String(data),/listening/);resolve();});
    child.once('exit',code=>{clearTimeout(timer);reject(new Error('exited before listening: '+code));});
  });
});
