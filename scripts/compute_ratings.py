"""
Compute ATK / DEF / EFF / AGG ratings for all World Cup 2026 teams.

Cross-references each team's CSV with their opponent's CSV to derive
defensive stats (what the opponent did TO them).

Outputs:
  - team_ratings.csv: All teams with computed ratings
  - Updates each team's CSV with ATK, DEF, EFF, AGG columns
  - ratings_dashboard.html: Visual comparison of all teams
"""

import csv
import os
import math

DATA_DIR = r"d:\WorldCup 2026"


def read_team_csv(team_name):
    """Read a team's CSV and return list of match dicts."""
    filepath = os.path.join(DATA_DIR, f"{team_name}.csv")
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def parse_int(val):
    """Safely parse an integer from CSV value."""
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def parse_pct(val):
    """Parse percentage string like '61%' to float 61.0."""
    if not val or val.strip() == "":
        return None
    return float(val.replace("%", "").strip())


def get_all_team_files():
    """Get all team CSV files in the data directory."""
    teams = []
    for f in os.listdir(DATA_DIR):
        if f.endswith(".csv") and f not in [
            "team_ratings.csv", "qualifier_features.csv",
            "goalscorers.csv", "results.csv", "shootouts.csv",
            "team_rankings_2026.csv", "team_trends_2026.csv"
        ]:
            team_name = f.replace(".csv", "")
            teams.append(team_name)
    return sorted(teams)


