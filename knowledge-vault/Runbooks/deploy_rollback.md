# Runbook: Deciding whether to roll back a deploy

Use when a problem starts within about 30 minutes of a deploy.

## Evidence that points to the deploy
- The first error or latency rise happens after the deploy finished, not before.
- The failing endpoint, page or query is touched by files changed in the deploy.
- Error stack traces point to files or functions changed in the deploy's commits.
- The same release/version tag appears on the new errors in the error tracker.

## Evidence against
- The problem started before the deploy, or on services the deploy did not touch.
- Third-party status pages report an outage at the same time.
- A content change (CMS publish) or a data migration happened in the same window.

## Rolling back
- Frontend hosts (Cloudflare Pages, Vercel, Netlify): promote the previous successful deployment from the dashboard; no rebuild needed.
- Revert the offending commit on the main branch afterwards so the next deploy does not bring it back.
- Record the deploy id, commit and time of rollback in the incident notes.
