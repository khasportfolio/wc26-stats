"""
World Cup 2026 — Prediction Logs Page

Generates a simple page showing every prediction with full reasoning:
- Per-dimension breakdown for each matchup
- Which team dominates which dimensions
- The weights applied
- Whether the prediction was correct (for completed matches)
"""

import os
import sys
import json

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
REPO_DIR = os.environ.get("REPO_DIR", SCRIPT_DIR)
DATA_DIR = os.path.join(REPO_DIR, "data")
PUBLIC_DIR = os.path.join(REPO_DIR, "public")

from build_bracket import (
    compute_team_raw_scores, compute_win_probability, DIM_WEIGHTS, FLAGS
)
from build_r32_dashboard import DIMS


def build_match_analysis(team_a, team_b, prob_a, predicted_winner, actual_result=None, reasoning="", is_tossup=False):
    """Build a detailed analysis block for one matchup."""
    scores_a = compute_team_raw_scores(team_a)
    scores_b = compute_team_raw_scores(team_b)
    if not scores_a or not scores_b:
        return ""

    dim_labels = {
        "finishing": "Finishing", "defense": "Defense", "control": "Control",
        "creation": "Creation", "pressing": "Pressing", "physicality": "Physicality",
    }
    dim_order = ["finishing", "defense", "control", "creation", "pressing", "physicality"]

    rows = []
    a_wins = 0
    b_wins = 0
    for dim in dim_order:
        weight = int(DIM_WEIGHTS[dim] * 100)
        val_a = scores_a[dim]
        val_b = scores_b[dim]
        avg_mag = (abs(val_a) + abs(val_b)) / 2
        diff = abs(val_a - val_b)
        if avg_mag > 0 and diff / avg_mag < 0.05:
            edge = "Even"
            edge_cls = "even"
        elif val_a > val_b:
            edge = team_a
            edge_cls = "team-a"
            a_wins += 1
        else:
            edge = team_b
            edge_cls = "team-b"
            b_wins += 1
        rows.append(f'<tr><td>{dim_labels[dim]}</td><td>{weight}%</td>'
                    f'<td>{val_a:.1f}</td><td>{val_b:.1f}</td>'
                    f'<td class="{edge_cls}">{edge}</td></tr>')

    pct_a = round(prob_a * 100) if prob_a <= 1 else prob_a
    pct_b = 100 - pct_a

    # Prediction label
    if is_tossup:
        pred_label = f'<span class="prediction tossup-badge">TOSS-UP ({pct_a}%-{pct_b}%)</span>'
    else:
        pred_label = f'<span class="prediction">{predicted_winner} ({max(pct_a,pct_b)}%)</span>'

    # Result status
    result_html = ""
    if actual_result:
        winner = actual_result["winner"]
        score = actual_result.get("score", "")
        if is_tossup:
            # Check if it was actually close
            parts = score.split("-")
            try:
                goal_diff = abs(int(parts[0]) - int(parts[1].split(" ")[0]))
            except (ValueError, IndexError):
                goal_diff = 0
            is_close = goal_diff <= 1 or "pen" in score or "AET" in score
            if is_close:
                status_cls = "correct"
                status_text = "✓ Correct — predicted toss-up, game was decided by 1 goal/penalties"
            else:
                status_cls = "incorrect"
                status_text = f"✗ Called toss-up but {winner} won convincingly"
            result_html = f'<div class="result-badge {status_cls}">{status_text} — FT: {score}</div>'
        else:
            correct = winner == predicted_winner
            status_cls = "correct" if correct else "incorrect"
            status_text = "✓ Correct" if correct else "✗ Wrong"
            result_html = f'<div class="result-badge {status_cls}">{status_text} — FT: {score}, {winner} advances</div>'

    # Reasoning block
    reasoning_html = f'<div class="reasoning">{reasoning}</div>' if reasoning else ''

    return f'''<div class="analysis-card">
<div class="analysis-header">
<span class="teams">{FLAGS.get(team_a,"")} {team_a} vs {FLAGS.get(team_b,"")} {team_b}</span>
{pred_label}
</div>
{result_html}
{reasoning_html}
<table class="dim-table">
<thead><tr><th>Dimension</th><th>Weight</th><th>{team_a}</th><th>{team_b}</th><th>Edge</th></tr></thead>
<tbody>{"".join(rows)}</tbody>
</table>
<div class="summary">
{team_a} leads {a_wins}/6 dimensions · {team_b} leads {b_wins}/6 dimensions · {6 - a_wins - b_wins} even
</div>
</div>'''


