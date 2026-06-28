"""
World Cup 2026 — Bracket Prediction & Visualization

Reads the bracket structure and team dimension scores, then:
1. Computes win probability for each R32 matchup based on stat comparison
2. Simulates the entire tournament bracket using those probabilities
3. Generates bracket.html with visual bracket + analysis

Win probability model:
  - Compare each team's 6 raw dimension scores (before normalization)
  - Weighted advantage: finishing (25%), defense (25%), control (20%),
    creation (15%), pressing (10%), physicality (5%)
  - Convert total advantage to probability via logistic function
"""

import csv
import os
import json
import math
from statistics import mean

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.environ.get("REPO_DIR", SCRIPT_DIR)
DATA_DIR = os.path.join(REPO_DIR, "data")
PUBLIC_DIR = os.path.join(REPO_DIR, "public")

DIMS = ["finishing", "creation", "control", "defense", "physicality", "pressing"]
# Weights for win probability (how much each dimension matters in knockout)
DIM_WEIGHTS = {
    "finishing": 0.25, "defense": 0.25, "control": 0.20,
    "creation": 0.15, "pressing": 0.10, "physicality": 0.05
}

import sys
sys.path.insert(0, SCRIPT_DIR)
from build_r32_dashboard import (
    read_team_matches, compute_match_score, safe_mean, parse_float, DIMS
)


def compute_team_raw_scores(team_name):
    """Compute average raw dimension scores for a team (unnormalized)."""
    matches = read_team_matches(team_name)
    if not matches:
        return None
    scores = {}
    for dim in DIMS:
        per_match = [compute_match_score(m, dim) for m in matches]
        scores[dim] = safe_mean(per_match)
    # Also store some key stats for display
    scores["goals_avg"] = safe_mean([parse_float(m.get("Goals")) for m in matches])
    scores["xg_avg"] = safe_mean([parse_float(m.get("xG")) for m in matches])
    scores["xgc_avg"] = safe_mean([parse_float(m.get("xG conceded")) for m in matches])
    scores["poss_avg"] = safe_mean([parse_float(m.get("Possession")) for m in matches])
    scores["matches"] = len(matches)
    return scores


def compute_win_probability(team_a_scores, team_b_scores):
    """
    Compute probability of team_a winning using logistic model.
    Returns (prob_a, prob_b, analysis_text).
    """
    if team_a_scores is None or team_b_scores is None:
        return 0.5, 0.5, "Insufficient data"

    # Compute weighted advantage
    total_advantage = 0
    dim_advantages = {}
    for dim in DIMS:
        diff = team_a_scores[dim] - team_b_scores[dim]
        # Normalize diff relative to the average magnitude
        avg_mag = (abs(team_a_scores[dim]) + abs(team_b_scores[dim])) / 2
        if avg_mag > 0:
            norm_diff = diff / avg_mag  # relative advantage (-1 to +1 range roughly)
        else:
            norm_diff = 0
        weighted = norm_diff * DIM_WEIGHTS[dim]
        total_advantage += weighted
        dim_advantages[dim] = norm_diff

    # Logistic function: sigmoid(k * advantage)
    # k controls sensitivity (higher = more decisive)
    k = 3.0
    prob_a = 1 / (1 + math.exp(-k * total_advantage))
    prob_b = 1 - prob_a

    return round(prob_a, 3), round(prob_b, 3), dim_advantages


def simulate_bracket(bracket, all_scores):
    """Simulate the full bracket using win probabilities. Returns results dict."""
    results = {}  # match_num -> {"winner", "prob_a", "prob_b", ...}

    def resolve_team(ref):
        """Resolve a team reference like 'W74' to the actual team name."""
        if ref.startswith("W"):
            match_num = int(ref[1:])
            if match_num in results:
                return results[match_num]["winner"]
        return ref

    # Process rounds in order
    for round_name in ["r32", "r16", "qf", "sf", "final"]:
        for match in bracket[round_name]:
            match_num = match["match"]
            team_a = resolve_team(match["team_a"])
            team_b = resolve_team(match["team_b"])

            if team_a == "TBD" or team_b == "TBD":
                results[match_num] = {
                    "team_a": team_a, "team_b": team_b,
                    "winner": team_a if team_b == "TBD" else (team_b if team_a == "TBD" else "TBD"),
                    "prob_a": 0.5, "prob_b": 0.5,
                    "dim_adv": {}, "date": match["date"], "venue": match["venue"],
                }
                continue

            scores_a = all_scores.get(team_a)
            scores_b = all_scores.get(team_b)

            prob_a, prob_b, dim_adv = compute_win_probability(scores_a, scores_b)
            winner = team_a if prob_a >= 0.5 else team_b

            results[match_num] = {
                "team_a": team_a, "team_b": team_b,
                "winner": winner,
                "prob_a": prob_a, "prob_b": prob_b,
                "dim_adv": dim_adv if isinstance(dim_adv, dict) else {},
                "date": match["date"], "venue": match["venue"],
            }

    return results


