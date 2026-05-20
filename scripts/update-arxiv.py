#!/usr/bin/env python3
"""Fetch works from arXiv author page and update the publications block in README."""

import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ARXIV_AUTHOR_ID = "liu_s_14"
AUTHOR_PAGE = f"https://arxiv.org/a/{ARXIV_AUTHOR_ID}.html"
ARXIV_API = "https://export.arxiv.org/api/query"
REQUEST_TIMEOUT = 20
MAX_RETRIES = 3

ATOM = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"

README = Path(__file__).resolve().parent.parent / "README.md"


def fetch_url(url: str, *, headers: dict[str, str] | None = None) -> bytes:
    """Fetch a URL with a few retries for transient arXiv/backend failures."""
    req = urllib.request.Request(url, headers=headers or {})
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return resp.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            last_error = exc
            if attempt == MAX_RETRIES:
                break
            time.sleep(2 ** (attempt - 1))

    raise RuntimeError(f"failed to fetch {url} after {MAX_RETRIES} attempts: {last_error}") from last_error


def fetch_arxiv_ids() -> list[str]:
    """Scrape arXiv IDs from the author page."""
    html = fetch_url(AUTHOR_PAGE, headers={"User-Agent": "Mozilla/5.0"}).decode()
    ids = re.findall(r"/abs/(\d{4}\.\d{4,5})", html)
    return list(dict.fromkeys(ids))


def fetch_metadata(arxiv_ids: list[str]) -> list[dict]:
    """Fetch paper metadata from arXiv API."""
    if not arxiv_ids:
        return []
    id_list = ",".join(arxiv_ids)
    url = f"{ARXIV_API}?id_list={id_list}&max_results={len(arxiv_ids)}"
    root = ET.fromstring(fetch_url(url))

    works = []
    for entry in root.findall(f"{ATOM}entry"):
        title = entry.findtext(f"{ATOM}title", "").replace("\n", " ").strip()
        arxiv_id = entry.findtext(f"{ATOM}id", "").split("/abs/")[-1]
        arxiv_id = re.sub(r"v\d+$", "", arxiv_id)  # strip version suffix

        # published date
        published = entry.findtext(f"{ATOM}published", "")
        year = published[:4] if published else ""
        month = published[5:7] if published else ""

        # authors
        authors = [
            a.findtext(f"{ATOM}name", "")
            for a in entry.findall(f"{ATOM}author")
        ]

        # DOI (if published)
        doi_el = entry.find(f"{ARXIV_NS}doi")
        doi = doi_el.text.strip() if doi_el is not None else ""

        # journal ref
        journal_el = entry.find(f"{ARXIV_NS}journal_ref")
        journal = journal_el.text.strip() if journal_el is not None else ""

        # comment (may contain "submitted to XXX")
        comment_el = entry.find(f"{ARXIV_NS}comment")
        comment = comment_el.text.strip() if comment_el is not None else ""

        works.append(
            {
                "title": title,
                "arxiv_id": arxiv_id,
                "year": year,
                "month": month,
                "authors": authors,
                "doi": doi,
                "journal": journal,
                "comment": comment,
            }
        )

    works.sort(key=lambda w: (w["year"], w["month"]), reverse=True)
    return works


def format_work(work: dict) -> str:
    date_str = work["year"]
    if work["month"]:
        date_str += f".{work['month']}"

    link = f"https://doi.org/{work['doi']}" if work["doi"] else f"https://arxiv.org/abs/{work['arxiv_id']}"
    line = f'<b>[{date_str}]</b> <a href="{link}">{work["title"]}</a>'

    if work["journal"]:
        line += f" — <i>{work['journal']}</i>"

    return line


def main():
    try:
        arxiv_ids = fetch_arxiv_ids()
    except RuntimeError as exc:
        print(f"WARNING: {exc}", file=sys.stderr)
        print("Keeping existing README publications block.")
        return

    if not arxiv_ids:
        print("No papers found on arXiv author page.")
        return

    try:
        works = fetch_metadata(arxiv_ids)
    except RuntimeError as exc:
        print(f"WARNING: {exc}", file=sys.stderr)
        print("Keeping existing README publications block.")
        return

    if not works:
        print("Failed to fetch metadata from arXiv API.")
        return

    entries = "\n".join(f"    {format_work(w)}" for w in works)
    block = (
        f"<!-- arxiv-start -->\n"
        f"<pre>\n"
        f"{entries}\n"
        f"</pre>\n"
        f"<!-- arxiv-end -->"
    )

    text = README.read_text()
    pattern = re.compile(r"<!-- arxiv-start -->.*?<!-- arxiv-end -->", re.DOTALL)

    if not pattern.search(text):
        print("ERROR: orcid markers not found in README.md", file=sys.stderr)
        sys.exit(1)

    new_text = pattern.sub(block, text)

    if new_text == text:
        print("No changes needed.")
        return

    README.write_text(new_text)
    print("README.md updated.")


if __name__ == "__main__":
    main()
