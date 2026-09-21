# Runbook: Login loops and "unauthorized" errors

Symptoms: users are sent back to the login page repeatedly, API calls return 401/403, or data that should be visible appears empty.

## Common causes
- Row-level security (RLS) policy changed or was enabled on a table without a policy for the signed-in role, so queries return no rows or permission errors.
- JWT secret, auth redirect URL or site URL changed in the auth provider settings.
- Cookie domain or `SameSite` settings changed with a domain move (for example `www` to apex).
- Clock or token expiry misconfiguration makes tokens expire immediately.

## How to check
1. Look at the auth logs for the error codes around the first report.
2. Diff recent migrations for `create policy`, `alter policy`, or `enable row level security`.
3. Check recent changes to environment variables holding auth URLs or keys.

## Fix
- Add or correct the RLS policy for the affected role; test with that role before releasing.
- Restore the previous auth URL/secret configuration.
