# Project memory

## 2026-09-15: Picture drafts

- Baseline: origin/main at 0d69a20. Branch codex/wechat-newspic.
- Added opt-in `publish.py --type newspic`; article mode stays the default.
- Validates every image before uploads; ordered permanent media are submitted in one picture draft and verified with draft/get.
- A durable receipt and exclusive lock prevent repeating the same intent. Unknown create results stop; known draft IDs only get read again. This is local receipt protection, not server-wide idempotency.
- No server changes or deployment required: the existing proxy forwards the article payload.
- Local validation: 12 unittest cases passed, Python compilation and Node syntax check passed; two existing PNG assets passed CLI dry-run with zero API calls.
- Live draft push pending confirmation of the target account alias. Do not assume default identifies the requested account.
- Credentials stay in private env files; draft receipts and test media stay outside the repository.
