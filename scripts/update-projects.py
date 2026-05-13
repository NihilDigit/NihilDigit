#!/usr/bin/env python3
"""Fetch pinned repos via GitHub GraphQL API and update the projects block in README."""

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
    return f"- [{name}]({url}) — {description}"


def main():
    repos = fetch_pinned_repos()
    entries = "\n".join(format_repo(repo) for repo in repos)
    block = f"<!-- projects-start -->\n{entries}\n<!-- projects-end -->"

    text = README.read_text()
    pattern = re.compile(r"<!-- projects-start -->.*?<!-- projects-end -->", re.DOTALL)

    if not pattern.search(text):
        print("ERROR: project markers not found in README.md", file=sys.stderr)
        sys.exit(1)

    new_text = pattern.sub(block, text)

    if new_text == text:
        print("No changes needed.")
        return

    README.write_text(new_text)
    print("README.md updated.")


if __name__ == "__main__":
    main()
