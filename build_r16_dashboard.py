"""
World Cup 2026 — Round of 16 Dashboard

Same 6-dimension analytics as R32 page, but:
- Only includes R32 winners (teams that advanced to R16)
- Uses ALL match data (group stage + R32 knockout matches)
- Normalized against only the R16 pool (tighter competition)
- Progressively fills in as more R32 matches complete

Reads R16 teams from data/r16_teams.txt.
"""

import csv
import os
import json
import sys
from statistics import mean

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
REPO_DIR = os.environ.get("REPO_DIR", SCRIPT_DIR)
DATA_DIR = os.path.join(REPO_DIR, "data")
PUBLIC_DIR = os.path.join(REPO_DIR, "public")

from build_r32_dashboard import (
    read_team_matches, compute_match_score, compute_team_dimensions,
    normalize_dimensions, weighted_mean, safe_mean, parse_float, DIMS, _nav_html
)
from html_templates import r32_html  # Reuse the same card layout


def read_r16_teams():
    filepath = os.path.join(DATA_DIR, "r16_teams.txt")
    teams = []
    if not os.path.exists(filepath):
        return teams
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                teams.append(line)
    return teams


def main():
    print("=" * 60)
    print("  World Cup 2026 — Round of 16 Dashboard")
    print("=" * 60)

    # Read R16 teams
    print("\n[1] Reading R16 teams...")
    r16_teams = read_r16_teams()
    print(f"    {len(r16_teams)} teams confirmed in R16")

    if len(r16_teams) < 2:
        print("    Not enough teams yet. Skipping R16 page.")
        return

    # Read ALL match data (group stage + knockout)
    print("\n[2] Reading all match data...")
    all_matches = {}
    for team in r16_teams:
        matches = read_team_matches(team)
        if matches:
            all_matches[team] = matches
            print(f"    {team:30s} — {len(matches)} matches")

    # Compute dimensions (normalized across R16 pool only)
    print(f"\n[3] Computing dimensions ({len(all_matches)} teams, all matches)...")
    all_data = []
    for team_name, matches in all_matches.items():
        data = compute_team_dimensions(team_name, matches)
        if data:
            all_data.append(data)

    all_data = normalize_dimensions(all_data)

    sorted_data = sorted(all_data, key=lambda x: x["overall"], reverse=True)
    print("\n    Rankings:")
    for i, t in enumerate(sorted_data, 1):
        print(f"    {i:2}. {t['team']:25s} OVR:{t['overall']:5.1f}")

    # Generate R16 page HTML (reuse R32 template with different title)
    print("\n[4] Generating R16 dashboard...")
    js_items = []
    for t in sorted_data:
        js_items.append(json.dumps({
            "name": t["team"], "matches": t["matches"], "overall": t["overall"],
            "finishing": t["finishing"], "creation": t["creation"],
            "control": t["control"], "defense": t["defense"],
            "physicality": t["physicality"], "pressing": t["pressing"],
            "consistency": t.get("consistency"),
            "finCon": t.get("finishing_consistency"), "creCon": t.get("creation_consistency"),
            "ctrlCon": t.get("control_consistency"), "defCon": t.get("defense_consistency"),
            "phyCon": t.get("physicality_consistency"), "prsCon": t.get("pressing_consistency"),
            "avgGoals": t["avg_goals"], "avgXG": t["avg_xg"], "avgXA": t["avg_xa"],
            "avgPoss": t["avg_possession"], "avgPassAcc": t["avg_pass_acc"],
            "avgXGC": t["avg_xg_conceded"], "avgTackles": t["avg_tackles"],
            "avgPPDA": t["avg_ppda"], "avgRecoveries": t["avg_recoveries"],
            "avgDuelsWon": t["avg_duels_won"],
        }))

    js_array = ",\n        ".join(js_items)

    # Build nav with R16 link active
    nav_links = [("dashboard.html", "Group Stage"), ("r32.html", "Round of 32"),
                 ("r16.html", "Round of 16"), ("trends.html", "Trends"), ("bracket.html", "Bracket")]
    nav_html = " &middot; ".join(
        f'<a href="{url}" class="nav-link{" active" if url == "r16.html" else ""}">{label}</a>'
        for url, label in nav_links
    )

    # Generate HTML using the r32 template (same card layout)
    from html_templates import r32_html
    html = r32_html(js_array, nav_html)
    # Replace title/subtitle
    html = html.replace(
        "World Cup 2026 — Round of 32",
        "World Cup 2026 — Round of 16"
    )
    html = html.replace(
        "6 dimensions · Normalized against qualified knockout teams only",
        f"6 dimensions · Normalized against {len(r16_teams)} R16 teams · Uses all matches (group + knockout)"
    )
    html = html.replace(
        "Scores are min-max normalized (0-100) across the 32 qualified knockout teams",
        f"Scores are min-max normalized (0-100) across the {len(r16_teams)} Round of 16 teams"
    )

    filepath = os.path.join(PUBLIC_DIR, "r16.html")
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✓ R16 Dashboard: {filepath}")

    print("\n" + "=" * 60)
    print("  Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
