"""
World Cup 2026 — Advanced Stats Dashboard Builder

Reads the expanded team CSVs and produces a clean HTML dashboard that distills
120+ raw stats into 6 intuitive composite dimensions per team:

  1. FINISHING    — How clinical (xG vs actual goals, shot accuracy, big chances)
  2. CREATION    — How dangerous in buildup (xA, chances created, final 3rd entries)
  3. CONTROL     — How dominant on the ball (possession, pass accuracy, PPDA)
  4. DEFENSE     — How solid at the back (xG conceded, tackles, interceptions)
  5. PHYSICALITY — How combative (duels won, aerials, fouls, cards)
  6. PRESSING    — How intense off the ball (PPDA, ball recoveries, poss won in att 3rd)

Each dimension is scaled 0-100. Simple radar charts + bar comparisons.
"""

import csv
import os
import json
from statistics import mean

# Resolve paths relative to this script's location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.environ.get("REPO_DIR", SCRIPT_DIR)

DATA_DIR = os.path.join(REPO_DIR, "data")
PUBLIC_DIR = os.path.join(REPO_DIR, "public")
OUTPUT_FILE = os.path.join(PUBLIC_DIR, "dashboard.html")

SKIP_FILES = {
    "team_ratings.csv", "qualifier_features.csv", "goalscorers.csv",
    "results.csv", "shootouts.csv", "team_rankings_2026.csv",
    "team_trends_2026.csv"
}


def parse_float(val):
    if val is None or str(val).strip() == "":
        return None
    try:
        return float(str(val).replace("%", "").strip())
    except ValueError:
        return None


def safe_mean(values):
    cleaned = [v for v in values if v is not None]
    return mean(cleaned) if cleaned else 0


