#!/usr/bin/env python3
"""Compare scheduled articles with their public Zenn and Qiita listings."""

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parent.parent
ZENN_FEED = "https://zenn.dev/seckeyjp/feed?all=1"
QIITA_ITEMS = "https://qiita.com/api/v2/users/SeckeyJP/items?per_page=100&page={}"
USER_AGENT = "j-six-articles-publication-check/1.0"
ID_PATTERN = re.compile(r"^[0-9a-f]{20}$")
JST = timezone(timedelta(hours=9))


def get_bytes(url):
    with urlopen(Request(url, headers={"User-Agent": USER_AGENT}), timeout=20) as response:
        return response.read()


def frontmatter_value(path, key):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("frontmatter missing: {}".format(path))
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("frontmatter not closed: {}".format(path))
    match = re.search(r"^{}:\s*(.*?)\s*$".format(re.escape(key)), text[4:end], re.M)
    if match is None:
        raise ValueError("{} missing: {}".format(key, path))
    return match.group(1).strip("'\"")


def public_zenn_slugs(xml_bytes):
    root = ElementTree.fromstring(xml_bytes)
    if root.tag != "rss" or root.find("channel") is None:
        raise ValueError("unexpected Zenn RSS format")
    articles = {}
    for item in root.findall("./channel/item"):
        link = item.findtext("link")
        parsed = urlparse(link or "")
        prefix = "/seckeyjp/articles/"
        if parsed.netloc != "zenn.dev" or not parsed.path.startswith("/seckeyjp/"):
            raise ValueError("unexpected Zenn RSS item: {}".format(link))
        if not parsed.path.startswith(prefix):
            continue  # 同じユーザーの本などは記事の照合対象外
        slug = parsed.path[len(prefix):].strip("/")
        if not slug or "/" in slug or slug in articles:
            raise ValueError("invalid or duplicate Zenn slug: {}".format(slug))
        published_at = parsedate_to_datetime(item.findtext("pubDate"))
        if published_at is None or published_at.tzinfo is None:
            raise ValueError("invalid Zenn publication date: {}".format(slug))
        articles[slug] = published_at.astimezone(JST)
    return articles


def public_qiita_ids(fetch=get_bytes):
    ids = set()
    for page in range(1, 101):
        items = json.loads(fetch(QIITA_ITEMS.format(page)))
        if not isinstance(items, list):
            raise ValueError("unexpected Qiita API format")
        for item in items:
            item_id = item.get("id") if isinstance(item, dict) else None
            if not isinstance(item_id, str) or not ID_PATTERN.fullmatch(item_id):
                raise ValueError("invalid Qiita item ID")
            if item.get("private") is not False:
                raise ValueError("Qiita listing contains non-public item: {}".format(item_id))
            if item_id in ids:
                raise ValueError("duplicate Qiita item ID: {}".format(item_id))
            ids.add(item_id)
        if len(items) < 100:
            return ids
    raise ValueError("Qiita pagination limit exceeded")


def publication_state(root=ROOT, fetch=get_bytes):
    schedule = json.loads((root / ".github/publish-schedule.json").read_text(encoding="utf-8"))["articles"]
    if not isinstance(schedule, list):
        raise ValueError("invalid publication schedule")
    seen = set()
    entries = []
    qiita_ids = set()
    def add_article(slug, due):
        published = frontmatter_value(root / "articles" / (slug + ".md"), "published")
        if published not in ("true", "false"):
            raise ValueError("invalid published flag: {}".format(slug))
        qiita_id = None
        if published == "true":
            qiita_path = root / "qiita/public" / (slug + ".md")
            if qiita_path.exists():
                qiita_id = frontmatter_value(qiita_path, "id")
                if not ID_PATTERN.fullmatch(qiita_id):
                    qiita_id = None
            if qiita_id is not None:
                if qiita_id in qiita_ids:
                    raise ValueError("duplicate local Qiita ID: {}".format(qiita_id))
                qiita_ids.add(qiita_id)
        entries.append({"slug": slug, "date": due, "published": published == "true", "qiita_id": qiita_id})

    for entry in schedule:
        slug = entry["slug"]
        due = date.fromisoformat(entry["date"])
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug) or slug in seen:
            raise ValueError("invalid or duplicate scheduled slug: {}".format(slug))
        seen.add(slug)
        add_article(slug, due)
    for path in sorted((root / "articles").glob("*.md")):
        if path.stem not in seen:
            add_article(path.stem, None)
    entries.sort(key=lambda item: (item["date"] or date.max, item["slug"]))
    zenn = public_zenn_slugs(fetch(ZENN_FEED))
    qiita = public_qiita_ids(fetch)
    return entries, zenn, qiita


def assess(entries, zenn, qiita, today):
    missing = []
    pending = []
    for entry in entries:
        slug = entry["slug"]
        if entry["published"]:
            if slug not in zenn:
                missing.append("Zenn: " + slug)
            if entry["qiita_id"] not in qiita:
                missing.append("Qiita: " + slug)
        elif entry["date"] is not None and entry["date"] <= today:
            pending.append(slug)
    return missing, pending


def next_candidate(pending, zenn, now):
    # This is a conservative operating interval, not Zenn's unpublished limit.
    if not pending or (zenn and now - max(zenn.values()) < timedelta(hours=24)):
        return None
    return pending[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("verify", "next"))
    parser.add_argument("--date", default=date.today().isoformat(), help="JST date, YYYY-MM-DD")
    args = parser.parse_args()
    try:
        today = date.fromisoformat(args.date)
        entries, zenn, qiita = publication_state()
        missing, pending = assess(entries, zenn, qiita, today)
        if missing:
            print("Publication mismatch: " + ", ".join(missing), file=sys.stderr)
            return 1
        if args.action == "next":
            candidate = next_candidate(pending, zenn, datetime.now(JST))
            if candidate:
                print(candidate)
            elif pending:
                print("Zenn published an article within the past 24 hours; defer next article", file=sys.stderr)
        else:
            print(json.dumps({"date": today.isoformat(), "scheduled_published": sum(e["published"] for e in entries), "pending_due": pending, "zenn_public": len(zenn), "qiita_public": len(qiita)}, ensure_ascii=False))
            if pending:
                print("Due articles still unpublished: " + ", ".join(pending), file=sys.stderr)
                return 1
        return 0
    except (OSError, ValueError, KeyError, TypeError, ElementTree.ParseError, json.JSONDecodeError) as exc:
        print("Publication check failed: {}".format(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
