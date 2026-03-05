#!/usr/bin/env python3
"""Fetch pinned repos via GitHub GraphQL API and update the pacman block in README."""

import json
import re
import subprocess
import sys
from pathlib import Path

QUERY = """
{
  user(login: "NihilDigit") {
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name
          url
          description
          stargazerCount
          latestRelease {
            tagName
          }
        }
      }
    }
  }
}
"""

README = Path(__file__).resolve().parent.parent / "README.md"


def fetch_pinned_repos() -> list[dict]:
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={QUERY}"],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    return data["data"]["user"]["pinnedItems"]["nodes"]


def format_repo(repo: dict) -> str:
    name = repo["name"]
    url = repo["url"]
    description = repo["description"] or "No description"
    stars = repo["stargazerCount"]
    release = repo.get("latestRelease")

    version = ""
    if release and release.get("tagName"):
        version = " " + release["tagName"].lstrip("v")

    star_badge = ""
    if stars > 0:
        star_badge = f" [installed: {stars}\u2605]"

    line1 = f'nihildigit/<a href="{url}"><b>{name}</b></a>{version}{star_badge}'
    line2 = f"    {description}"
    return f"{line1}\n{line2}"


def main():
    repos = fetch_pinned_repos()
    entries = "\n".join(format_repo(r) for r in repos)
    block = f"<!-- pacman-start -->\n<pre>\n{entries}\n</pre>\n<!-- pacman-end -->"

    text = README.read_text()
    pattern = re.compile(
        r"<!-- pacman-start -->.*?<!-- pacman-end -->", re.DOTALL
    )

    if not pattern.search(text):
        print("ERROR: pacman markers not found in README.md", file=sys.stderr)
        sys.exit(1)

    new_text = pattern.sub(block, text)

    if new_text == text:
        print("No changes needed.")
        return

    README.write_text(new_text)
    print("README.md updated.")


if __name__ == "__main__":
    main()