def main():
    print("=" * 60)
    print("  World Cup 2026 — Building Prediction Logs")
    print("=" * 60)

    # Load frozen R32 predictions
    with open(os.path.join(DATA_DIR, "r32_predictions_frozen.json"), "r") as f:
        r32_frozen = json.load(f)

    # Load R32 results
    with open(os.path.join(DATA_DIR, "r32_results.json"), "r") as f:
        r32_results = json.load(f)
    completed = {r["match"]: r for r in r32_results.get("completed", [])}

    # Load R16 predictions if they exist
    r16_frozen = {}
    r16_path = os.path.join(DATA_DIR, "r16_predictions_frozen.json")
    if os.path.exists(r16_path):
        with open(r16_path, "r") as f:
            r16_frozen = json.load(f)

    # Load bracket
    with open(os.path.join(DATA_DIR, "bracket.json"), "r") as f:
        bracket = json.load(f)

    # Build analysis for each R32 match
    print("\n  Generating R32 analyses...")
    r32_analyses = []
    for match in bracket["r32"]:
        mn = match["match"]
        fp = r32_frozen.get(str(mn))
        if not fp:
            continue
        team_a = fp["team_a"]
        team_b = fp["team_b"]
        prob_a = fp["prob_a"] / 100.0
        predicted_winner = fp.get("predicted_winner", team_a if prob_a >= 0.5 else team_b)

        actual = None
        if mn in completed:
            c = completed[mn]
            score_str = f"{c['score_a']}-{c['score_b']}"
            if c.get("penalties"):
                score_str += f" (pen {c['pen_a']}-{c['pen_b']})"
            actual = {"winner": c["winner"], "score": score_str}

        html = build_match_analysis(team_a, team_b, fp["prob_a"], predicted_winner, actual,
                                    reasoning=fp.get("reasoning", ""),
                                    is_tossup=fp.get("is_tossup", False))
        r32_analyses.append(html)
        print(f"    M{mn}: {team_a} vs {team_b}")

    # Build analysis for R16 matches
    print("\n  Generating R16 analyses...")
    r16_analyses = []
    for mn_str, fp in r16_frozen.items():
        team_a = fp["team_a"]
        team_b = fp["team_b"]
        predicted_winner = fp.get("predicted_winner")
        html = build_match_analysis(team_a, team_b, fp["prob_a"], predicted_winner,
                                    reasoning=fp.get("reasoning", ""),
                                    is_tossup=fp.get("is_tossup", False))
        r16_analyses.append(html)
        print(f"    M{mn_str}: {team_a} vs {team_b}")

    # Generate HTML
    nav_html = ' &middot; '.join([
        '<a href="dashboard.html" class="nav-link">Group Stage</a>',
        '<a href="r32.html" class="nav-link">Round of 32</a>',
        '<a href="r16.html" class="nav-link">Round of 16</a>',
        '<a href="trends.html" class="nav-link">Trends</a>',
        '<a href="bracket.html" class="nav-link">Bracket</a>',
        '<a href="predictions.html" class="nav-link active">Predictions</a>',
    ])

    # Count correct/incorrect
    # Toss-ups count as CORRECT if the match was close (1-goal margin or pens/ET)
    correct = 0
    total = len(completed)
    for mn, c in completed.items():
        fp = r32_frozen.get(str(mn), {})
        if fp.get("is_tossup"):
            # Toss-up is correct if match was close (1-goal diff, ET, or pens)
            goal_diff = abs(c["score_a"] - c["score_b"])
            if goal_diff <= 1 or c.get("extra_time") or c.get("penalties"):
                correct += 1  # We correctly predicted it would be close
        else:
            if c["winner"] == fp.get("predicted_winner"):
                correct += 1
    tossup_count = sum(1 for mn in completed if r32_frozen.get(str(mn), {}).get("is_tossup"))
    accuracy = f"{correct}/{total}" if total else "—"

    filepath = os.path.join(PUBLIC_DIR, "predictions.html")
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>World Cup 2026 — Prediction Logs</title>
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<style>
:root {{--bg:#FAFAFA;--card-bg:#FFF;--card-border:#E2E4E2;--text-primary:#1A1A1A;--text-secondary:#3D3D3D;--text-muted:#666;--wc-blue:#2A398D;--wc-green:#3CAC3B;--wc-red:#E61D25;--bar-bg:#ECEEED}}
@media(prefers-color-scheme:dark){{:root{{--bg:#0F1318;--card-bg:#1A1F27;--card-border:#2D333B;--text-primary:#FFF;--text-secondary:#D4D4D4;--text-muted:#A0A0A0;--wc-blue:#79B8FF;--bar-bg:#2D333B}}}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text-primary);padding:24px;min-height:100vh}}
h1{{text-align:center;font-size:1.7rem;color:var(--wc-blue);margin-bottom:4px}}
h2{{font-size:1.2rem;color:var(--wc-blue);margin:30px 0 15px;padding-bottom:8px;border-bottom:2px solid var(--card-border)}}
.subtitle{{text-align:center;color:var(--text-secondary);font-size:.82rem;margin-bottom:8px}}
.nav{{text-align:center;margin-bottom:24px;font-size:.85rem}}
.nav-link{{color:var(--text-secondary);text-decoration:none;padding:4px 10px;border-radius:4px}}
.nav-link:hover{{background:var(--bar-bg)}}
.nav-link.active{{color:var(--wc-blue);font-weight:600;background:rgba(42,57,141,.08)}}
.accuracy{{text-align:center;font-size:.9rem;margin-bottom:20px;padding:10px;background:var(--card-bg);border:1px solid var(--card-border);border-radius:8px;max-width:400px;margin-left:auto;margin-right:auto}}
.content{{max-width:900px;margin:0 auto}}
.analysis-card{{background:var(--card-bg);border:1px solid var(--card-border);border-radius:10px;padding:16px;margin-bottom:12px}}
.analysis-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:8px}}
.teams{{font-weight:700;font-size:.9rem}}
.prediction{{font-size:.75rem;padding:3px 8px;border-radius:6px;background:rgba(232,155,45,.15);color:#E89B2D;font-weight:600}}
.prediction.tossup-badge{{background:rgba(150,150,150,.15);color:var(--text-muted)}}
.result-badge{{font-size:.72rem;padding:4px 10px;border-radius:6px;margin-bottom:8px;font-weight:600}}
.result-badge.correct{{background:rgba(60,172,59,.1);color:var(--wc-green)}}
.result-badge.incorrect{{background:rgba(230,29,37,.1);color:var(--wc-red)}}
.result-badge.neutral{{background:rgba(150,150,150,.1);color:var(--text-muted)}}
.reasoning{{font-size:.72rem;color:var(--text-secondary);padding:8px 12px;background:var(--bar-bg);border-radius:6px;margin:8px 0;line-height:1.5;font-style:italic}}
.dim-table{{width:100%;border-collapse:collapse;font-size:.72rem;margin-top:8px}}
.dim-table th{{text-align:left;padding:4px 8px;border-bottom:1px solid var(--card-border);color:var(--text-muted);font-weight:600}}
.dim-table td{{padding:4px 8px;border-bottom:1px solid var(--card-border)}}
.dim-table .team-a{{color:var(--wc-blue);font-weight:600}}
.dim-table .team-b{{color:#E89B2D;font-weight:600}}
.dim-table .even{{color:var(--text-muted)}}
.summary{{font-size:.7rem;color:var(--text-muted);margin-top:8px;text-align:center}}
</style>
</head>
<body>
<h1>⚽ World Cup 2026 — Prediction Logs</h1>
<p class="subtitle">Full reasoning behind every prediction · Per-dimension breakdown</p>
<div class="nav">{nav_html}</div>
<div class="accuracy">R32 Accuracy: <strong>{accuracy}</strong> ({tossup_count} toss-ups verified as close games)</div>
<div class="content">
<h2>Round of 32 Predictions</h2>
{"".join(r32_analyses)}
'''

    if r16_analyses:
        html += f'''<h2>Round of 16 Predictions</h2>
{"".join(r16_analyses)}
'''

    html += '''</div>
</body></html>'''

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\n  ✓ Predictions page: {filepath}")
    print(f"  R32 accuracy: {accuracy}")
    print("\n" + "=" * 60)
    print("  Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