def compute_ratings(team_name, team_matches, all_teams_data):
    """
    Compute ATK, DEF, EFF, AGG for a team across all played matches.
    Returns a dict with ratings or None if no played matches.
    """
    played_matches = []

    for match in team_matches:
        goals = parse_int(match.get("Goals"))
        if goals is None:
            continue  # Match not played yet

        opponent_name = match.get("Opponent", "").strip()
        shots = parse_int(match.get("Shots"))
        shots_on_target = parse_int(match.get("Shots on target"))
        possession = parse_pct(match.get("Possession"))
        passes = parse_int(match.get("Passes"))
        pass_acc = parse_pct(match.get("Pass Accuracy"))
        fouls = parse_int(match.get("Fouls"))
        yellows = parse_int(match.get("Yellow cards"))
        reds = parse_int(match.get("Red cards"))
        corners = parse_int(match.get("Corners"))

        # Cross-reference: get opponent's stats against this team
        opp_goals = None
        opp_shots = None
        opp_sot = None
        opp_shot_acc = None
        opp_corners = None

        if opponent_name in all_teams_data:
            for opp_match in all_teams_data[opponent_name]:
                if opp_match.get("Opponent", "").strip() == team_name:
                    opp_goals = parse_int(opp_match.get("Goals"))
                    opp_shots = parse_int(opp_match.get("Shots"))
                    opp_sot = parse_int(opp_match.get("Shots on target"))
                    opp_shot_acc = parse_pct(opp_match.get("Shot Accuracy"))
                    opp_corners = parse_int(opp_match.get("Corners"))
                    break

        played_matches.append({
            "goals": goals,
            "shots": shots,
            "shots_on_target": shots_on_target,
            "possession": possession,
            "passes": passes,
            "pass_acc": pass_acc,
            "fouls": fouls,
            "yellows": yellows,
            "reds": reds,
            "corners": corners,
            "opp_goals": opp_goals,
            "opp_shots": opp_shots,
            "opp_sot": opp_sot,
            "opp_shot_acc": opp_shot_acc,
            "opp_corners": opp_corners,
        })

    if not played_matches:
        return None

    n = len(played_matches)

    # Aggregate averages
    avg = lambda key: sum(m[key] for m in played_matches if m[key] is not None) / max(1, sum(1 for m in played_matches if m[key] is not None))

    avg_goals = avg("goals")
    avg_shots = avg("shots")
    avg_sot = avg("shots_on_target")
    avg_possession = avg("possession")
    avg_passes = avg("passes")
    avg_pass_acc = avg("pass_acc")
    avg_fouls = avg("fouls")
    avg_yellows = avg("yellows")
    avg_reds = avg("reds")
    avg_corners = avg("corners")
    avg_opp_goals = avg("opp_goals")
    avg_opp_shots = avg("opp_shots")
    avg_opp_sot = avg("opp_sot")
    avg_opp_shot_acc = avg("opp_shot_acc")
    avg_opp_corners = avg("opp_corners")

    # === ATK (0-100) ===
    # Goals: 0-7 range → scale to 0-100 (weight 35%)
    # Shots on target: 0-12 range → scale (weight 25%)
    # Shot accuracy: 0-100% already (weight 25%)
    # Corners: 0-11 range → scale (weight 15%)
    shot_accuracy = (avg_sot / avg_shots * 100) if avg_shots > 0 else 0

    atk_goals = min(avg_goals / 5.0 * 100, 100)  # 5 goals = 100
    atk_sot = min(avg_sot / 10.0 * 100, 100)     # 10 SoT = 100
    atk_shot_acc = shot_accuracy                   # already 0-100
    atk_corners = min(avg_corners / 10.0 * 100, 100)  # 10 corners = 100

    ATK = (atk_goals * 0.35) + (atk_sot * 0.25) + (atk_shot_acc * 0.25) + (atk_corners * 0.15)

    # === DEF (0-100) ===
    # Goals conceded inverted: 0 conceded = 100, 5+ conceded = 0
    # Opp shots on target inverted: 0 = 100, 10+ = 0
    # Opp shot accuracy inverted: 0% = 100, 100% = 0
    def_goals_inv = max(0, (1 - avg_opp_goals / 5.0)) * 100 if avg_opp_goals is not None else 50
    def_opp_sot_inv = max(0, (1 - avg_opp_sot / 10.0)) * 100 if avg_opp_sot is not None else 50
    def_opp_acc_inv = max(0, 100 - (avg_opp_shot_acc if avg_opp_shot_acc else 50))

    DEF = (def_goals_inv * 0.40) + (def_opp_sot_inv * 0.35) + (def_opp_acc_inv * 0.25)

    # === EFF (Efficiency 0-100) ===
    # Goal conversion: Goals / Shots (0-50% realistic → scale)
    # Possession quality: Goals / (Possession/100) → goals per possession unit
    # Shot generation: SoT / (Possession/100) → shots on target per possession unit
    goal_conversion = (avg_goals / avg_shots * 100) if avg_shots > 0 else 0
    eff_conversion = min(goal_conversion / 30.0 * 100, 100)  # 30% conversion = perfect

    poss_fraction = avg_possession / 100.0 if avg_possession > 0 else 0.5
    goals_per_poss = avg_goals / poss_fraction if poss_fraction > 0 else 0
    eff_poss_quality = min(goals_per_poss / 5.0 * 100, 100)  # 5 goals at any possession = 100

    sot_per_poss = avg_sot / poss_fraction if poss_fraction > 0 else 0
    eff_shot_gen = min(sot_per_poss / 12.0 * 100, 100)  # 12 SoT normalized by possession = 100

    EFF = (eff_conversion * 0.40) + (eff_poss_quality * 0.30) + (eff_shot_gen * 0.30)

    # === AGG (Aggression 0-100) ===
    # Fouls: 0-20 → scale (weight 30%)
    # Cards: yellows + reds*2, 0-8 scale (weight 40%)
    # Shots attempted: 0-28 range (weight 30%)
    agg_fouls = min(avg_fouls / 18.0 * 100, 100) if avg_fouls else 0
    card_score = avg_yellows + (avg_reds * 2) if avg_yellows is not None else 0
    agg_cards = min(card_score / 6.0 * 100, 100)
    agg_shots = min(avg_shots / 22.0 * 100, 100) if avg_shots else 0

    AGG = (agg_fouls * 0.30) + (agg_cards * 0.40) + (agg_shots * 0.30)

    return {
        "ATK": round(ATK, 1),
        "DEF": round(DEF, 1),
        "EFF": round(EFF, 1),
        "AGG": round(AGG, 1),
        "overall": round((ATK + DEF + EFF) / 3, 1),
        # Raw stats for reference
        "avg_goals": round(avg_goals, 2),
        "avg_shots": round(avg_shots, 1),
        "avg_sot": round(avg_sot, 1),
        "shot_accuracy": round(shot_accuracy, 1),
        "avg_possession": round(avg_possession, 1),
        "avg_pass_acc": round(avg_pass_acc, 1),
        "avg_opp_goals": round(avg_opp_goals, 2) if avg_opp_goals else 0,
        "avg_opp_sot": round(avg_opp_sot, 1) if avg_opp_sot else 0,
        "avg_corners": round(avg_corners, 1),
        "avg_fouls": round(avg_fouls, 1) if avg_fouls else 0,
        "matches_played": n,
    }


