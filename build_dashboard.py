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
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: #0a0e14;
            color: #c9d1d9;
            padding: 24px;
            min-height: 100vh;
        }
        h1 { text-align: center; font-size: 1.8rem; color: #58a6ff; margin-bottom: 4px; }
        .subtitle { text-align: center; color: #6e7681; font-size: 0.85rem; margin-bottom: 20px; }

        .controls {
            display: flex; justify-content: center; gap: 12px;
            margin-bottom: 20px; flex-wrap: wrap; align-items: center;
        }
        .controls select, .controls input {
            padding: 6px 12px; border-radius: 6px; border: 1px solid #30363d;
            background: #161b22; color: #c9d1d9; font-size: 0.8rem;
        }
        .controls input { width: 180px; }
        .controls label { font-size: 0.8rem; color: #8b949e; }

        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 14px; max-width: 1600px; margin: 0 auto;
        }
        .card {
            background: #161b22; border: 1px solid #21262d; border-radius: 10px;
            padding: 16px; transition: all 0.2s;
        }
        .card:hover { border-color: #58a6ff; transform: translateY(-1px); }
        .card-header {
            display: flex; justify-content: space-between; align-items: center;
            margin-bottom: 10px;
        }
        .team-name { font-weight: 600; font-size: 0.95rem; color: #e6edf3; }
        .rank-badge {
            font-size: 0.7rem; font-weight: 700; padding: 2px 8px;
            border-radius: 10px; background: rgba(88,166,255,0.12); color: #58a6ff;
        }

        .radar-wrap { display: flex; justify-content: center; margin: 8px 0; }
        canvas.radar { width: 180px; height: 180px; }

        .dim-bars { margin-top: 8px; }
        .dim-row {
            display: flex; align-items: center; margin-bottom: 4px;
            font-size: 0.7rem;
        }
        .dim-label { width: 75px; color: #8b949e; font-weight: 500; }
        .dim-bar-bg {
            flex: 1; height: 7px; background: #21262d;
            border-radius: 4px; overflow: hidden; position: relative;
        }
        .dim-bar {
            height: 100%; border-radius: 4px;
            transition: width 0.4s ease;
        }
        .dim-val { width: 32px; text-align: right; color: #6e7681; font-size: 0.65rem; }
        .con-dot {
            width: 7px; height: 7px; border-radius: 50%; margin-left: 4px;
            display: inline-block; flex-shrink: 0;
        }
        .con-high { background: #4ade80; }
        .con-med { background: #facc15; }
        .con-low { background: #f87171; }
        .con-na { background: #30363d; }

        .consistency-row {
            display: flex; align-items: center; justify-content: space-between;
            margin-top: 8px; padding-top: 6px; border-top: 1px solid #21262d;
            font-size: 0.68rem;
        }
        .con-label { color: #6e7681; }
        .con-badge {
            padding: 2px 7px; border-radius: 8px; font-weight: 600; font-size: 0.65rem;
        }
        .con-badge-high { background: rgba(74,222,128,0.12); color: #4ade80; }
        .con-badge-med { background: rgba(250,204,21,0.12); color: #facc15; }
        .con-badge-low { background: rgba(248,113,113,0.12); color: #f87171; }
        .con-badge-na { background: rgba(48,54,61,0.3); color: #484f58; }

        .bar-finishing { background: linear-gradient(90deg, #f97316, #ea580c); }
        .bar-creation { background: linear-gradient(90deg, #a78bfa, #7c3aed); }
        .bar-control { background: linear-gradient(90deg, #38bdf8, #0284c7); }
        .bar-defense { background: linear-gradient(90deg, #4ade80, #16a34a); }
        .bar-physicality { background: linear-gradient(90deg, #fb923c, #dc2626); }
        .bar-pressing { background: linear-gradient(90deg, #facc15, #ca8a04); }

        .meta-row {
            display: flex; justify-content: space-between;
            font-size: 0.63rem; color: #484f58; margin-top: 6px;
            border-top: 1px solid #21262d; padding-top: 6px;
        }

        .legend {
            display: flex; justify-content: center; gap: 16px;
            margin-bottom: 16px; flex-wrap: wrap;
        }
        .legend-item { display: flex; align-items: center; gap: 5px; font-size: 0.72rem; color: #8b949e; }
        .legend-dot { width: 10px; height: 10px; border-radius: 2px; }
        .dot-fin { background: #f97316; }
        .dot-cre { background: #a78bfa; }
        .dot-ctrl { background: #38bdf8; }
        .dot-def { background: #4ade80; }
        .dot-phy { background: #fb923c; }
        .dot-press { background: #facc15; }
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
const COLORS = ["#f97316","#a78bfa","#38bdf8","#4ade80","#fb923c","#facc15"];
const BAR_CLASSES = ["bar-finishing","bar-creation","bar-control","bar-defense","bar-physicality","bar-pressing"];
const DIM_LABELS = ["Finishing","Creation","Control","Defense","Physical","Pressing"];

function drawRadar(canvas, team) {
    const ctx = canvas.getContext("2d");
    const w = canvas.width, h = canvas.height;
    const cx = w/2, cy = h/2, r = Math.min(w,h)/2 - 20;

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
        ctx.strokeStyle = "rgba(48,54,61,0.6)";
        ctx.lineWidth = 0.5;
        ctx.stroke();
    }

    // Draw axes
    for (let i = 0; i < 6; i++) {
        const angle = (Math.PI * 2 / 6) * i - Math.PI/2;
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(cx + Math.cos(angle) * r, cy + Math.sin(angle) * r);
        ctx.strokeStyle = "rgba(48,54,61,0.4)";
        ctx.lineWidth = 0.5;
        ctx.stroke();
    }

    // Draw data polygon
    ctx.beginPath();
    for (let i = 0; i < 6; i++) {
        const angle = (Math.PI * 2 / 6) * i - Math.PI/2;
        const val = team[DIMS[i]] / 100;
        const x = cx + Math.cos(angle) * r * val;
        const y = cy + Math.sin(angle) * r * val;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
    }
    ctx.closePath();
    ctx.fillStyle = "rgba(88,166,255,0.15)";
    ctx.fill();
    ctx.strokeStyle = "rgba(88,166,255,0.8)";
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
        ctx.fillStyle = "#6e7681";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(DIM_LABELS[i], lx, ly);
    }
}

function createCard(team, rank) {
    const card = document.createElement("div");
    card.className = "card";

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
