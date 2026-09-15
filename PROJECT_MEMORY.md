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

## 2026-09-15: Request-mode production acceptance completed

- Deployed a separate request-mode service at https://cs.qwjxqn.xyz/wechat-skill, port127.0.0.1:18891, processwechat-skill-api. Existing /wechat-mp body-credentials-v1 has extra unrelated endpoints; it was preserved unchanged.
- Server release39d8163, SHA256 fd8f3430432ad5f52aa07e75d78d4416473aa23b91dc4a7571ba43e6086f0e5f. Fixed release-symlink startup guard and tested on Node18.20.8 before enabling the new route.
- 13 public checks passed using operator-authorized local account credentials: connection, negative credentials/auth, image and cover uploads, downloaded image decode, article/picture create/update/readback, picture reorder. No publication, broadcast, payment, or extra draft retry.
- WeChat normalizes article image URLs to data-src and /640; smoke validation now compares media identity, covered by regression cases.
- 22 Python tests and 7 Node18 HTTP integration tests pass. PM2 state saved, original/new internal and public health pass; new process has no stored WeChat secret env.
- Reverse proxy disables request buffering/access logs for new route. Backup at /www/wwwroot/wechat-skill-api/backups/cs.qwjxqn.xyz.conf.before; rollback removes new route/process while preserving old service.
- Backend visual UI acceptance unavailable due browser site-safety restriction; real draft readback and returned image visual inspection completed. Independent image generation/layout extraction and payment were not exercised by this publishing-API smoke.

## 2026-09-15: Expanded layout and image-generation acceptance

- The user corrected the acceptance scope to include layout copying and real generation, not just the publishing API.
- Extracted layout from an authentic locally saved WeChat article (2026-07-03, title AI知识星球，自己会运营、会答疑、会进化). Source mostly relies on WeChat defaults; theme separates observed bold/paragraph/image structure from inferred font/spacing defaults. No fresh online article fetch or pixel-identical clone is claimed.
- Applied the inferred theme to newly written content. Desktop and390px mobile screenshots visually checked. Pushed 排版复刻实测｜新内容应用 to the confirmed self-use account; readback verified title,8paragraphs,2bold sections,inline emphasis,body style and image.
- Replaced regex Markdown rendering with Python Markdown and unified Markdown/HTML publishing through durable receipts. Local images are decoded before any write, uploaded and replaced by WeChat URLs. HTML sanitizes active content and converts code blocks. Markdown全流程实测 passed live title/heading/emphasis/table/image/code-compatible readback.
- Fixed automatic cover integration from obsolete api.evolink.io/synchronous z-image-turbo assumptions to api.evolink.ai async Nano Banana2. Durable receipts persist task ID, progress and usage; unknown submissions never auto-retry; downloaded results require complete image decoding. Local generator is bundled identically in both standalone image and publishing skills, checked by test.
- Local suite33Python cases and7Node integration cases pass. Generation success/failure/resume tests use mocked provider; they are NOT paid/live image generation evidence.
- BLOCKER: no usable EVOLINK_API_KEY found in the current environment or relevant local configs. Asked user for private env path. No paid generation submitted. Real generation, image editing/reference generation, and new-generated-image-to-draft acceptance remain outstanding. Do not declare all functions accepted or ready for sale.
- Evidence is outside Git at /Users/burning/Documents/workbuddy/outputs/wechat-full-workflow-20260915. Earlier publish-API live receipts remain in wechat-public-smoke-20260915. Browser policy still prevents WeChat backend UI acceptance; local previews and API readback are separate evidence.

## 2026-09-15: Agent-native illustration handoff supersedes EvoLink requirement

- User explicitly changed WeChat image scope: the Skill writes prompts and guides the user's current Agent to generate illustrations using its available tools. No fixed provider integration or image-provider Key is required.
- Removed the publishing package's EvoLink helper and automatic-cover call. Missing Markdown cover now returns needs_image, a prompt, ratio, target path and resume instruction (exit2, no upload/draft); --cover resumes with an Agent-generated local image. --cover-prompt is prompt text only.
- Added references/image-prompts.md for content-specific cover/body/picture prompts, placement/order, actual host capability discovery, local image retrieval and visual QA. If no image tool is available, deliver prompts and wait for real images; never claim a prompt or placeholder is an image.
- Buyer docs/env template no longer ask for image-provider credentials. The separate skills/evolink-nano-banana-2 remains an independent opt-in tool, outside the WeChat product dependency and acceptance scope.
- Previous missing EVOLINK_API_KEY blocker is obsolete for this product. No key or provider generation approval is needed to complete this change.
- Local34Python tests and7Node tests pass, including missing cover with a legacy provider key making no generation request, and Agent-supplied cover resuming without a provider key. No new images, paid generation or drafts were submitted; WorkBuddy/Doubao host-specific image generation has not been exercised in this test.

## 2026-09-15: Firefly Image2 fallback installation guidance

- User specified the no-image-capability fallback: guide installation of Image2生图【星元科技·Firefly·出品】, exact slug @user_34e6449f/xy-image2-1k.
- Verified official https://skillhub.cn/install/skillhub.md. Instructions require explicit --dir to the current Agent's actual skills directory; preserve host-specific discovery/reload requirements.
- Updated illustration reference, skill entrypoint, buyer README and needs_image CLI response with exact name, slug and installation guide. Once installed and discoverable, read its own SKILL.md and reuse the prepared prompts to continue.
- This changes the buyer guidance; it does not install Image2 in this development environment or trigger image generation/payment. Existing native generation remains the first choice.