def update_team_csv(team_name, ratings):
    """Add ATK, DEF, EFF, AGG columns to the team's CSV."""
    filepath = os.path.join(DATA_DIR, f"{team_name}.csv")
    if not os.path.exists(filepath):
        return

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        original_fields = reader.fieldnames

    # Add new columns if not present
    new_fields = list(original_fields)
    for col in ["ATK", "DEF", "EFF", "AGG"]:
        if col not in new_fields:
            new_fields.append(col)

    # Update rows with ratings (apply same rating to all played matches)
    for row in rows:
        goals = parse_int(row.get("Goals"))
        if goals is not None and ratings:
            row["ATK"] = ratings["ATK"]
            row["DEF"] = ratings["DEF"]
            row["EFF"] = ratings["EFF"]
            row["AGG"] = ratings["AGG"]
        else:
            row["ATK"] = ""
            row["DEF"] = ""
            row["EFF"] = ""
            row["AGG"] = ""

    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=new_fields)
            writer.writeheader()
            writer.writerows(rows)
    except PermissionError:
        print(f"  SKIPPED (locked): {team_name}.csv")


def write_ratings_csv(all_ratings):
    """Write the master ratings CSV."""
    filepath = os.path.join(DATA_DIR, "team_ratings.csv")
    fields = [
        "Team", "ATK", "DEF", "EFF", "AGG", "Overall",
        "Goals/Match", "Shots/Match", "SoT/Match", "Shot Acc%",
        "Possession%", "Pass Acc%", "Conceded/Match", "Opp SoT/Match",
        "Corners/Match", "Fouls/Match", "Matches"
    ]

    rows = []
    for team, r in sorted(all_ratings.items(), key=lambda x: x[1]["overall"], reverse=True):
        rows.append({
            "Team": team,
            "ATK": r["ATK"],
            "DEF": r["DEF"],
            "EFF": r["EFF"],
            "AGG": r["AGG"],
            "Overall": r["overall"],
            "Goals/Match": r["avg_goals"],
            "Shots/Match": r["avg_shots"],
            "SoT/Match": r["avg_sot"],
            "Shot Acc%": r["shot_accuracy"],
            "Possession%": r["avg_possession"],
            "Pass Acc%": r["avg_pass_acc"],
            "Conceded/Match": r["avg_opp_goals"],
            "Opp SoT/Match": r["avg_opp_sot"],
            "Corners/Match": r["avg_corners"],
            "Fouls/Match": r["avg_fouls"],
            "Matches": r["matches_played"],
        })

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\n  Master ratings: {filepath}")


