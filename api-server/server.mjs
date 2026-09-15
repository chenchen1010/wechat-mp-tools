#!/usr/bin/env node
import http from 'node:http';
import { URL } from 'node:url';
import { Buffer } from 'node:buffer';
import { pathToFileURL } from 'node:url';

export function createWechatServer({ credentialMode = process.env.WECHAT_CREDENTIAL_MODE || 'legacy', apiToken = process.env.API_TOKEN || '', fetchImpl = globalThis.fetch } = {}) {
const API_TOKEN = apiToken;
const REQUEST_CREDENTIALS = credentialMode === 'request';
if (!['legacy', 'request'].includes(credentialMode)) throw new Error('invalid credential mode');
if (REQUEST_CREDENTIALS && !API_TOKEN) throw new Error('request mode requires API_TOKEN');
const fetch = fetchImpl;
const TOKEN_SKEW_MS = 60_000;
const BODY_LIMIT = 30 * 1024 * 1024;

const ACCOUNTS = REQUEST_CREDENTIALS ? {} : {
  default: {
    appId: process.env.WECHAT_APP_ID || '',
    appSecret: process.env.WECHAT_APP_SECRET || '',
  },
  qwjxqn: {
    appId: process.env.WECHAT_APP_ID_QWJXQN || '',
    appSecret: process.env.WECHAT_APP_SECRET_QWJXQN || '',
  },
  jscxbwd: {
    appId: process.env.WECHAT_APP_ID_JSCXBWD || '',
    appSecret: process.env.WECHAT_APP_SECRET_JSCXBWD || '',
  },
};

const tokenCache = new Map();

function json(res, status, payload) {
  let serialized = JSON.stringify(payload, null, 2);
  if (REQUEST_CREDENTIALS) {
    for (const value of [API_TOKEN, ...Object.values(res.requestCredentials || {})]) {
      if (value) serialized = serialized.split(value).join('[redacted]');
    }
  }
  const data = Buffer.from(serialized, 'utf8');
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': String(data.length),
  });
  res.end(data);
}

function sanitizeFilename(name = 'upload.bin', fallbackExt = '.bin') {
  const raw = String(name || '').trim() || `upload${fallbackExt}`;
  const extMatch = raw.match(/(\.[a-zA-Z0-9]+)$/);
  const ext = extMatch ? extMatch[1].toLowerCase() : fallbackExt;
  return `upload${ext}`;
}

function parseJsonBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    let total = 0;
    req.on('data', (chunk) => {
      total += chunk.length;
      if (total > BODY_LIMIT) {
        reject(new Error('request body too large'));
        req.destroy();
        return;
      }
      chunks.push(chunk);
    });
    req.on('end', () => {
      try {
        const text = Buffer.concat(chunks).toString('utf8').trim();
        resolve(text ? JSON.parse(text) : {});
      } catch (err) {
        reject(err);
      }
    });
    req.on('error', reject);
  });
}

function requireAuth(req) {
  if (!API_TOKEN) return true;
  const auth = req.headers.authorization || '';
  const token = auth.startsWith('Bearer ') ? auth.slice(7).trim() : '';
  return token && token === API_TOKEN;
}

function getAccount(name = 'default') {
  const key = String(name || 'default').trim().toLowerCase();
  const account = ACCOUNTS[key];
  if (!account || !account.appId || !account.appSecret) {
    throw new Error(`account not configured: ${key}`);
  }
  return { key, ...account };
}

async function fetchJson(url, options = {}) {
  const resp = await fetch(url, options);
  const text = await resp.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    throw new Error(`non-json response from upstream (${resp.status}): ${text.slice(0, 500)}`);
  }
  return { status: resp.status, data };
}

async function getAccessToken(accountName = 'default') {
  if (REQUEST_CREDENTIALS) {
    // Only the current request's headers supply credentials. No account lookup/cache.
    const { appId, appSecret } = accountName;
    const { status, data } = await fetchJson('https://api.weixin.qq.com/cgi-bin/stable_token', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ grant_type: 'client_credential', appid: appId, secret: appSecret, force_refresh: false }),
    });
    if (status !== 200 || data.errcode || !data.access_token) {
      const error = new Error('WeChat authentication failed');
      error.wechatCode = Number.isInteger(data.errcode) ? data.errcode : undefined;
      throw error;
    }
    accountName.accessToken = data.access_token;
    return data.access_token;
  }
  const { key, appId, appSecret } = getAccount(accountName);
  const cached = tokenCache.get(key);
  if (cached && cached.expiresAt > Date.now() + TOKEN_SKEW_MS) {
    return cached.token;
  }

  const url = new URL('https://api.weixin.qq.com/cgi-bin/token');
  url.searchParams.set('grant_type', 'client_credential');
  url.searchParams.set('appid', appId);
  url.searchParams.set('secret', appSecret);

  const { data } = await fetchJson(url.toString());
  if (data.errcode) {
    throw new Error(`get access token failed: ${JSON.stringify(data)}`);
  }
  if (!data.access_token) {
    throw new Error(`access_token missing: ${JSON.stringify(data)}`);
  }

  tokenCache.set(key, {
    token: data.access_token,
    expiresAt: Date.now() + (Number(data.expires_in || 7200) * 1000),
  });
  return data.access_token;
}