def read_all_teams():
    """Read all team CSVs and return {team_name: [row_dicts]}."""
    teams = {}
    for f in sorted(os.listdir(DATA_DIR)):
        if not f.endswith(".csv") or f in SKIP_FILES:
            continue
        filepath = os.path.join(DATA_DIR, f)
        team_name = f.replace(".csv", "")
        with open(filepath, "r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = [r for r in reader if r.get("Goals", "").strip()]
        if rows:
            teams[team_name] = rows
    return teams


def compute_dimensions(team_name, matches):
    """
    Compute 6 composite dimensions from raw stats.
    Returns dict with raw averages and normalized 0-100 scores.
    """
    # Collect per-match values
    goals = [parse_float(m.get("Goals")) for m in matches]
    xg = [parse_float(m.get("xG")) for m in matches]
    sot_pct = [parse_float(m.get("Shot Accuracy")) for m in matches]
    big_created = [parse_float(m.get("Big chances created")) for m in matches]
    big_missed = [parse_float(m.get("Big chances missed")) for m in matches]

    xa = [parse_float(m.get("xA")) for m in matches]
    final_third = [parse_float(m.get("Final third entries")) for m in matches]
    pen_area = [parse_float(m.get("Penalty area entries")) for m in matches]
    shot_assists = [parse_float(m.get("Shot assists")) for m in matches]
    through_balls = [parse_float(m.get("Accurate through balls")) for m in matches]

    possession = [parse_float(m.get("Possession")) for m in matches]
    pass_acc = [parse_float(m.get("Pass Accuracy")) for m in matches]
    passes = [parse_float(m.get("Passes")) for m in matches]
    touches = [parse_float(m.get("Touches")) for m in matches]

    xg_conceded = [parse_float(m.get("xG conceded")) for m in matches]
    goals_conceded = [parse_float(m.get("Goals conceded")) for m in matches]
    tackles_won = [parse_float(m.get("Tackles won")) for m in matches]
    interceptions = [parse_float(m.get("Interceptions")) for m in matches]
    clearances = [parse_float(m.get("Effective clearances")) for m in matches]
    blocked = [parse_float(m.get("Blocked shots")) for m in matches]

    duels_won = [parse_float(m.get("Duels won")) for m in matches]
    duels_total = [parse_float(m.get("Duels")) for m in matches]
    aerials_won = [parse_float(m.get("Aerials won")) for m in matches]
    fouls_committed = [parse_float(m.get("Fouls committed")) for m in matches]

    ppda = [parse_float(m.get("PPDA")) for m in matches]
    ball_recoveries = [parse_float(m.get("Ball recoveries")) for m in matches]
    poss_att = [parse_float(m.get("Poss won att 3rd")) for m in matches]
    poss_mid = [parse_float(m.get("Poss won mid 3rd")) for m in matches]

    # Raw averages
    avg_goals = safe_mean(goals)
    avg_xg = safe_mean(xg)
    avg_sot_pct = safe_mean(sot_pct)
    avg_big_created = safe_mean(big_created)
    avg_big_missed = safe_mean(big_missed)
    avg_xa = safe_mean(xa)
    avg_final_third = safe_mean(final_third)
    avg_pen_area = safe_mean(pen_area)
    avg_shot_assists = safe_mean(shot_assists)
    avg_possession = safe_mean(possession)
    avg_pass_acc = safe_mean(pass_acc)
    avg_passes = safe_mean(passes)
    avg_touches = safe_mean(touches)
    avg_xg_conceded = safe_mean(xg_conceded)
    avg_goals_conceded = safe_mean(goals_conceded)
    avg_tackles = safe_mean(tackles_won)
    avg_interceptions = safe_mean(interceptions)
    avg_clearances = safe_mean(clearances)
    avg_blocked = safe_mean(blocked)
    avg_duels_won = safe_mean(duels_won)
    avg_duels = safe_mean(duels_total)
    avg_aerials = safe_mean(aerials_won)
    avg_fouls = safe_mean(fouls_committed)
    avg_ppda = safe_mean(ppda)
    avg_recoveries = safe_mean(ball_recoveries)
    avg_poss_att = safe_mean(poss_att)
    avg_poss_mid = safe_mean(poss_mid)

    return {
        "team": team_name,
        "matches": len(matches),
        "_matches": matches,  # Keep raw rows for consistency calculation
        # Raw values for tooltips
        "avg_goals": round(avg_goals, 2),
        "avg_xg": round(avg_xg, 2),
        "avg_sot_pct": round(avg_sot_pct, 1),
        "avg_xa": round(avg_xa, 2),
        "avg_final_third": round(avg_final_third, 1),
        "avg_pen_area": round(avg_pen_area, 1),
        "avg_possession": round(avg_possession, 1),
        "avg_pass_acc": round(avg_pass_acc, 1),
        "avg_xg_conceded": round(avg_xg_conceded, 2),
        "avg_goals_conceded": round(avg_goals_conceded, 2),
        "avg_tackles": round(avg_tackles, 1),
        "avg_interceptions": round(avg_interceptions, 1),
        "avg_duels_won": round(avg_duels_won, 1),
        "avg_aerials": round(avg_aerials, 1),
        "avg_ppda": round(avg_ppda, 1),
        "avg_recoveries": round(avg_recoveries, 1),
        "avg_poss_att": round(avg_poss_att, 1),
        # Components for normalization
        "_finishing_raw": {
            "goals_over_xg": avg_goals - avg_xg if avg_xg > 0 else 0,
            "sot_pct": avg_sot_pct,
            "big_conversion": (avg_big_created - avg_big_missed) / max(avg_big_created, 1),
            "goals_per_match": avg_goals,
        },
        "_creation_raw": {
            "xa": avg_xa,
            "final_third": avg_final_third,
            "pen_area": avg_pen_area,
            "shot_assists": avg_shot_assists,
            "big_created": avg_big_created,
        },
        "_control_raw": {
            "possession": avg_possession,
            "pass_acc": avg_pass_acc,
            "passes": avg_passes,
            "touches": avg_touches,
        },
        "_defense_raw": {
            "xg_conceded": avg_xg_conceded,
            "goals_conceded": avg_goals_conceded,
            "tackles": avg_tackles,
            "interceptions": avg_interceptions,
            "clearances": avg_clearances,
            "blocked": avg_blocked,
        },
        "_physicality_raw": {
            "duels_won": avg_duels_won,
            "duel_pct": avg_duels_won / max(avg_duels, 1) * 100,
            "aerials": avg_aerials,
            "fouls": avg_fouls,
        },
        "_pressing_raw": {
            "ppda": avg_ppda,
            "recoveries": avg_recoveries,
            "poss_att": avg_poss_att,
            "poss_mid": avg_poss_mid,
        },
    }


def compute_match_score(match, dim):
    """Compute a single dimension's raw score for one match row."""
    def pf(key):
        v = parse_float(match.get(key))
        return v if v is not None else 0

    if dim == "finishing":
        goals = pf("Goals")
        xg = pf("xG")
        sot_pct = pf("Shot Accuracy")
        big_c = pf("Big chances created")
        big_m = pf("Big chances missed")
        big_conv = (big_c - big_m) / max(big_c, 1) if big_c else 0
        return (
            goals * 15 +
            (goals - xg) * 10 +
            sot_pct * 0.3 +
            big_conv * 15
        )
    elif dim == "creation":
        return (
            pf("xA") * 20 +
            pf("Final third entries") * 0.5 +
            pf("Penalty area entries") * 1.0 +
            pf("Shot assists") * 3 +
            pf("Big chances created") * 8
        )
    elif dim == "control":
        return (
            pf("Possession") * 1.0 +
            pf("Pass Accuracy") * 0.5 +
            pf("Passes") * 0.05 +
            pf("Touches") * 0.03
        )
    elif dim == "defense":
        return (
            (3.0 - pf("xG conceded")) * 20 +
            (3.0 - pf("Goals conceded")) * 15 +
            pf("Tackles won") * 2 +
            pf("Interceptions") * 3 +
            pf("Blocked shots") * 3
        )
    elif dim == "physicality":
        duels_won = pf("Duels won")
        duels = pf("Duels")
        duel_pct = duels_won / max(duels, 1) * 100
        return (
            duels_won * 1.5 +
            duel_pct * 0.5 +
            pf("Aerials won") * 2 +
            pf("Fouls committed") * 1.5
        )
    elif dim == "pressing":
        ppda = pf("PPDA")
        return (
            max(0, (25 - ppda)) * 3 +
            pf("Ball recoveries") * 1.0 +
            pf("Poss won att 3rd") * 5 +
            pf("Poss won mid 3rd") * 2
        )
    return 0


def normalize_dimensions(all_team_data):
    """
    Normalize each dimension to 0-100 across all teams using min-max scaling.
    Also computes per-match consistency (coefficient of variation).
    """
    dims = ["finishing", "creation", "control", "defense", "physicality", "pressing"]

    # Compute raw composite scores first (from averages — same as before)
    for t in all_team_data:
        f = t["_finishing_raw"]
        t["_finishing_score"] = (
            f["goals_per_match"] * 15 +
            f["goals_over_xg"] * 10 +
            f["sot_pct"] * 0.3 +
            f["big_conversion"] * 15
        )

        c = t["_creation_raw"]
        t["_creation_score"] = (
            c["xa"] * 20 +
            c["final_third"] * 0.5 +
            c["pen_area"] * 1.0 +
            c["shot_assists"] * 3 +
            c["big_created"] * 8
        )

        ctrl = t["_control_raw"]
        t["_control_score"] = (
            ctrl["possession"] * 1.0 +
            ctrl["pass_acc"] * 0.5 +
            ctrl["passes"] * 0.05 +
            ctrl["touches"] * 0.03
        )

        d = t["_defense_raw"]
        t["_defense_score"] = (
            (3.0 - d["xg_conceded"]) * 20 +
            (3.0 - d["goals_conceded"]) * 15 +
            d["tackles"] * 2 +
            d["interceptions"] * 3 +
            d["blocked"] * 3
        )

        p = t["_physicality_raw"]
        t["_physicality_score"] = (
            p["duels_won"] * 1.5 +
            p["duel_pct"] * 0.5 +
            p["aerials"] * 2 +
            p["fouls"] * 1.5
        )

        pr = t["_pressing_raw"]
        t["_pressing_score"] = (
            max(0, (25 - pr["ppda"])) * 3 +
            pr["recoveries"] * 1.0 +
            pr["poss_att"] * 5 +
            pr["poss_mid"] * 2
        )

    # Min-max normalize each dimension to 0-100
    for dim in dims:
        key = f"_{dim}_score"
        values = [t[key] for t in all_team_data]
        min_val = min(values)
        max_val = max(values)
        spread = max_val - min_val if max_val != min_val else 1

        for t in all_team_data:
            t[dim] = round((t[key] - min_val) / spread * 100, 1)

    # Compute overall
    for t in all_team_data:
        t["overall"] = round(mean([t[dim] for dim in dims]), 1)

    # === CONSISTENCY: per-match variance for each dimension ===
    # For each team, compute each dimension's raw score per match,
    # then measure stability as 1 - normalized_CV (coefficient of variation).
    # consistency = 100 means identical performance every match.
    # consistency = 0 means wildly different match-to-match.
    for t in all_team_data:
        matches = t.get("_matches", [])
        if len(matches) < 2:
            # Can't measure consistency with 1 match
            for dim in dims:
                t[f"{dim}_consistency"] = None
            t["consistency"] = None
            continue

        dim_consistencies = []
        for dim in dims:
            per_match_scores = [compute_match_score(m, dim) for m in matches]
            avg = mean(per_match_scores) if per_match_scores else 0
            if avg != 0 and len(per_match_scores) > 1:
                std = (sum((x - avg) ** 2 for x in per_match_scores) / len(per_match_scores)) ** 0.5
                cv = std / abs(avg)  # coefficient of variation
                # Clamp CV to [0, 2] range then invert to 0-100
                consistency = max(0, min(100, (1 - cv / 2) * 100))
            else:
                consistency = 100  # no variance = perfectly consistent
            t[f"{dim}_consistency"] = round(consistency, 1)
            dim_consistencies.append(consistency)

        t["consistency"] = round(mean(dim_consistencies), 1)

    return all_team_data


def generate_html(all_team_data):
    """Generate the HTML dashboard with radar charts."""
    sorted_teams = sorted(all_team_data, key=lambda x: x["overall"], reverse=True)

    # Build JS data
    js_items = []
    for t in sorted_teams:
        js_items.append(json.dumps({
            "name": t["team"],
            "matches": t["matches"],
            "overall": t["overall"],
            "finishing": t["finishing"],
            "creation": t["creation"],
            "control": t["control"],
            "defense": t["defense"],
            "physicality": t["physicality"],
            "pressing": t["pressing"],
            "consistency": t.get("consistency"),
            "finCon": t.get("finishing_consistency"),
            "creCon": t.get("creation_consistency"),
            "ctrlCon": t.get("control_consistency"),
            "defCon": t.get("defense_consistency"),
            "phyCon": t.get("physicality_consistency"),
            "prsCon": t.get("pressing_consistency"),
            # Tooltip raw stats
            "avgGoals": t["avg_goals"],
            "avgXG": t["avg_xg"],
            "avgXA": t["avg_xa"],
            "avgPoss": t["avg_possession"],
            "avgPassAcc": t["avg_pass_acc"],
            "avgXGC": t["avg_xg_conceded"],
            "avgTackles": t["avg_tackles"],
            "avgPPDA": t["avg_ppda"],
            "avgRecoveries": t["avg_recoveries"],
            "avgDuelsWon": t["avg_duels_won"],
        }))

    js_array = ",\n        ".join(js_items)

    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>World Cup 2026 — Advanced Analytics Dashboard</title>
    <meta name="description" content="World Cup 2026 team analytics: 6 composite dimensions from 120+ ESPN match stats, updated daily.">
    <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚽</text></svg>">
    <style>
        :root {
            --wc-green: #3CAC3B;
            --wc-blue: #2A398D;
            --wc-red: #E61D25;
            --wc-light-gray: #D1D4D1;
            --wc-dark-gray: #474A4A;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #FAFAFA;
            color: #2D2D2D;
            padding: 24px;
            min-height: 100vh;
        }
        h1 { text-align: center; font-size: 1.8rem; color: var(--wc-blue); margin-bottom: 4px; }
        .subtitle { text-align: center; color: #5F6368; font-size: 0.85rem; margin-bottom: 20px; }

        .controls {
            display: flex; justify-content: center; gap: 12px;
            margin-bottom: 20px; flex-wrap: wrap; align-items: center;
        }
        .controls select, .controls input {
            padding: 6px 12px; border-radius: 6px; border: 1px solid #E2E4E2;
            background: #FFFFFF; color: #2D2D2D; font-size: 0.8rem;
        }
        .controls input { width: 180px; }
        .controls input:focus, .controls select:focus { outline: 2px solid var(--wc-blue); border-color: var(--wc-blue); }
        .controls label { font-size: 0.8rem; color: #5F6368; }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 14px; max-width: 1600px; margin: 0 auto;
        }
        .card {
            background: #FFFFFF; border: 1px solid #E2E4E2; border-radius: 10px;
            padding: 16px; transition: all 0.2s; border-top: 3px solid var(--wc-green);
        }
        .card:hover { border-color: var(--wc-blue); transform: translateY(-1px); box-shadow: 0 4px 12px rgba(42,57,141,0.08); }
        .card-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 10px;
        }
        .team-name { font-weight: 600; font-size: 0.95rem; color: #2D2D2D; }
        .rank-badge {
            font-size: 0.7rem; font-weight: 700; padding: 2px 8px;
            border-radius: 10px; background: rgba(42,57,141,0.08); color: var(--wc-blue);
        }

        .radar-wrap { display: flex; justify-content: center; margin: 8px 0; }
        canvas.radar { width: 180px; height: 180px; }

        .dim-bars { margin-top: 8px; }
        .dim-row {
            display: flex; align-items: center; margin-bottom: 4px;
            font-size: 0.7rem;
        }
        .dim-label { width: 75px; color: #5F6368; font-weight: 500; }
        .dim-bar-bg {
            flex: 1; height: 7px; background: #ECEEED;
            border-radius: 4px; overflow: hidden; position: relative;
        }
        .dim-bar {
            height: 100%; border-radius: 4px;
            transition: width 0.4s ease;
        }
        .dim-val { width: 32px; text-align: right; color: #8A8F94; font-size: 0.65rem; }
        .con-dot {
            width: 7px; height: 7px; border-radius: 50%; margin-left: 4px;
            display: inline-block; flex-shrink: 0;
        }
        .con-high { background: var(--wc-green); }
        .con-med { background: #E6A817; }
        .con-low { background: var(--wc-red); }
        .con-na { background: var(--wc-light-gray); }

        .consistency-row {
            display: flex; align-items: center; justify-content: space-between;
            margin-top: 8px; padding-top: 6px; border-top: 1px solid #E2E4E2;
            font-size: 0.68rem;
        }
        .con-label { color: #8A8F94; }
        .con-badge {
            padding: 2px 7px; border-radius: 8px; font-weight: 600; font-size: 0.65rem;
        }
        .con-badge-high { background: rgba(60,172,59,0.1); color: #2D8A2C; }
        .con-badge-med { background: rgba(230,168,23,0.1); color: #B8860B; }
        .con-badge-low { background: rgba(230,29,37,0.1); color: #C41920; }
        .con-badge-na { background: rgba(209,212,209,0.3); color: #8A8F94; }

        .bar-finishing { background: linear-gradient(90deg, #E61D25, #C41920); }
        .bar-creation { background: linear-gradient(90deg, #2A398D, #1E2A6B); }
        .bar-control { background: linear-gradient(90deg, #3CAC3B, #2D8A2C); }
        .bar-defense { background: linear-gradient(90deg, #5B7EC2, #3A5CA0); }
        .bar-physicality { background: linear-gradient(90deg, #E67E22, #D35400); }
        .bar-pressing { background: linear-gradient(90deg, #8E44AD, #6C3483); }

        .meta-row {
            display: flex; justify-content: space-between;
            font-size: 0.63rem; color: #8A8F94; margin-top: 6px;
            border-top: 1px solid #E2E4E2; padding-top: 6px;
        }

        .legend {
            display: flex; justify-content: center; gap: 16px;
            margin-bottom: 16px; flex-wrap: wrap;
        }
        .legend-item { display: flex; align-items: center; gap: 5px; font-size: 0.72rem; color: #5F6368; }
        .legend-dot { width: 10px; height: 10px; border-radius: 2px; }
        .dot-fin { background: #E61D25; }
        .dot-cre { background: #2A398D; }
        .dot-ctrl { background: #3CAC3B; }
        .dot-def { background: #5B7EC2; }
        .dot-phy { background: #E67E22; }
        .dot-press { background: #8E44AD; }
    </style>
</head>
<body>
    <h1>⚽ World Cup 2026 — Advanced Analytics</h1>
    <p class="subtitle">6 dimensions derived from 120+ ESPN match stats · xG · PPDA · Duels · Pressing zones</p>

    <div class="legend">
        <div class="legend-item"><div class="legend-dot dot-fin"></div>Finishing</div>
        <div class="legend-item"><div class="legend-dot dot-cre"></div>Creation</div>
        <div class="legend-item"><div class="legend-dot dot-ctrl"></div>Control</div>
        <div class="legend-item"><div class="legend-dot dot-def"></div>Defense</div>
        <div class="legend-item"><div class="legend-dot dot-phy"></div>Physicality</div>
        <div class="legend-item"><div class="legend-dot dot-press"></div>Pressing</div>
    </div>

    <div class="controls">
        <label>Sort:</label>
        <select id="sortBy" onchange="render()">
            <option value="overall">Overall</option>
            <option value="finishing">Finishing</option>
            <option value="creation">Creation</option>
            <option value="control">Control</option>
            <option value="defense">Defense</option>
            <option value="physicality">Physicality</option>
            <option value="pressing">Pressing</option>
            <option value="consistency">Consistency</option>
            <option value="name">Name</option>
        </select>
        <label>Filter:</label>
        <input type="text" id="filter" placeholder="Type team name..." oninput="render()">
    </div>

    <div class="grid" id="grid"></div>

<script>
const teams = [
        ''' + js_array + '''
    ];

const DIMS = ["finishing","creation","control","defense","physicality","pressing"];
const COLORS = ["#E61D25","#2A398D","#3CAC3B","#5B7EC2","#E67E22","#8E44AD"];
const BAR_CLASSES = ["bar-finishing","bar-creation","bar-control","bar-defense","bar-physicality","bar-pressing"];
const DIM_LABELS = ["Finishing","Creation","Control","Defense","Physical","Pressing"];

// Country color schemes: [primary, secondary] — based on national football team kit colors
const COUNTRY_COLORS = {
    "Argentina":["#75AADB","#FFFFFF"],  // Albiceleste light blue & white
    "Algeria":["#006233","#FFFFFF"],    // Green & white
    "Australia":["#FBB917","#003580"],  // Socceroos gold & green/navy
    "Austria":["#ED2939","#FFFFFF"],    // Red & white
    "Belgium":["#ED2939","#000000"],    // Red Devils red & black
    "Bosnia and Herzegovina":["#002395","#FFFFFF"],  // Blue & white
    "Brazil":["#FEDF00","#009B3A"],    // Canarinha yellow & green
    "Canada":["#FF0000","#FFFFFF"],     // Red & white
    "Cape Verde":["#003893","#CF2027"],  // Blue & red
    "Colombia":["#FCD116","#003893"],   // Yellow & blue
    "Croatia":["#FF0000","#FFFFFF"],    // Red & white checks
    "Curacao":["#002B7F","#F9E814"],   // Blue & yellow
    "Czech Republic":["#D7141A","#FFFFFF"],  // Red & white
    "DR Congo":["#007FFF","#CE1021"],  // Blue & red
    "Ecuador":["#FFD100","#003DA5"],   // Yellow & blue
    "Egypt":["#CE1126","#FFFFFF"],     // Pharaohs red & white
    "England":["#FFFFFF","#CF081F"],   // Three Lions white & red
    "France":["#002395","#FFFFFF"],    // Les Bleus navy & white
    "Germany":["#FFFFFF","#000000"],   // Die Mannschaft white & black
    "Ghana":["#FFFFFF","#006B3F"],     // Black Stars white & green
    "Haiti":["#00209F","#D21034"],     // Blue & red
    "Iran":["#FFFFFF","#CE1126"],      // Team Melli white & red
    "Iraq":["#007A3D","#FFFFFF"],      // Green & white
    "Ivory Coast":["#FF8200","#009A44"],  // Elephants orange & green
    "Japan":["#002FA7","#FFFFFF"],     // Samurai Blue & white
    "Jordan":["#CE1126","#FFFFFF"],    // Red & white
    "Mexico":["#006341","#FFFFFF"],    // El Tri green & white
    "Morocco":["#C1272D","#006233"],   // Atlas Lions red & green
    "Netherlands":["#FF6600","#FFFFFF"],  // Oranje & white
    "New Zealand":["#FFFFFF","#000000"],  // All Whites white & black
    "Norway":["#BA0C2F","#FFFFFF"],    // Red & white
    "Panama":["#DA121A","#FFFFFF"],    // Red & white
    "Paraguay":["#DA121A","#FFFFFF"],  // Red & white stripes
    "Portugal":["#DA291C","#006600"], // Selecao red & green
    "Qatar":["#8D1B3D","#FFFFFF"],    // Maroon & white
    "Saudi Arabia":["#006C35","#FFFFFF"],  // Green Falcons green & white
    "Scotland":["#003078","#FFFFFF"],  // Navy & white
    "Senegal":["#FFFFFF","#006A4E"],   // Teranga Lions white & green
    "South Africa":["#007749","#FFB81C"],  // Bafana Bafana green & gold
    "South Korea":["#CD2E3A","#FFFFFF"],  // Red Warriors & white
    "Spain":["#AA151B","#F1BF00"],    // La Roja red & gold
    "Sweden":["#FECC00","#006AA7"],   // Blågult yellow & blue
    "Switzerland":["#FF0000","#FFFFFF"],  // Nati red & white
    "Tunisia":["#E70013","#FFFFFF"],   // Eagles of Carthage red & white
    "Turkey":["#E30A17","#FFFFFF"],    // Crescent Stars red & white
    "Uruguay":["#7FC4E6","#FFFFFF"],   // Celeste light blue & white
    "USA":["#002868","#BF0A30"],       // Stars & Stripes navy & red
    "Uzbekistan":["#1EB53A","#FFFFFF"],  // White Wolves green & white
};

function getTeamColors(name) {
    const c = COUNTRY_COLORS[name] || ["#3CAC3B","#2A398D"];
    // If primary is white/very light, use secondary for visibility on white bg
    const hex = c[0].replace("#","");
    const r = parseInt(hex.substring(0,2),16);
    const g = parseInt(hex.substring(2,4),16);
    const b = parseInt(hex.substring(4,6),16);
    const luminance = (0.299*r + 0.587*g + 0.114*b);
    if (luminance > 200) return [c[1], c[0]];
    return c;
}

function drawRadar(canvas, team) {
    const ctx = canvas.getContext("2d");
    const w = canvas.width, h = canvas.height;
    const cx = w/2, cy = h/2, r = Math.min(w,h)/2 - 20;
    const [primary] = getTeamColors(team.name);

    ctx.clearRect(0, 0, w, h);

    // Draw grid rings
    for (let ring = 0.25; ring <= 1; ring += 0.25) {
        ctx.beginPath();
        for (let i = 0; i <= 6; i++) {
            const angle = (Math.PI * 2 / 6) * i - Math.PI/2;
            const x = cx + Math.cos(angle) * r * ring;
            const y = cy + Math.sin(angle) * r * ring;
            if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.strokeStyle = "rgba(209,212,209,0.7)";
        ctx.lineWidth = 0.5;
        ctx.stroke();
    }

    // Draw axes
    for (let i = 0; i < 6; i++) {
        const angle = (Math.PI * 2 / 6) * i - Math.PI/2;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(angle) * r, cy + Math.sin(angle) * r);
        ctx.strokeStyle = "rgba(209,212,209,0.5)";
        ctx.lineWidth = 0.5;
        ctx.stroke();
    }

    // Draw data polygon with team color
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
        const angle = (Math.PI * 2 / 6) * i - Math.PI/2;
        const val = team[DIMS[i]] / 100;
        const x = cx + Math.cos(angle) * r * val;
        const y = cy + Math.sin(angle) * r * val;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.fillStyle = primary + "22";
    ctx.fill();
    ctx.strokeStyle = primary;
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Draw dots + labels
    for (let i = 0; i < 6; i++) {
        const angle = (Math.PI * 2 / 6) * i - Math.PI/2;
        const val = team[DIMS[i]] / 100;
        const x = cx + Math.cos(angle) * r * val;
        const y = cy + Math.sin(angle) * r * val;

        ctx.beginPath();
        ctx.arc(x, y, 3, 0, Math.PI*2);
        ctx.fillStyle = COLORS[i];
        ctx.fill();

        // Labels
        const lx = cx + Math.cos(angle) * (r + 14);
        const ly = cy + Math.sin(angle) * (r + 14);
        ctx.font = "9px system-ui";
        ctx.fillStyle = "#5F6368";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(DIM_LABELS[i], lx, ly);
    }
}

function createCard(team, rank) {
    const card = document.createElement("div");
    card.className = "card";
    const [primary] = getTeamColors(team.name);
    card.style.borderTopColor = primary;

    const conKeys = ["finCon","creCon","ctrlCon","defCon","phyCon","prsCon"];

    let barsHtml = "";
    for (let i = 0; i < 6; i++) {
        const val = team[DIMS[i]];
        const con = team[conKeys[i]];
        let dotClass = "con-na";
        if (con !== null) {
            if (con >= 70) dotClass = "con-high";
            else if (con >= 40) dotClass = "con-med";
            else dotClass = "con-low";
        }
        barsHtml += `<div class="dim-row">
            <span class="dim-label">${DIM_LABELS[i]}</span>
            <div class="dim-bar-bg"><div class="dim-bar ${BAR_CLASSES[i]}" style="width:${val}%"></div></div>
            <span class="dim-val">${val}</span>
            <span class="con-dot ${dotClass}" title="${con !== null ? 'Consistency: ' + con + '%' : '1 match — no data'}"></span>
        </div>`;
    }

    // Overall consistency badge
    const con = team.consistency;
    let conBadge = "";
    if (con !== null) {
        let cls = "con-badge-med", label = "Mixed";
        if (con >= 70) { cls = "con-badge-high"; label = "Stable"; }
        else if (con < 40) { cls = "con-badge-low"; label = "Volatile"; }
        conBadge = `<div class="consistency-row">
            <span class="con-label">Consistency</span>
            <span class="con-badge ${cls}">${label} (${con}%)</span>
        </div>`;
    } else {
        conBadge = `<div class="consistency-row">
            <span class="con-label">Consistency</span>
            <span class="con-badge con-badge-na">1 match</span>
        </div>`;
    }

    card.innerHTML = `
        <div class="card-header">
            <span class="team-name">#${rank} ${team.name}</span>
            <span class="rank-badge">${team.overall}</span>
        </div>
        <div class="radar-wrap"><canvas class="radar" width="180" height="180"></canvas></div>
        <div class="dim-bars">${barsHtml}</div>
        ${conBadge}
        <div class="meta-row">
            <span>${team.avgGoals}g · ${team.avgXG}xG · ${team.avgXA}xA</span>
            <span>${team.avgPoss}% poss · ${team.avgPassAcc}% pass</span>
            <span>${team.avgXGC}xGC · PPDA ${team.avgPPDA}</span>
        </div>
    `;
    return card;
}

function render() {
    const sortBy = document.getElementById("sortBy").value;
    const filter = document.getElementById("filter").value.toLowerCase();

    let filtered = teams.filter(t => t.name.toLowerCase().includes(filter));

    if (sortBy === "name") {
        filtered.sort((a,b) => a.name.localeCompare(b.name));
    } else if (sortBy === "consistency") {
        filtered.sort((a,b) => (b.consistency ?? -1) - (a.consistency ?? -1));
    } else {
        filtered.sort((a,b) => b[sortBy] - a[sortBy]);
    }

    const grid = document.getElementById("grid");
    grid.innerHTML = "";

    filtered.forEach((t, i) => {
        const card = createCard(t, i + 1);
        grid.appendChild(card);
        const canvas = card.querySelector("canvas");
        drawRadar(canvas, t);
    });
}

render();
</script>
</body>
</html>'''

    os.makedirs(PUBLIC_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✓ Dashboard: {OUTPUT_FILE}")


def main():
    print("=" * 60)
    print("  World Cup 2026 — Advanced Analytics Dashboard")
    print("=" * 60)

    print("\n[1] Reading team CSVs...")
    teams = read_all_teams()
    print(f"    Found {len(teams)} teams with played matches")

    print("\n[2] Computing 6 dimensions per team...")
    all_data = []
    for team_name, matches in teams.items():
        data = compute_dimensions(team_name, matches)
        all_data.append(data)

    print("\n[3] Normalizing (min-max → 0-100)...")
    all_data = normalize_dimensions(all_data)

    # Print top 10
    sorted_data = sorted(all_data, key=lambda x: x["overall"], reverse=True)
    print("\n    Top 10:")
    for i, t in enumerate(sorted_data[:10], 1):
        print(f"    {i:2}. {t['team']:25s} OVR:{t['overall']:5.1f}  "
              f"FIN:{t['finishing']:4.1f} CRE:{t['creation']:4.1f} "
              f"CTR:{t['control']:4.1f} DEF:{t['defense']:4.1f} "
              f"PHY:{t['physicality']:4.1f} PRS:{t['pressing']:4.1f}")

    print("\n[4] Generating HTML dashboard...")
    generate_html(all_data)

    print("\n" + "=" * 60)
    print("  Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
