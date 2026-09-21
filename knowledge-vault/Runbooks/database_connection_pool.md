# Runbook: Database connection pool exhaustion

Symptoms: API requests slow down sharply (p95 from ~100 ms to several seconds), then start failing with timeouts or HTTP 500. Logs show `remaining connection slots are reserved`, `too many clients already`, `timeout acquiring connection`, or `pool timeout`.

## Common causes
- A deploy lowered the pool size (`DB_POOL_MAX`, `pool_size`, `max_connections`) or raised it above the database limit.
- A new code path opens connections without releasing them (missing `finally`/`close`, long transactions).
- A slow query holds connections for seconds, so the pool drains under normal traffic.
- Serverless functions each open their own connections instead of using the pooler (Supabase: use the pooler URL, port 6543 transaction mode, for serverless).

## How to check
1. Compare the time errors started with the last deploy; diff the configuration files touched by that deploy.
2. Look at active connections by state (`select state, count(*) from pg_stat_activity group by state`).
3. Look for long-running queries or idle-in-transaction sessions.
4. Check the database advisors for missing indexes on the tables used by the failing endpoint.

## Fix
- Restore the previous pool size, or roll back the deploy.
- Kill idle-in-transaction sessions older than a few minutes.
- Add the missing index or fix the connection leak; keep the pool size at or below 80% of the database connection limit.