def generate_bracket_html(results, bracket):
    """Generate bracket.html with the full tournament bracket and predictions."""
    # Serialize results for JS
    js_results = json.dumps(results, indent=2)
    js_bracket = json.dumps(bracket, indent=2)

    nav_html = ' &middot; '.join([
        '<a href="dashboard.html" class="nav-link">Group Stage</a>',
        '<a href="r32.html" class="nav-link">Round of 32</a>',
        '<a href="trends.html" class="nav-link">Trends</a>',
        '<a href="bracket.html" class="nav-link active">Bracket</a>',
    ])

    filepath = os.path.join(PUBLIC_DIR, "bracket.html")
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>World Cup 2026 — Bracket Predictions</title>
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<style>
:root {{
    --wc-green:#3CAC3B;--wc-blue:#2A398D;--wc-red:#E61D25;
    --bg:#FAFAFA;--card-bg:#FFF;--card-border:#E2E4E2;
    --text-primary:#2D2D2D;--text-secondary:#5F6368;--text-muted:#8A8F94;
    --bar-bg:#ECEEED;--hover-shadow:rgba(42,57,141,.08);
    --win-green:#2D8A2C;--lose-gray:#999;
}}
@media(prefers-color-scheme:dark){{:root{{
    --bg:#0F1318;--card-bg:#1A1F27;--card-border:#2D333B;
    --text-primary:#E6EDF3;--text-secondary:#A8B1BA;--text-muted:#6E7681;
    --bar-bg:#2D333B;--hover-shadow:rgba(88,166,255,.1);
    --win-green:#56D364;--lose-gray:#555;
}}}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text-primary);padding:24px;min-height:100vh}}
h1{{text-align:center;font-size:1.8rem;color:var(--wc-blue);margin-bottom:4px}}
.subtitle{{text-align:center;color:var(--text-secondary);font-size:.85rem;margin-bottom:8px}}
.nav{{text-align:center;margin-bottom:20px;font-size:.85rem}}
.nav-link{{color:var(--text-secondary);text-decoration:none;padding:4px 10px;border-radius:4px}}
.nav-link:hover{{background:var(--bar-bg)}}
.nav-link.active{{color:var(--wc-blue);font-weight:600;background:rgba(42,57,141,.08)}}
@media(prefers-color-scheme:dark){{h1{{color:#79B8FF}}.nav-link.active{{color:#79B8FF;background:rgba(88,166,255,.12)}}}}
.bracket-container{{overflow-x:auto;padding:20px 0}}
.round{{display:inline-block;vertical-align:top;margin-right:10px}}
.round-title{{text-align:center;font-size:.75rem;font-weight:600;color:var(--text-muted);margin-bottom:10px;text-transform:uppercase;letter-spacing:.5px}}
.matchup{{background:var(--card-bg);border:1px solid var(--card-border);border-radius:8px;margin-bottom:8px;overflow:hidden;width:220px}}
.matchup-team{{display:flex;align-items:center;padding:6px 10px;font-size:.78rem;gap:6px;border-bottom:1px solid var(--card-border)}}
.matchup-team:last-child{{border-bottom:none}}
.matchup-team.winner{{font-weight:700;color:var(--win-green)}}
.matchup-team.loser{{color:var(--lose-gray)}}
.prob{{margin-left:auto;font-size:.65rem;font-weight:600;opacity:.7}}
.matchup-team.winner .prob{{opacity:1}}
.vs-badge{{text-align:center;font-size:.6rem;color:var(--text-muted);padding:2px;background:var(--bar-bg)}}
.matchup-info{{text-align:center;font-size:.58rem;color:var(--text-muted);padding:3px;background:var(--bar-bg);border-top:1px solid var(--card-border)}}
.analysis{{max-width:1200px;margin:30px auto 0}}
.analysis h2{{font-size:1.2rem;color:var(--wc-blue);margin-bottom:15px;text-align:center}}
@media(prefers-color-scheme:dark){{.analysis h2{{color:#79B8FF}}}}
.match-analysis{{background:var(--card-bg);border:1px solid var(--card-border);border-radius:10px;padding:16px;margin-bottom:12px}}
.ma-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}}
.ma-teams{{font-weight:600;font-size:.9rem}}
.ma-prediction{{font-size:.75rem;padding:3px 8px;border-radius:6px;background:rgba(60,172,59,.1);color:var(--win-green);font-weight:600}}
.ma-bars{{display:flex;gap:4px;margin-top:8px}}
.ma-bar{{flex:1;text-align:center}}
.ma-bar-label{{font-size:.6rem;color:var(--text-muted);margin-bottom:2px}}
.ma-bar-track{{height:6px;background:var(--bar-bg);border-radius:3px;overflow:hidden;display:flex}}
.ma-bar-a{{background:var(--wc-blue);border-radius:3px 0 0 3px}}
.ma-bar-b{{background:var(--wc-red);border-radius:0 3px 3px 0}}
.champion-card{{text-align:center;margin:30px auto;padding:30px;background:var(--card-bg);border:2px solid var(--wc-green);border-radius:16px;max-width:400px}}
.champion-card h2{{color:var(--wc-green);font-size:1.5rem;margin-bottom:5px}}
.champion-card .team{{font-size:2rem;font-weight:700}}
</style>
</head>
<body>
<h1>⚽ World Cup 2026 — Bracket Predictions</h1>
<p class="subtitle">Statistical predictions based on 6-dimension group-stage performance analysis</p>
<div class="nav">{nav_html}</div>

<div class="champion-card" id="champion"></div>

<div class="analysis" id="analysis"></div>

<script>
const results = {js_results};
const bracket = {js_bracket};
const DIMS=["finishing","creation","control","defense","physicality","pressing"];
const DIM_LABELS={{"finishing":"FIN","creation":"CRE","control":"CTR","defense":"DEF","physicality":"PHY","pressing":"PRS"}};

// Show predicted champion
const finalMatch = results[104];
if(finalMatch) {{
    document.getElementById("champion").innerHTML=`<h2>🏆 Predicted Champion</h2><div class="team">${{finalMatch.winner}}</div><p style="color:var(--text-muted);font-size:.8rem;margin-top:8px">Based on group-stage performance analysis</p>`;
}}

// Build analysis cards for R32
function buildAnalysis() {{
    const container = document.getElementById("analysis");
    let html = '<h2>Round of 32 — Match-by-Match Analysis</h2>';

    bracket.r32.forEach(match => {{
        const r = results[match.match];
        if (!r) return;
        const pctA = Math.round(r.prob_a * 100);
        const pctB = Math.round(r.prob_b * 100);
        const dimAdv = r.dim_adv || {{}};

        let barsHtml = '';
        DIMS.forEach(dim => {{
            const adv = dimAdv[dim] || 0;
            const aPct = Math.round(50 + adv * 50);
            const bPct = 100 - aPct;
            barsHtml += `<div class="ma-bar"><div class="ma-bar-label">${{DIM_LABELS[dim]}}</div><div class="ma-bar-track"><div class="ma-bar-a" style="width:${{aPct}}%"></div><div class="ma-bar-b" style="width:${{bPct}}%"></div></div></div>`;
        }});

        html += `<div class="match-analysis">
            <div class="ma-header">
                <span class="ma-teams">${{r.team_a}} vs ${{r.team_b}}</span>
                <span class="ma-prediction">${{r.winner}} (${{Math.max(pctA,pctB)}}%)</span>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:.7rem;color:var(--text-muted)">
                <span>${{r.team_a}} ${{pctA}}%</span>
                <span>${{match.date}} · ${{match.venue}}</span>
                <span>${{pctB}}% ${{r.team_b}}</span>
            </div>
            <div class="ma-bars">${{barsHtml}}</div>
        </div>`;
    }});

    // R16 predictions
    html += '<h2 style="margin-top:30px">Round of 16 — Predicted Matchups</h2>';
    bracket.r16.forEach(match => {{
        const r = results[match.match];
        if (!r || r.team_a === "TBD" || r.team_b === "TBD") return;
        const pctA = Math.round(r.prob_a * 100);
        const pctB = Math.round(r.prob_b * 100);
        html += `<div class="match-analysis">
            <div class="ma-header">
                <span class="ma-teams">${{r.team_a}} vs ${{r.team_b}}</span>
                <span class="ma-prediction">${{r.winner}} (${{Math.max(pctA,pctB)}}%)</span>
            </div>
            <div style="font-size:.7rem;color:var(--text-muted)">${{match.date}} · ${{match.venue}} · ${{pctA}}% - ${{pctB}}%</div>
        </div>`;
    }});

    // QF, SF, Final
    ['qf','sf','final'].forEach(round => {{
        const labels = {{'qf':'Quarterfinals','sf':'Semifinals','final':'Final'}};
        html += `<h2 style="margin-top:30px">${{labels[round]}} — Predicted</h2>`;
        bracket[round].forEach(match => {{
            const r = results[match.match];
            if (!r || r.team_a === "TBD" || r.team_b === "TBD") return;
            const pctA = Math.round(r.prob_a * 100);
            const pctB = Math.round(r.prob_b * 100);
            html += `<div class="match-analysis">
                <div class="ma-header">
                    <span class="ma-teams">${{r.team_a}} vs ${{r.team_b}}</span>
                    <span class="ma-prediction">${{r.winner}} (${{Math.max(pctA,pctB)}}%)</span>
                </div>
                <div style="font-size:.7rem;color:var(--text-muted)">${{match.date}} · ${{match.venue}} · ${{pctA}}% - ${{pctB}}%</div>
            </div>`;
        }});
    }});

    container.innerHTML = html;
}}
buildAnalysis();
</script>
</body></html>'''

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  ✓ Bracket: {filepath}")


def main():
    print("=" * 60)
    print("  World Cup 2026 — Bracket Predictions")
    print("=" * 60)

    # Load bracket structure
    print("\n[1] Loading bracket...")
    bracket_path = os.path.join(DATA_DIR, "bracket.json")
    with open(bracket_path, "r", encoding="utf-8") as f:
        bracket = json.load(f)
    print(f"    R32: {len(bracket['r32'])} matches")

    # Compute raw scores for all teams in the bracket
    print("\n[2] Computing team scores...")
    all_teams = set()
    for match in bracket["r32"]:
        all_teams.add(match["team_a"])
        all_teams.add(match["team_b"])
    all_teams.discard("TBD")

    all_scores = {}
    for team in sorted(all_teams):
        scores = compute_team_raw_scores(team)
        if scores:
            all_scores[team] = scores
            print(f"    {team:30s} — {scores['matches']} matches")

    # Simulate bracket
    print(f"\n[3] Simulating bracket ({len(all_scores)} teams)...")
    results = simulate_bracket(bracket, all_scores)

    # Print R32 predictions
    print("\n    Round of 32 Predictions:")
    for match in bracket["r32"]:
        r = results[match["match"]]
        if r["team_b"] == "TBD":
            print(f"    M{match['match']}: {r['team_a']:20s} vs {'TBD':20s} → {r['winner']}")
        else:
            prob = max(r["prob_a"], r["prob_b"])
            print(f"    M{match['match']}: {r['team_a']:20s} vs {r['team_b']:20s} → {r['winner']} ({prob:.0%})")

    # Print predicted champion
    final = results.get(104)
    if final:
        print(f"\n    🏆 Predicted Champion: {final['winner']}")

    # Generate HTML
    print("\n[4] Generating bracket page...")
    # Convert results keys to strings for JSON
    str_results = {str(k): v for k, v in results.items()}
    generate_bracket_html(str_results, bracket)

    print("\n" + "=" * 60)
    print("  Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
