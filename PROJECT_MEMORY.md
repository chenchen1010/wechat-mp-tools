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
