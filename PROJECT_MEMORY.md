# Project memory

## 2026-09-15: Picture drafts

- Baseline: origin/main at 0d69a20. Branch codex/wechat-newspic.
- Added opt-in `publish.py --type newspic`; article mode stays the default.
- Validates every image before uploads; ordered permanent media are submitted in one picture draft and verified with draft/get.
- A durable receipt and exclusive lock prevent repeating the same intent. Unknown create results stop; known draft IDs only get read again. This is local receipt protection, not server-wide idempotency.
- No server changes or deployment required: the existing proxy forwards the article payload.
- Local validation: 12 unittest cases passed, Python compilation and Node syntax check passed; two existing PNG assets passed CLI dry-run with zero API calls.
- The user confirmed the target account alias before the live run. Live upload and draft/get passed: newspic type, exact title/content, two image IDs in the expected order. No public publish or broadcast was submitted. Browser preview was unavailable due to site-safety policy; API verification is complete, backend visual acceptance is not.
- Credentials stay in private env files; draft receipts and test media stay outside the repository.

## 2026-09-15: Buyer-held credentials (supersedes the earlier binding design)

- Buyers own their AppID/AppSecret and retain them in private local env files. Every call carries them in HTTPS headers to the shared fixed-IP service; no seller-side account provisioning/binding is required.
- Buyers add the documented server egress IP 8.153.207.214 to their own account whitelist. The previous operator default/account-name mapping is only a self-use test fact.
- Skill1.2.0 client defaults to request mode, strips account aliases, and verifies health credential_mode=request before sending credentials or writes. It requires HTTPS and refuses redirects. Receipts scope identity by hashed AppID.
- Server request mode accepts only current request credentials, ignores legacy account selection, uses stable_token without a local cross-request token/credential cache, and redacts credentials/tokens from responses. No file/database logging or storage of buyer secrets is added. Reverse-proxy/APM configuration must also exclude sensitive headers/bodies/upstream URLs before deployment.
- Existing legacy mode remains unchanged for older deployments. Buyer instructions prohibit falling back to legacy. Server request mode requires explicit WECHAT_CREDENTIAL_MODE=request; the provided server env template has this setting and contains no buyer credentials.
- Local verification: 19 Python cases and 6 Node HTTP integration cases pass, including concurrent buyer isolation, missing/invalid credentials, legacy-server refusal, redirect/HTTP refusal, explicit env account selection, and receipt recovery. Node uses mocked WeChat upstream, not real buyer accounts.
- The request-credential backend has NOT been deployed or live-tested. The earlier successful picture draft used the legacy operator service; it is not evidence for request-mode production operation. No additional draft, payment, or public publish was made.
