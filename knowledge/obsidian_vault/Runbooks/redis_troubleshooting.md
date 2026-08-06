# Runbook: Redis Cache Troubleshooting & Latency Spikes

This document outlines diagnostic steps when the Checkout or API gateway reports high latency or redis timeout logs.

## Troubleshooting Steps

1. **Check log signatures:**
   - Look for error messages matching: `Redis connection timed out` or `dial tcp: i/o timeout`.
   
2. **Review Deployment History:**
   - Verify if any recent pull request has changed the Redis client configuration (e.g., changes to connection limits, timeouts, or TLS options).
   
3. **Verify Network Paths:**
   - Ensure the security group for the API container allows outbound traffic to TCP 6379 on `redis.internal.net`.
   - Verify VPC routing rules between the application subnet and cache subnet.

4. **Remediation Commands:**
   - If a bad config was deployed, roll back the container to the last stable tag:
     ```bash
     kubectl rollout undo deployment/checkout-service -n production
     ```
   - Restart the Redis cluster or clear stale client connections if Redis CPU is saturated.
