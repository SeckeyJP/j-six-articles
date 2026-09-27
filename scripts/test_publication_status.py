import importlib.util
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("publication_status", Path(__file__).with_name("publication_status.py"))
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PublicationStatusTests(unittest.TestCase):
    def setUp(self):
        self.entries = [
            {"slug": "j-six-walkthrough-02-spec", "date": date(2026, 9, 24), "published": True, "qiita_id": "a" * 20},
            {"slug": "j-six-walkthrough-03-design", "date": date(2026, 9, 25), "published": True, "qiita_id": "b" * 20},
            {"slug": "j-six-walkthrough-04-tdd", "date": date(2026, 9, 28), "published": False, "qiita_id": None},
            {"slug": "j-six-walkthrough-05-deliverables", "date": date(2026, 9, 29), "published": False, "qiita_id": None},
        ]

    def test_missing_zenn_article_blocks_next(self):
        missing, pending = MODULE.assess(self.entries, {self.entries[0]["slug"]}, {"a" * 20, "b" * 20}, date(2026, 9, 29))
        self.assertEqual(missing, ["Zenn: j-six-walkthrough-03-design"])
        self.assertEqual(pending, ["j-six-walkthrough-04-tdd", "j-six-walkthrough-05-deliverables"])

    def test_backlog_yields_one_oldest_article(self):
        missing, pending = MODULE.assess(self.entries, {e["slug"] for e in self.entries[:2]}, {"a" * 20, "b" * 20}, date(2026, 9, 30))
        self.assertEqual(missing, [])
        last = datetime(2026, 9, 27, 7, tzinfo=MODULE.JST)
        self.assertEqual(MODULE.next_candidate(pending, {"j-six-walkthrough-03-design": last}, datetime(2026, 9, 30, 12, tzinfo=MODULE.JST)), "j-six-walkthrough-04-tdd")

    def test_recent_zenn_publication_defers_backlog(self):
        pending = ["j-six-walkthrough-04-tdd", "j-six-walkthrough-05-deliverables"]
        last = datetime(2026, 9, 28, 19, tzinfo=MODULE.JST)
        self.assertIsNone(MODULE.next_candidate(pending, {"j-six-walkthrough-03-design": last}, datetime(2026, 9, 29, 12, tzinfo=MODULE.JST)))

    def test_missing_qiita_article_blocks_next(self):
        missing, _ = MODULE.assess(self.entries, {e["slug"] for e in self.entries[:2]}, {"a" * 20}, date(2026, 9, 28))
        self.assertEqual(missing, ["Qiita: j-six-walkthrough-03-design"])

    def test_rss_requires_all_articles_and_rejects_wrong_account(self):
        valid = b'<rss><channel><item><link>https://zenn.dev/seckeyjp/articles/one</link><pubDate>Sun, 27 Sep 2026 00:00:00 GMT</pubDate></item></channel></rss>'
        self.assertEqual(MODULE.public_zenn_slugs(valid), {"one": datetime(2026, 9, 27, 9, tzinfo=MODULE.JST)})
        with self.assertRaises(ValueError):
            MODULE.public_zenn_slugs(valid.replace(b"seckeyjp", b"someone"))

    def test_network_failure_is_not_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / ".github").mkdir()
            (root / ".github/publish-schedule.json").write_text('{"articles": []}')
            def fail(_):
                raise OSError("offline")
            with self.assertRaises(OSError):
                MODULE.publication_state(root, fail)


if __name__ == "__main__":
    unittest.main()