def generate_html(all_ratings):
    """Generate an HTML dashboard with radar-style stat cards."""
    filepath = os.path.join(DATA_DIR, "ratings_dashboard.html")

    # Sort by overall
    sorted_teams = sorted(all_ratings.items(), key=lambda x: x[1]["overall"], reverse=True)

    # Build JS data array
    js_data = []
    for team, r in sorted_teams:
        js_data.append(
            f'        {{ name: "{team}", atk: {r["ATK"]}, def: {r["DEF"]}, '
            f'eff: {r["EFF"]}, agg: {r["AGG"]}, overall: {r["overall"]}, '
            f'goals: {r["avg_goals"]}, conceded: {r["avg_opp_goals"]}, '
            f'possession: {r["avg_possession"]}, shotAcc: {r["shot_accuracy"]}, '
            f'passAcc: {r["avg_pass_acc"]} }}'
        )

    js_array = ",\n".join(js_data)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>World Cup 2026 — Team Ratings</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #0d1117;
            color: #e6edf3;
            padding: 30px;
            min-height: 100vh;
        }}
        h1 {{
            text-align: center;
            font-size: 2rem;
            margin-bottom: 5px;
            color: #58a6ff;
        }}
        .subtitle {{ text-align: center; color: #8b949e; margin-bottom: 25px; font-size: 0.9rem; }}
        .legend {{
            display: flex; justify-content: center; gap: 20px;
            margin-bottom: 20px; flex-wrap: wrap;
        }}
        .legend-item {{ display: flex; align-items: center; gap: 6px; font-size: 0.8rem; }}
        .legend-dot {{ width: 12px; height: 12px; border-radius: 2px; }}
        .dot-atk {{ background: #f85149; }}
        .dot-def {{ background: #58a6ff; }}
        .dot-eff {{ background: #3fb950; }}
        .dot-agg {{ background: #d29922; }}

        .controls {{ text-align: center; margin-bottom: 20px; }}
        .controls select {{
            padding: 6px 14px; border-radius: 6px; border: 1px solid #30363d;
            background: #161b22; color: #e6edf3; font-size: 0.85rem; cursor: pointer;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 16px; max-width: 1400px; margin: 0 auto;
        }}
        .card {{
            background: #161b22; border: 1px solid #30363d; border-radius: 10px;
            padding: 18px; transition: transform 0.2s;
        }}
        .card:hover {{ transform: translateY(-2px); border-color: #58a6ff; }}
        .card-top {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }}
        .team-name {{ font-weight: 600; font-size: 1rem; }}
        .overall-badge {{
            font-size: 0.75rem; font-weight: 700; padding: 3px 8px;
            border-radius: 10px; background: rgba(88, 166, 255, 0.15); color: #58a6ff;
        }}

        .stats-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
        .stat-block {{ text-align: center; }}
        .stat-label {{ font-size: 0.65rem; color: #8b949e; text-transform: uppercase; letter-spacing: 0.5px; }}
        .stat-value {{ font-size: 1.4rem; font-weight: 700; margin-top: 2px; }}
        .stat-atk {{ color: #f85149; }}
        .stat-def {{ color: #58a6ff; }}
        .stat-eff {{ color: #3fb950; }}
        .stat-agg {{ color: #d29922; }}

        .bar-section {{ margin-top: 12px; }}
        .mini-bar-row {{ display: flex; align-items: center; margin-bottom: 5px; }}
        .mini-label {{ width: 35px; font-size: 0.7rem; color: #8b949e; font-weight: 600; }}
        .mini-bar-bg {{ flex: 1; height: 8px; background: #21262d; border-radius: 4px; overflow: hidden; }}
        .mini-bar {{ height: 100%; border-radius: 4px; transition: width 0.5s ease; }}
        .mini-bar-atk {{ background: linear-gradient(90deg, #f85149, #da3633); }}
        .mini-bar-def {{ background: linear-gradient(90deg, #58a6ff, #1f6feb); }}
        .mini-bar-eff {{ background: linear-gradient(90deg, #3fb950, #238636); }}
        .mini-bar-agg {{ background: linear-gradient(90deg, #d29922, #9e6a03); }}

        .meta {{ font-size: 0.68rem; color: #484f58; margin-top: 8px; text-align: right; }}
    </style>
</head>
<body>
    <h1>⚽ World Cup 2026 — Team Ratings</h1>
    <p class="subtitle">ATK / DEF / EFF / AGG — Matchday 1 Performance Ratings</p>

    <div class="legend">
        <div class="legend-item"><div class="legend-dot dot-atk"></div>ATK (Attack Power)</div>
        <div class="legend-item"><div class="legend-dot dot-def"></div>DEF (Defensive Solidity)</div>
        <div class="legend-item"><div class="legend-dot dot-eff"></div>EFF (Efficiency)</div>
        <div class="legend-item"><div class="legend-dot dot-agg"></div>AGG (Aggression)</div>
    </div>

    <div class="controls">
        <label>Sort by: </label>
        <select id="sortSelect" onchange="sortCards()">
            <option value="overall">Overall</option>
            <option value="atk">ATK</option>
            <option value="def">DEF</option>
            <option value="eff">EFF</option>
            <option value="agg">AGG</option>
            <option value="name">Name</option>
        </select>
    </div>

    <div class="grid" id="grid"></div>

    <script>
    const teams = [
{js_array}
    ];

    function createCard(t, rank) {{
        const card = document.createElement('div');
        card.className = 'card';
        card.innerHTML = `
            <div class="card-top">
                <span class="team-name">#${{rank}} ${{t.name}}</span>
                <span class="overall-badge">${{t.overall}}</span>
            </div>
            <div class="stats-grid">
                <div class="stat-block"><div class="stat-label">ATK</div><div class="stat-value stat-atk">${{t.atk}}</div></div>
                <div class="stat-block"><div class="stat-label">DEF</div><div class="stat-value stat-def">${{t.def}}</div></div>
                <div class="stat-block"><div class="stat-label">EFF</div><div class="stat-value stat-eff">${{t.eff}}</div></div>
                <div class="stat-block"><div class="stat-label">AGG</div><div class="stat-value stat-agg">${{t.agg}}</div></div>
            </div>
            <div class="bar-section">
                <div class="mini-bar-row"><span class="mini-label">ATK</span><div class="mini-bar-bg"><div class="mini-bar mini-bar-atk" style="width:${{t.atk}}%"></div></div></div>
                <div class="mini-bar-row"><span class="mini-label">DEF</span><div class="mini-bar-bg"><div class="mini-bar mini-bar-def" style="width:${{t.def}}%"></div></div></div>
                <div class="mini-bar-row"><span class="mini-label">EFF</span><div class="mini-bar-bg"><div class="mini-bar mini-bar-eff" style="width:${{t.eff}}%"></div></div></div>
                <div class="mini-bar-row"><span class="mini-label">AGG</span><div class="mini-bar-bg"><div class="mini-bar mini-bar-agg" style="width:${{t.agg}}%"></div></div></div>
            </div>
            <div class="meta">${{t.goals}} goals scored · ${{t.conceded}} conceded · ${{t.possession}}% poss · ${{t.shotAcc}}% shot acc</div>
        `;
        return card;
    }}

    function renderCards(sorted) {{
        const grid = document.getElementById('grid');
        grid.innerHTML = '';
        sorted.forEach((t, i) => grid.appendChild(createCard(t, i + 1)));
    }}

    function sortCards() {{
        const sortBy = document.getElementById('sortSelect').value;
        let sorted = [...teams];
        switch(sortBy) {{
            case 'overall': sorted.sort((a, b) => b.overall - a.overall); break;
            case 'atk': sorted.sort((a, b) => b.atk - a.atk); break;
            case 'def': sorted.sort((a, b) => b.def - a.def); break;
            case 'eff': sorted.sort((a, b) => b.eff - a.eff); break;
            case 'agg': sorted.sort((a, b) => b.agg - a.agg); break;
            case 'name': sorted.sort((a, b) => a.name.localeCompare(b.name)); break;
        }}
        renderCards(sorted);
    }}

    sortCards();
    </script>
</body>
</html>'''

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  Dashboard HTML: {filepath}")


def main():
    print("=" * 60)
    print("  World Cup 2026 — Team Rating Calculator")
    print("=" * 60)

    # Step 1: Read all team data
    print("\n[1] Reading team CSVs...")
    teams = get_all_team_files()
    all_teams_data = {}
    for team in teams:
        matches = read_team_csv(team)
        if matches:
            all_teams_data[team] = matches

    print(f"    Found {len(all_teams_data)} team files")

    # Step 2: Compute ratings with cross-referencing
    print("\n[2] Computing ratings (cross-referencing opponents)...")
    all_ratings = {}
    for team, matches in all_teams_data.items():
        ratings = compute_ratings(team, matches, all_teams_data)
        if ratings:
            all_ratings[team] = ratings
            print(f"    {team:30s} → ATK:{ratings['ATK']:5.1f}  DEF:{ratings['DEF']:5.1f}  EFF:{ratings['EFF']:5.1f}  AGG:{ratings['AGG']:5.1f}  OVR:{ratings['overall']:5.1f}")

    print(f"\n    Rated {len(all_ratings)} teams (skipped {len(all_teams_data) - len(all_ratings)} with no played matches)")

    # Step 3: Update individual team CSVs
    print("\n[3] Updating team CSVs with ATK/DEF/EFF/AGG columns...")
    for team in all_teams_data:
        ratings = all_ratings.get(team)
        update_team_csv(team, ratings)
    print("    Done.")

    # Step 4: Write master ratings CSV
    print("\n[4] Writing master ratings file...")
    write_ratings_csv(all_ratings)

    # Step 5: Generate HTML dashboard
    print("\n[5] Generating ratings dashboard...")
    generate_html(all_ratings)

    print("\n" + "=" * 60)
    print("  Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
