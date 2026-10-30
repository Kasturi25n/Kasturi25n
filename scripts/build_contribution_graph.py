#!/usr/bin/env python3
"""Render the contribution graph as an SVG in the profile's purple palette.

GitHub's own graph cannot be recoloured and the hosted graph image services
either hardcode their colours or run out of quota, so the graph is generated
here from the contributions calendar and published by the workflow.

Usage:
    python3 scripts/build_contribution_graph.py <github-username> <output.svg>

Needs GITHUB_TOKEN or GH_TOKEN: the contributions calendar is only available
through the GraphQL API, which requires authentication.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date

BG = "#0b0816"
BORDER = "#8b5cf6"
TEXT = "#e9e5ff"
MUTED = "#8b87a8"
EMPTY = "#1a1433"
LEVELS = {
    "NONE": EMPTY,
    "FIRST_QUARTILE": "#3b2a73",
    "SECOND_QUARTILE": "#5b3fb5",
    "THIRD_QUARTILE": "#8b5cf6",
    "FOURTH_QUARTILE": "#c4b5fd",
}
FONT = "'Segoe UI','Helvetica Neue',Helvetica,Arial,sans-serif"

CELL, GAP = 12, 4
PITCH = CELL + GAP
LEFT, TOP = 56, 74

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          firstDay
          contributionDays { date contributionCount contributionLevel weekday }
        }
      }
    }
  }
}
"""


def fetch(username):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("Set GITHUB_TOKEN or GH_TOKEN to read the contributions calendar.")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": username}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            payload = json.loads(r.read())
    except urllib.error.HTTPError as exc:
        sys.exit(f"GitHub API returned {exc.code}: {exc.read()[:200]!r}")
    if "errors" in payload:
        sys.exit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def build(cal):
    weeks = cal["weeks"]
    total = cal["totalContributions"]
    width = LEFT + len(weeks) * PITCH + 24
    height = TOP + 7 * PITCH + 56

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{total} contributions in the last year">',
        f'<rect width="{width}" height="{height}" rx="18" fill="{BG}"/>',
        f'<rect x="0.75" y="0.75" width="{width - 1.5}" height="{height - 1.5}" rx="17.5" fill="none" stroke="{BORDER}" stroke-opacity="0.35"/>',
        f'<text x="28" y="40" font-family="{FONT}" font-size="20" font-weight="600" fill="{TEXT}">{total} contributions in the last year</text>',
    ]

    # One label per month, skipping a label that would sit on the previous one
    # (which happens when the year window opens mid-month).
    months, last_month = [], None
    for i, w in enumerate(weeks):
        d = date.fromisoformat(w["firstDay"])
        if d.month != last_month and (i == 0 or d.day <= 7):
            months.append((i, d.strftime("%b")))
            last_month = d.month
    if len(months) > 1 and months[1][0] - months[0][0] < 3:
        months.pop(0)
    for i, name in months:
        parts.append(
            f'<text x="{LEFT + i * PITCH}" y="{TOP - 12}" font-family="{FONT}" font-size="12" fill="{MUTED}">{name}</text>'
        )

    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        parts.append(
            f'<text x="28" y="{TOP + row * PITCH + CELL - 1}" font-family="{FONT}" font-size="12" fill="{MUTED}">{label}</text>'
        )

    for i, w in enumerate(weeks):
        for day in w["contributionDays"]:
            n = day["contributionCount"]
            tip = f'{n} contribution{"" if n == 1 else "s"} on {day["date"]}'
            parts.append(
                f'<rect x="{LEFT + i * PITCH}" y="{TOP + day["weekday"] * PITCH}" width="{CELL}" height="{CELL}" rx="3" '
                f'fill="{LEVELS[day["contributionLevel"]]}"><title>{tip}</title></rect>'
            )

    ly = height - 26
    lx = width - 24 - 5 * PITCH - 90
    parts.append(f'<text x="{lx}" y="{ly + 10}" font-family="{FONT}" font-size="12" fill="{MUTED}">Less</text>')
    for j, color in enumerate(LEVELS.values()):
        parts.append(f'<rect x="{lx + 34 + j * PITCH}" y="{ly}" width="{CELL}" height="{CELL}" rx="3" fill="{color}"/>')
    parts.append(
        f'<text x="{lx + 34 + 5 * PITCH + 4}" y="{ly + 10}" font-family="{FONT}" font-size="12" fill="{MUTED}">More</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts), total


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    username, target = sys.argv[1], sys.argv[2]
    svg, total = build(fetch(username))
    with open(target, "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"wrote {target} ({total} contributions)")


if __name__ == "__main__":
    main()
