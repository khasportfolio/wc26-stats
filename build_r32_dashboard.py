"""
World Cup 2026 — Round of 32 Dashboard & Trend Analysis

Builds two pages:
  1. r32.html — Same 6-dimension analytics, normalized against only the
     32 qualified teams (not the full 48).
  2. trends.html — Per-match dimension trends across all games for each
     of the 32 qualified teams.

Reads qualified teams from data/qualified_r32.txt.
"""

import csv
import os
import json
import sys
from statistics import mean

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)  # Ensure html_templates can be imported
REPO_DIR = os.environ.get("REPO_DIR", SCRIPT_DIR)
DATA_DIR = os.path.join(REPO_DIR, "data")
PUBLIC_DIR = os.path.join(REPO_DIR, "public")

DIMS = ["finishing", "creation", "control", "defense", "physicality", "pressing"]


# ─── Utilities ───────────────────────────────────────────────────────────────

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


def read_qualified_teams():
    filepath = os.path.join(DATA_DIR, "qualified_r32.txt")
    teams = []
    if not os.path.exists(filepath):
        print("  WARNING: qualified_r32.txt not found!")
        return teams
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                teams.append(line)
    return teams


def read_team_matches(team_name):
    filepath = os.path.join(DATA_DIR, f"{team_name}.csv")
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return [r for r in reader if r.get("Goals", "").strip()]


# ─── Dimension scoring (same formulas as build_dashboard.py) ─────────────────

def compute_match_score(match, dim):
    def pf(key):
        v = parse_float(match.get(key))
        return v if v is not None else 0

    if dim == "finishing":
        goals = pf("Goals"); xg = pf("xG")
        sot_pct = pf("Shot Accuracy")
        big_c = pf("Big chances created"); big_m = pf("Big chances missed")
        big_conv = (big_c - big_m) / max(big_c, 1) if big_c else 0
        return goals * 15 + (goals - xg) * 10 + sot_pct * 0.3 + big_conv * 15
    elif dim == "creation":
        return (pf("xA") * 20 + pf("Final third entries") * 0.5 +
                pf("Penalty area entries") * 1.0 + pf("Shot assists") * 3 +
                pf("Big chances created") * 8)
    elif dim == "control":
        return (pf("Possession") * 1.0 + pf("Pass Accuracy") * 0.5 +
                pf("Passes") * 0.05 + pf("Touches") * 0.03)
    elif dim == "defense":
        return ((3.0 - pf("xG conceded")) * 20 + (3.0 - pf("Goals conceded")) * 15 +
                pf("Tackles won") * 2 + pf("Interceptions") * 3 + pf("Blocked shots") * 3)
    elif dim == "physicality":
        dw = pf("Duels won"); d = pf("Duels")
        return dw * 1.5 + (dw / max(d, 1) * 100) * 0.5 + pf("Aerials won") * 2 + pf("Fouls committed") * 1.5
    elif dim == "pressing":
        ppda = pf("PPDA")
        return (max(0, (25 - ppda)) * 3 + pf("Ball recoveries") * 1.0 +
                pf("Poss won att 3rd") * 5 + pf("Poss won mid 3rd") * 2)
    return 0


# ─── Team-level computation ──────────────────────────────────────────────────

def compute_team_dimensions(team_name, matches):
    per_match_scores = {dim: [] for dim in DIMS}
    for m in matches:
        for dim in DIMS:
            per_match_scores[dim].append(compute_match_score(m, dim))

    avg_scores = {f"_{dim}_score": safe_mean(per_match_scores[dim]) for dim in DIMS}

    return {
        "team": team_name,
        "matches": len(matches),
        "_matches": matches,
        "avg_goals": round(safe_mean([parse_float(m.get("Goals")) for m in matches]), 2),
        "avg_xg": round(safe_mean([parse_float(m.get("xG")) for m in matches]), 2),
        "avg_xa": round(safe_mean([parse_float(m.get("xA")) for m in matches]), 2),
        "avg_possession": round(safe_mean([parse_float(m.get("Possession")) for m in matches]), 1),
        "avg_pass_acc": round(safe_mean([parse_float(m.get("Pass Accuracy")) for m in matches]), 1),
        "avg_xg_conceded": round(safe_mean([parse_float(m.get("xG conceded")) for m in matches]), 2),
        "avg_tackles": round(safe_mean([parse_float(m.get("Tackles won")) for m in matches]), 1),
        "avg_ppda": round(safe_mean([parse_float(m.get("PPDA")) for m in matches]), 1),
        "avg_recoveries": round(safe_mean([parse_float(m.get("Ball recoveries")) for m in matches]), 1),
        "avg_duels_won": round(safe_mean([parse_float(m.get("Duels won")) for m in matches]), 1),
        **avg_scores,
    }