async function loadBinaryInput({ filename, image_base64, file_base64, image_url, file_url }) {
  const finalName = sanitizeFilename(filename || 'upload.bin');
  const b64 = image_base64 || file_base64;
  const remoteUrl = image_url || file_url;

  if (b64) {
    const base64Text = String(b64).replace(/^data:[^;]+;base64,/, '');
    return { filename: finalName, buffer: Buffer.from(base64Text, 'base64') };
  }

  if (remoteUrl) {
    if (REQUEST_CREDENTIALS) throw new Error('request mode requires local image bytes');
    const resp = await fetch(String(remoteUrl));
    if (!resp.ok) {
      throw new Error(`download failed: ${resp.status} ${resp.statusText}`);
    }
    const arrayBuffer = await resp.arrayBuffer();
    return { filename: finalName, buffer: Buffer.from(arrayBuffer) };
  }

  throw new Error('missing image/file input');
}

async function uploadWechatFile({ account, endpoint, query = {}, input }) {
  const accessToken = await getAccessToken(account);
  const { filename, buffer } = await loadBinaryInput(input);

  const url = new URL(`https://api.weixin.qq.com${endpoint}`);
  url.searchParams.set('access_token', accessToken);
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v));
  }

  const form = new FormData();
  form.append('media', new Blob([buffer]), filename);

  const { data } = await fetchJson(url.toString(), {
    method: 'POST',
    body: form,
  });
  return data;
}

async function handleDraftAdd(body) {
  const account = body.account || 'default';
  const accessToken = await getAccessToken(account);
  const payload = body.articles ? { articles: body.articles } : { articles: [body.article] };
  const { data } = await fetchJson(`https://api.weixin.qq.com/cgi-bin/draft/add?access_token=${encodeURIComponent(accessToken)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return data;
}

async function handleDraftUpdate(body) {
  const account = body.account || 'default';
  const accessToken = await getAccessToken(account);
  const payload = body.payload || {
    media_id: body.media_id,
    index: body.index ?? 0,
    articles: body.articles || body.article,
  };
  const { data } = await fetchJson(`https://api.weixin.qq.com/cgi-bin/draft/update?access_token=${encodeURIComponent(accessToken)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return data;
}

async function handleDraftGet(body) {
  const account = body.account || 'default';
  const accessToken = await getAccessToken(account);
  const payload = { media_id: body.media_id };
  const { data } = await fetchJson(`https://api.weixin.qq.com/cgi-bin/draft/get?access_token=${encodeURIComponent(accessToken)}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  return data;
}

function availableAccounts() {
  return Object.entries(ACCOUNTS)
    .filter(([, value]) => value.appId && value.appSecret)
    .map(([name]) => name);
}

const server = http.createServer(async (req, res) => {
  try {
    const url = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);

    if (req.method === 'GET' && url.pathname === '/health') {
      return json(res, 200, {
        ok: true,
        service: 'wechat-mp-api',
        credential_mode: credentialMode,
        ...(REQUEST_CREDENTIALS ? {} : { accounts: availableAccounts() }),
        now: new Date().toISOString(),
      });
    }

    if (!requireAuth(req)) {
      return json(res, 401, { ok: false, error: 'unauthorized' });
    }

    if (req.method !== 'POST') {
      return json(res, 405, { ok: false, error: 'method not allowed' });
    }

    // Validate before reading/uploads; ignore any client-supplied legacy account alias.
    let credentials;
    if (REQUEST_CREDENTIALS) {
      const appId = req.headers['x-wechat-appid'];
      const appSecret = req.headers['x-wechat-appsecret'];
      if (typeof appId !== 'string' || !/^wx[a-zA-Z0-9]{16}$/.test(appId)
          || typeof appSecret !== 'string' || !/^[a-zA-Z0-9]{32}$/.test(appSecret)) {
        return json(res, 400, { ok: false, error: 'valid WeChat credentials required on every request' });
      }
      credentials = { appId, appSecret };
      res.requestCredentials = credentials;
    }
    const body = await parseJsonBody(req);
    if (REQUEST_CREDENTIALS) body.account = credentials;

    if (url.pathname === '/token/test') {
      const account = body.account || 'default';
      await getAccessToken(account);
      return json(res, 200, { ok: true, ...(REQUEST_CREDENTIALS ? {} : { account }), message: 'token ok' });
    }

    if (url.pathname === '/wechat/media/uploadimg') {
      const data = await uploadWechatFile({
        account: body.account || 'default',
        endpoint: '/cgi-bin/media/uploadimg',
        input: body,
      });
      return json(res, 200, data);
    }

    if (url.pathname === '/wechat/material/add_material') {
      const data = await uploadWechatFile({
        account: body.account || 'default',
        endpoint: '/cgi-bin/material/add_material',
        query: { type: body.type || 'image' },
        input: body,
      });
      return json(res, 200, data);
    }

    if (url.pathname === '/wechat/draft/add') {
      const data = await handleDraftAdd(body);
      return json(res, 200, data);
    }

    if (url.pathname === '/wechat/draft/update') {
      const data = await handleDraftUpdate(body);
      return json(res, 200, data);
    }

    if (url.pathname === '/wechat/draft/get') {
      const data = await handleDraftGet(body);
      return json(res, 200, data);
    }

    return json(res, 404, { ok: false, error: 'not found' });
  } catch (err) {
    return json(res, 500, {
      ok: false,
      error: REQUEST_CREDENTIALS ? 'WeChat proxy request failed' : (err?.message || String(err)),
      ...(REQUEST_CREDENTIALS && Number.isInteger(err?.wechatCode) ? { errcode: err.wechatCode } : {}),
    });
  }
});

return server;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const PORT = Number(process.env.PORT || 18890);
  const server = createWechatServer();
  server.listen(PORT, '127.0.0.1', () => {
    console.log(`[wechat-mp-api] listening on 127.0.0.1:${PORT}`);
  });
}
