"""One public LinkedIn request; persistent Cloudflare backoff, no retries."""

import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit

GUEST_QUERIES = (
    ("software engineer", "Sri Lanka"),
    ("devops engineer", "Sri Lanka"),
    ("cloud engineer", "Sri Lanka"),
)


def select_query(now=None, queries=GUEST_QUERIES):
    ts = time.time() if now is None else now
    index = int(ts // 300) % len(queries)
    return queries[index]


def build_search_url(keywords, location):
    params = urllib.parse.urlencode(
        {"keywords": keywords, "location": location, "start": 0, "sortBy": "DD"},
        quote_via=urllib.parse.quote,
    )
    return f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?{params}"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Cards(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.jobs = []
        self.card = None
        self.field = None
        self.field_tag = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        urn = attrs.get("data-entity-urn", "")
        match = re.fullmatch(r"urn:li:jobPosting:(\d{6,20})", urn)
        if match:
            self.card = {"id": match[1], "title": "", "company": "", "location": ""}
        if self.card is None:
            return
        if tag == "time":
            self.card["postedDate"] = attrs.get("datetime", "")
            self.card["postedText"] = ""
            self.field, self.field_tag = "postedText", tag
        classes = attrs.get("class", "").split()
        for cls, field in (
            ("base-search-card__title", "title"),
            ("base-search-card__subtitle", "company"),
            ("job-search-card__location", "location"),
        ):
            if cls in classes:
                self.field, self.field_tag = field, tag

    def handle_data(self, data):
        if self.card is not None and self.field:
            self.card[self.field] += data

    def handle_endtag(self, tag):
        if tag == self.field_tag:
            self.field = self.field_tag = None
        if tag == "li" and self.card is not None:
            card = {k: " ".join(v.split())[:300] for k, v in self.card.items()}
            if card["title"] and len(self.jobs) < 25:
                card["company"] = card["company"] or "Unknown company"
                card["location"] = card["location"] or "See LinkedIn listing"
                card["url"] = "https://www.linkedin.com/jobs/view/" + card["id"]
                if not any(j["id"] == card["id"] for j in self.jobs):
                    self.jobs.append(card)
            self.card = None
            self.field = self.field_tag = None


def retry_seconds(value):
    try:
        return (
            max(0, int(value))
            if value.isdigit()
            else max(0, int(parsedate_to_datetime(value).timestamp() - time.time()))
        )
    except (ValueError, TypeError, OverflowError):
        return 0


def main():
    base = os.environ.get("WORKER_URL", "").rstrip("/")
    token = os.environ.get("GUEST_INGEST_TOKEN", "")
    parsed = urlsplit(base)
    if (
        parsed.scheme != "https"
        or not (parsed.hostname or "").endswith(".workers.dev")
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
        or parsed.path
        or parsed.query
        or parsed.fragment
        or not token
    ):
        raise SystemExit("Worker secrets missing or URL invalid")
    opener = urllib.request.build_opener(NoRedirect())

    def worker(path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        req = urllib.request.Request(
            base + path,
            data=data,
            headers={
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
                "User-Agent": "JobRadar-GitHub/1.0",
            },
        )
        try:
            with opener.open(req, timeout=20) as response:
                return json.loads(response.read(10000))
        except Exception:
            raise SystemExit(
                "Cloudflare guest request failed; inspect secret configuration and service health"
            ) from None

    health = worker("/guest-health")
    if health.get("next_check", 0) > time.time():
        print(json.dumps({"result": "backoff", "next_check": health["next_check"]}))
        return
    keywords, location = select_query()
    url = build_search_url(keywords, location)
    req = urllib.request.Request(
        url, headers={"User-Agent": "JobRadar/1.0 (personal job discovery)", "Accept": "text/html"}
    )
    try:
        with opener.open(req, timeout=20) as response:
            body = response.read(500001)
            if len(body) > 500000:
                raise ValueError("Oversized response")
        parser = Cards()
        parser.feed(body.decode("utf-8", errors="replace"))
        if not parser.jobs:
            raise ValueError("No recognizable cards")
    except urllib.error.HTTPError as error:
        result = worker(
            "/guest-health",
            {
                "status": error.code,
                "retryAfter": retry_seconds(error.headers.get("Retry-After", "")),
            },
        )
        print(
            json.dumps(
                {
                    "result": "source_unavailable",
                    "query": keywords,
                    "http_status": error.code,
                    **result,
                }
            )
        )
        return
    except (urllib.error.URLError, TimeoutError, ValueError):
        result = worker("/guest-health", {"status": 503})
        print(json.dumps({"result": "source_unavailable", "query": keywords, **result}))
        return
    result = worker("/guest-ingest", parser.jobs)
    print(
        json.dumps(
            {
                "result": "ingested",
                "query": keywords,
                "cards_found": len(parser.jobs),
                **result,
            }
        )
    )


if __name__ == "__main__":
    main()