def normalize_dimensions(all_team_data):
    for dim in DIMS:
        key = f"_{dim}_score"
        values = [t[key] for t in all_team_data]
        min_val, max_val = min(values), max(values)
        spread = max_val - min_val if max_val != min_val else 1
        for t in all_team_data:
            t[dim] = round((t[key] - min_val) / spread * 100, 1)

    for t in all_team_data:
        t["overall"] = round(mean([t[dim] for dim in DIMS]), 1)

    # Consistency (CV-based)
    for t in all_team_data:
        matches = t.get("_matches", [])
        if len(matches) < 2:
            for dim in DIMS:
                t[f"{dim}_consistency"] = None
            t["consistency"] = None
            continue
        dim_cons = []
        for dim in DIMS:
            scores = [compute_match_score(m, dim) for m in matches]
            avg = mean(scores)
            if avg != 0:
                std = (sum((x - avg)**2 for x in scores) / len(scores))**0.5
                con = max(0, min(100, (1 - (std / abs(avg)) / 2) * 100))
            else:
                con = 100
            t[f"{dim}_consistency"] = round(con, 1)
            dim_cons.append(con)
        t["consistency"] = round(mean(dim_cons), 1)

    return all_team_data


# ─── HTML Generation ─────────────────────────────────────────────────────────

def _nav_html(active):
    links = [("dashboard.html", "Group Stage"), ("r32.html", "Round of 32"), ("trends.html", "Trends"), ("bracket.html", "Bracket")]
    parts = []
    for url, label in links:
        cls = ' class="nav-link active"' if url == active else ' class="nav-link"'
        parts.append(f'<a href="{url}"{cls}>{label}</a>')
    return " · ".join(parts)


def write_r32_html(all_team_data):
    """Generate r32.html — the Round of 32 dashboard."""
    from html_templates import r32_html

    sorted_teams = sorted(all_team_data, key=lambda x: x["overall"], reverse=True)
    js_items = []
    for t in sorted_teams:
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
    nav = _nav_html("r32.html")

    filepath = os.path.join(PUBLIC_DIR, "r32.html")
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(r32_html(js_array, nav))
    print(f"  ✓ R32 Dashboard: {filepath}")


def write_trends_html(all_matches, global_mins, global_maxs):
    """Generate trends.html — per-match dimension evolution."""
    from html_templates import trends_html

    all_trends = {}
    for team_name, matches in sorted(all_matches.items()):
        trend = []
        for i, m in enumerate(matches):
            entry = {
                "match": i + 1,
                "opponent": m.get("Opponent", ""),
                "date": m.get("Date", ""),
                "goals": int(parse_float(m.get("Goals")) or 0),
                "conceded": int(parse_float(m.get("Goals conceded")) or 0),
            }
            for dim in DIMS:
                raw = compute_match_score(m, dim)
                mn = global_mins[dim]
                mx = global_maxs[dim]
                spread = mx - mn if mx != mn else 1
                entry[dim] = round((raw - mn) / spread * 100, 1)
            trend.append(entry)
        all_trends[team_name] = trend

    js_data = json.dumps(all_trends, indent=2)
    nav = _nav_html("trends.html")

    filepath = os.path.join(PUBLIC_DIR, "trends.html")
    os.makedirs(PUBLIC_DIR, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(trends_html(js_data, nav))
    print(f"  ✓ Trends Page: {filepath}")


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  World Cup 2026 — R32 Dashboard + Trends")
    print("=" * 60)

    # Read qualified teams
    print("\n[1] Reading qualified teams...")
    qualified = read_qualified_teams()
    print(f"    {len(qualified)} teams in qualified_r32.txt")

    # Read all match data
    print("\n[2] Reading match data...")
    all_matches = {}
    for team in qualified:
        matches = read_team_matches(team)
        if matches:
            all_matches[team] = matches
            print(f"    {team:30s} — {len(matches)} matches")
        else:
            print(f"    {team:30s} — NO DATA (skipped)")

    if not all_matches:
        print("\n  ERROR: No match data found. Exiting.")
        return

    # Compute dimensions (normalized across R32 pool only)
    print(f"\n[3] Computing dimensions ({len(all_matches)} teams)...")
    all_data = []
    for team_name, matches in all_matches.items():
        data = compute_team_dimensions(team_name, matches)
        if data:
            all_data.append(data)

    all_data = normalize_dimensions(all_data)

    sorted_data = sorted(all_data, key=lambda x: x["overall"], reverse=True)
    print("\n    Top 10:")
    for i, t in enumerate(sorted_data[:10], 1):
        print(f"    {i:2}. {t['team']:25s} OVR:{t['overall']:5.1f}")

    # Generate R32 page
    print("\n[4] Generating R32 dashboard...")
    write_r32_html(all_data)

    # Compute global min/max for trend normalization
    print("\n[5] Computing trends (global normalization)...")
    all_raw = {dim: [] for dim in DIMS}
    for matches in all_matches.values():
        for m in matches:
            for dim in DIMS:
                all_raw[dim].append(compute_match_score(m, dim))

    global_mins = {dim: min(scores) for dim, scores in all_raw.items()}
    global_maxs = {dim: max(scores) for dim, scores in all_raw.items()}

    # Generate trends page
    print("\n[6] Generating trends page...")
    write_trends_html(all_matches, global_mins, global_maxs)

    print("\n" + "=" * 60)
    print("  Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
