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

## 2026-09-15: Third-party buyer onboarding

- Product intent is third-party sales. Buyers share the seller server egress IP (documented as 8.153.207.214), and must add it to their own Official Account IP whitelist and bind their own account.
- The previous default-to-account-name mapping was confirmed by the operator for a self-use test only. It is not a product-wide mapping or a buyer default.
- Skill 1.1.1 removes seller-specific local env paths and production endpoint defaults from buyer onboarding. CLI now requires explicit account or WECHAT_MP_API_ACCOUNT_DEFAULT from buyer config; it does not silently select default.
- Existing server uses one process-wide API_TOKEN with static account aliases, not buyer-scoped authorization. No new backend tenancy or automatic purchase/binding service has been implemented or deployed. Dedicated buyer instances on the same egress IP are one supported deployment model; a shared multi-buyer service needs server-side authorization binding before sale.
- Validation: 14 unittests pass, including missing-account refusal and buyer env/explicit account selection; Python compilation and diff check pass. Existing live picture-draft test is unchanged; no additional draft created in this change.
