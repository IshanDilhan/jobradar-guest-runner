import unittest

from guest_runner import Cards, build_search_url, retry_seconds, select_query


class ParserTests(unittest.TestCase):
    def test_nested_company_entities_duplicates(self):
        html = (
            '<li><div data-entity-urn="urn:li:jobPosting:4000001">'
            '<h3 class="base-search-card__title">Software Engineer</h3>'
            '<h4 class="base-search-card__subtitle"><a>Example &amp; Co</a></h4>'
            '<span class="job-search-card__location">Colombo</span>'
            '<time datetime="2026-09-25">2 hours ago</time></div></li>'
        )
        parser = Cards()
        parser.feed(html + html)
        self.assertEqual(len(parser.jobs), 1)
        self.assertEqual(parser.jobs[0]["company"], "Example & Co")
        self.assertEqual(parser.jobs[0]["location"], "Colombo")
        self.assertEqual(parser.jobs[0]["postedDate"], "2026-09-25")
        self.assertEqual(parser.jobs[0]["postedText"], "2 hours ago")

    def test_block_page_is_not_a_job(self):
        parser = Cards()
        parser.feed("<html>Please sign in</html>")
        self.assertEqual(parser.jobs, [])

    def test_retry_after(self):
        self.assertEqual(retry_seconds("14400"), 14400)
        self.assertEqual(retry_seconds("invalid"), 0)

    def test_query_rotation(self):
        # 300-second slots rotate deterministically
        q0 = select_query(now=0)
        q1 = select_query(now=300)
        q2 = select_query(now=600)
        q3 = select_query(now=900)
        self.assertEqual(q0, ("software engineer", "Sri Lanka"))
        self.assertEqual(q1, ("devops engineer", "Sri Lanka"))
        self.assertEqual(q2, ("cloud engineer", "Sri Lanka"))
        self.assertEqual(q3, ("software engineer", "Sri Lanka"))

    def test_build_search_url(self):
        url = build_search_url("software engineer", "Sri Lanka")
        self.assertIn("keywords=software%20engineer", url)
        self.assertIn("location=Sri%20Lanka", url)
        self.assertIn("start=0", url)
        self.assertIn("sortBy=DD", url)
        self.assertTrue(url.startswith("https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search?"))

        url_devops = build_search_url("devops engineer", "Sri Lanka")
        self.assertIn("keywords=devops%20engineer", url_devops)


if __name__ == "__main__":
    unittest.main()
