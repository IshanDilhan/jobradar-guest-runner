# Guest job discovery runner

Small public runner for a private personal job-alert service. Scheduled every five
minutes using standard GitHub-hosted Ubuntu runners. No paid services, caches or
artifacts. GitHub schedules can be delayed or dropped; detection within five minutes
is not guaranteed. Public schedules may disable after 60 days without repository activity.

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
disable the private repository's hourly guest schedule, then enable this schedule.
Do not run both schedulers. Keep failure backoff and any outstanding Retry-After.

Test locally: python -m unittest discover -p test_guest_runner.py
