# Runbook: Broken or stale pages after a frontend deploy (CDN cache)

Symptoms: right after a deploy some users see a blank page, a "ChunkLoadError", `Failed to fetch dynamically imported module`, missing styles, or the old version of the site; others are fine.

## Common causes
- HTML is cached at the edge while the JavaScript/CSS files it references were renamed by the new build (hashed filenames), so old HTML points to files that no longer exist.
- A cache rule or `Cache-Control` header change made HTML cacheable for too long.
- A redirect or header rule added in the hosting dashboard (Cloudflare Pages `_headers`/`_redirects`, Vercel `vercel.json`, Netlify `netlify.toml`) catches asset paths.

## How to check
1. Find the deployment that went live just before the first error and what configuration files it changed.
2. Check the response headers of the HTML page and one asset (`cf-cache-status`, `age`, `cache-control`).
3. Look for 404s on `/assets/*` or `/_next/static/*` in edge logs.

## Fix
- Purge the CDN cache for HTML (or everything) after the deploy.
- Serve HTML with `Cache-Control: no-cache` and long-cache only hashed assets.
- Revert the redirect/header rule that captures asset paths.
