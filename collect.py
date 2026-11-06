"""Archive all publicly listed notices and publish a stable RSS 2.0 feed."""
from __future__ import annotations

import json
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urljoin

from lxml import html

BASE = "https://hdj.nea.gov.cn/dtyw/tzgg/"
ORIGIN = "https://zhengboyuan.github.io/hdj-notices-rss/"
ROOT = Path(__file__).resolve().parent
CST = timezone(timedelta(hours=8))
ET.register_namespace("atom", "http://www.w3.org/2005/Atom")


def fetch(url: str) -> bytes:
    return subprocess.run(
        ["curl", "--fail", "--location", "--silent", "--show-error",
         "--retry", "2", "--retry-delay", "2", "--max-time", "30", url],
        check=True, capture_output=True,
    ).stdout


def parse_page(raw: bytes, url: str) -> list[dict]:
    tree = html.fromstring(raw.decode("utf-8"))
    result = []
    for li in tree.xpath('//div[@class="wrapper_overview_right_list"]/ul/li'):
        anchors = li.xpath("./a[@href]")
        if not anchors:
            continue
        a = anchors[0]
        spans = a.xpath("./span")
        if len(spans) < 2:
            raise ValueError(f"Notice structure changed: {url}")
        title = " ".join(spans[0].text_content().split())
        date = spans[1].text_content().strip()
        datetime.strptime(date, "%Y-%m-%d")
        link = urljoin(url, a.get("href"))
        if not title or not link.startswith(("https://", "http://")):
            raise ValueError(f"Invalid notice: {url}")
        result.append({"title": title, "date": date, "url": link})
    if not result:
        raise ValueError(f"No notices found: {url}")
    return result


def complete_title(item: dict) -> str:
    if not re.search(r"\.{3}|…", item["title"]) or not item["url"].endswith(".html"):
        return item["title"]
    tree = html.fromstring(fetch(item["url"]).decode("utf-8"))
    titles = tree.xpath('//meta[@name="ArticleTitle"]/@content')
    if not titles:
        titles = tree.xpath("//title/text()")
    if not titles:
        raise ValueError(f"No article title: {item['url']}")
    return " ".join(titles[0].split()).removesuffix("_国家能源局华东监管局")


def atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)


def main() -> None:
    archive_path = ROOT / "data/notices.json"
    previous = json.loads(archive_path.read_text()) if archive_path.exists() else []
    records = {item["url"]: item for item in previous}
    first = fetch(urljoin(BASE, "index.html"))
    match = re.search(rb'countPage\s*=\s*Number\("(\d+)"\)', first)
    if not match:
        raise ValueError("Unable to identify total page count")
    page_count = int(match[1])
    if not 1 <= page_count <= 10000:
        raise ValueError("Unexpected page count")
    observed = {}
    for page in range(page_count):
        url = urljoin(BASE, "index.html" if page == 0 else f"index_{page}.html")
        raw = first if page == 0 else fetch(url)
        for item in parse_page(raw, url):
            observed.setdefault(item["url"], item)
        print(f"Page {page + 1}/{page_count}: {len(observed)} unique notices", flush=True)
        time.sleep(0.3)
    # Publish only after every list page succeeded; retain older archived notices.
    for item in observed.values():
        old = records.get(item["url"])
        if old and not re.search(r"\.{3}|…", old["title"]) and re.search(r"\.{3}|…", item["title"]):
            item["title"] = old["title"]
        elif re.search(r"\.{3}|…", item["title"]):
            try:
                item["title"] = complete_title(item)
            except (subprocess.CalledProcessError, ValueError, UnicodeError) as exc:
                print(f"Title fallback: {item['url']} ({type(exc).__name__})", flush=True)
            time.sleep(0.3)
        records[item["url"]] = item
    items = sorted(records.values(), key=lambda item: (item["date"], item["url"]), reverse=True)
    now = datetime.now(CST)
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    for tag, value in {
        "title": "华东能源监管局｜通知公告（历史归档与更新）",
        "link": BASE,
        "description": "非官方订阅源：收录官网通知公告栏目现存全部分页，保留历史记录。内容版权归原发布单位。",
        "language": "zh-cn", "ttl": "360", "lastBuildDate": format_datetime(now),
    }.items():
        ET.SubElement(channel, tag).text = value
    ET.SubElement(channel, "{http://www.w3.org/2005/Atom}link", {
        "href": ORIGIN + "feed.xml", "rel": "self", "type": "application/rss+xml",
    })
    for item in items:
        node = ET.SubElement(channel, "item")
        ET.SubElement(node, "title").text = item["title"]
        ET.SubElement(node, "link").text = item["url"]
        ET.SubElement(node, "guid", isPermaLink="true").text = item["url"]
        ET.SubElement(node, "pubDate").text = format_datetime(datetime.strptime(item["date"], "%Y-%m-%d").replace(tzinfo=CST))
        ET.SubElement(node, "description").text = f"{item['title']}\n发布日期：{item['date']}\n来源：国家能源局华东监管局。点击原文查看正文或附件。"
    ET.indent(rss)
    xml = ET.tostring(rss, encoding="utf-8", xml_declaration=True)
    assert len(ET.fromstring(xml).findall("./channel/item")) == len(items)
    atomic_write(archive_path, (json.dumps(items, ensure_ascii=False, indent=2) + "\n").encode())
    atomic_write(ROOT / "public/feed.xml", xml)
    atomic_write(ROOT / "public/status.json", (json.dumps({
        "updated_at": now.isoformat(), "pages": page_count,
        "currently_listed_count": len(observed), "archive_count": len(items),
        "oldest_date": items[-1]["date"], "newest_date": items[0]["date"],
    }, ensure_ascii=False, indent=2) + "\n").encode())
    print(f"Published {len(items)} notices, {items[-1]['date']} to {items[0]['date']}", flush=True)


if __name__ == "__main__":
    main()
