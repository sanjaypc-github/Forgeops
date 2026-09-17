# Checkout Service API Specification

The Checkout Service processes all cart payments and purchases. It is a critical path service.

## Caching Strategy
- In order to meet <200ms latency SLA, the Checkout Service leverages a local Redis cache to cache product listings, stock counts, and temporary campaign configs.
- **Redis Connection Details:**
  - Hostname: `redis.internal.net`
  - Port: `6379`
  - Connection Pool Timeout: `3000ms`
  - Keep-alive: `true`

## Database Fallback Mechanism
- If the Redis connection drops, times out, or throws error packets, the service will attempt to fetch data directly from the PostgreSQL instance (`db-primary.internal.net`).
- **Warning:** A high volume of traffic directly to PostgreSQL can cause connection pool exhaustion, increasing response times from ~50ms to >5000ms, and eventually returning HTTP 500 errors to callers.
