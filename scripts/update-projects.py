#!/usr/bin/env python3
"""Plan the profile cards from pinned repos and update the projects block in README.

  plan    query pinned repos, write `repos` and `cards` to $GITHUB_OUTPUT
  readme  render the projects block from $PINNED_REPOS (the `repos` output)

The readme step reuses the plan's repo list instead of querying again, so the
README never points at a pin card that the same run has not published.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

USER = "NihilDigit"

QUERY = f"""
{{
  user(login: "{USER}") {{
    pinnedItems(first: 6, types: REPOSITORY) {{
      nodes {{
        ... on Repository {{
          name
          url
          owner {{ login }}
        }}
      }}
    }}
  }}
}}
"""

STATS_OPTIONS = (
    f"username={USER}&show_icons=true&include_all_commits=true&hide_border=true"
    "&hide=contribs&show=prs_merged,all_time_contribs&disable_animations=true"
)
LANGS_OPTIONS = (
    f"username={USER}&layout=compact&langs_count=6&size_weight=0.5&count_weight=0.5"
    "&hide_border=true&card_width=320&disable_animations=true"
)
# A fixed description height keeps cards in the same row aligned
PIN_WIDTH = 390
PIN_OPTIONS = f"description_lines_count=2&card_width={PIN_WIDTH}"

ASSETS = f"https://raw.githubusercontent.com/{USER}/{USER}/output"
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


def pin_name(repo: dict) -> str:
    return f"pin-{repo['owner']['login']}-{repo['name']}"


def plan_cards(repos: list[dict]) -> list[dict]:
    cards = [
        {
            "name": "stats",
            "card": "stats",
            "light": f"{STATS_OPTIONS}&theme=light_github",
            "dark": f"{STATS_OPTIONS}&theme=dark_github",
        },
        {
            "name": "top-langs",
            "card": "top-langs",
            "light": f"{LANGS_OPTIONS}&theme=light_github",
            "dark": f"{LANGS_OPTIONS}&theme=dark_github",
        },
    ]
    for repo in repos:
        owner = repo["owner"]["login"]
        options = f"username={owner}&repo={repo['name']}&{PIN_OPTIONS}"
        if owner != USER:
            options += "&show_owner=true"
        cards.append(
            {
                "name": pin_name(repo),
                "card": "pin",
                "light": f"{options}&theme=light_github_repocard",
                "dark": f"{options}&theme=dark_github_repocard",
            }
        )
    return cards


def format_repo(repo: dict) -> str:
    name = pin_name(repo)
    # One line per anchor: whitespace inside <a> renders as an underlined space
    return (
        f'<a href="{repo["url"]}"><picture>'
        f'<source media="(prefers-color-scheme: dark)" srcset="{ASSETS}/{name}-dark.avif" />'
        f'<img width="{PIN_WIDTH}" alt="{repo["name"]}" src="{ASSETS}/{name}-light.avif" />'
        f"</picture></a>"
    )


def plan() -> None:
    repos = fetch_pinned_repos()
    with open(os.environ["GITHUB_OUTPUT"], "a") as output:
        output.write(f"repos={json.dumps(repos)}\n")
        output.write(f"cards={json.dumps(plan_cards(repos))}\n")


def readme() -> None:
    repos = json.loads(os.environ["PINNED_REPOS"])
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


def main():
    commands = {"plan": plan, "readme": readme}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        print(f"usage: {sys.argv[0]} plan|readme", file=sys.stderr)
        sys.exit(2)
    commands[sys.argv[1]]()


if __name__ == "__main__":
    main()
