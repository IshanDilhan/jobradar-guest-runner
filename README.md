# Guest job discovery runner

Small public runner for a private personal job-alert service. Dispatched every five
minutes by a Cloudflare Worker using workflow_dispatch. No public schedule; the
Worker manages dispatch timing, lease-based deduplication and source backoff.

No paid services, caches or artifacts. GitHub schedules can be delayed or dropped;
detection within five minutes is not guaranteed. Public workflow_dispatch runs use
standard GitHub-hosted Ubuntu runners (no private-repository minute limits).

Contains only the HTTP fetch/parser, tests and workflow. No CVs, profile, job database,
Telegram credentials, Gmail credentials or private-repository history. WORKER_URL
and GUEST_INGEST_TOKEN are repository secrets. Logs show only counts and health status.

The paired worker permits five-minute healthy checks. It independently
filters roles, posting ages and duplicates. Source backoff and Retry-After override
the schedule. No proxy rotation, account cookies, retries or bypass of access blocks.

Initial query: Software Engineer, Sri Lanka, newest first. This does not cover all
LinkedIn jobs. SE/DevOps and eligible remote query coverage must be expanded and
validated separately, with per-query backoff and global request bounds.

Deployment procedure: configure secrets, set Worker guest healthy interval to 300 seconds,
confirm Cloudflare dispatch produces workflow_dispatch runs. Do not add a public
cron schedule alongside Cloudflare dispatch. Keep failure backoff and any outstanding
Retry-After.

Test locally: python -m unittest discover -p test_guest_runner.py
