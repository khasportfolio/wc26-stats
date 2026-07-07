"""
World Cup 2026 — Bracket Prediction & Visualization

Reads the bracket structure and team dimension scores, then:
1. Computes win probability for each R32 matchup based on stat comparison
2. Generates bracket.html with a traditional sports bracket layout
   - Only R32 predictions are shown
   - R16 through Final shown as empty slots (venue/date only)

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
DIM_WEIGHTS = {
    "finishing": 0.25, "defense": 0.25, "control": 0.20,
    "creation": 0.15, "pressing": 0.10, "physicality": 0.05
}

import sys
sys.path.insert(0, SCRIPT_DIR)
from build_r32_dashboard import (
    read_team_matches, compute_match_score, safe_mean, weighted_mean, parse_float, DIMS
)

# Country codes for display (consistent, no emoji rendering issues)
FLAGS = {
    "South Africa": "RSA", "Canada": "CAN", "Germany": "GER", "Paraguay": "PAR",
    "Netherlands": "NED", "Morocco": "MAR", "Brazil": "BRA", "Japan": "JPN",
    "France": "FRA", "Sweden": "SWE", "Ivory Coast": "CIV", "Norway": "NOR",
    "Mexico": "MEX", "Ecuador": "ECU", "England": "ENG", "DR Congo": "COD",
    "USA": "USA", "Bosnia and Herzegovina": "BIH", "Belgium": "BEL", "Senegal": "SEN",
    "Portugal": "POR", "Croatia": "CRO", "Spain": "ESP", "TBD": "TBD",
    "Switzerland": "SUI", "Argentina": "ARG", "Cape Verde": "CPV",
    "Colombia": "COL", "Ghana": "GHA", "Australia": "AUS", "Egypt": "EGY",
    "Austria": "AUT", "Algeria": "ALG",
}


def compute_team_raw_scores(team_name):
    """Compute recency-weighted raw dimension scores for a team."""
    matches = read_team_matches(team_name)
    if not matches:
        return None
    scores = {}
    for dim in DIMS:
        per_match = [compute_match_score(m, dim) for m in matches]
        scores[dim] = weighted_mean(per_match)
    scores["matches"] = len(matches)
    # Stats for goals prediction (also recency-weighted)
    scores["goals_avg"] = weighted_mean([parse_float(m.get("Goals")) for m in matches])
    scores["xg_avg"] = weighted_mean([parse_float(m.get("xG")) for m in matches])
    scores["xgc_avg"] = weighted_mean([parse_float(m.get("xG conceded")) for m in matches])
    scores["goals_conceded_avg"] = weighted_mean([parse_float(m.get("Goals conceded")) for m in matches])
    scores["sot_avg"] = weighted_mean([parse_float(m.get("Shots on target")) for m in matches])
    return scores


def compute_win_probability(team_a_scores, team_b_scores):
    """
    Compute probability of team_a winning using logistic model.
    Returns (prob_a, prob_b).
    """
    if team_a_scores is None or team_b_scores is None:
        return 0.5, 0.5

    total_advantage = 0
    for dim in DIMS:
        diff = team_a_scores[dim] - team_b_scores[dim]
        avg_mag = (abs(team_a_scores[dim]) + abs(team_b_scores[dim])) / 2
        if avg_mag > 0:
            norm_diff = diff / avg_mag
        else:
            norm_diff = 0
        total_advantage += norm_diff * DIM_WEIGHTS[dim]

    k = 3.0
    prob_a = 1 / (1 + math.exp(-k * total_advantage))
    prob_b = 1 - prob_a

    return round(prob_a, 3), round(prob_b, 1)


def compute_prediction(team_a, team_b, scores_a, scores_b):
    """
    Dual-signal prediction model.

    Signal 1: Weighted probability (logistic model on raw scores)
    Signal 2: Dimension dominance (who leads more dimensions)

    Decision logic:
    - If both signals agree → confident pick
    - If signals disagree → toss-up (regardless of raw probability)
    - If probability within 55/45 and dimensions close → toss-up

    Returns dict with prediction details and reasoning.
    """
    if scores_a is None or scores_b is None:
        return {
            "predicted_winner": None, "is_tossup": True,
            "prob_a": 50, "prob_b": 50,
            "reasoning": "Insufficient data",
            "dim_edges": {}, "a_dims": 0, "b_dims": 0,
        }

    # Signal 1: Weighted probability
    prob_a_raw, _ = compute_win_probability(scores_a, scores_b)
    prob_a_pct = round(prob_a_raw * 100)
    prob_b_pct = 100 - prob_a_pct
    prob_winner = team_a if prob_a_raw >= 0.5 else team_b

    # Signal 2: Dimension dominance
    DIM_LABELS = {
        "finishing": "Finishing", "defense": "Defense", "control": "Control",
        "creation": "Creation", "pressing": "Pressing", "physicality": "Physicality",
    }
    dim_edges = {}
    a_dims = 0
    b_dims = 0
    even_dims = 0
    for dim in DIMS:
        val_a = scores_a[dim]
        val_b = scores_b[dim]
        avg_mag = (abs(val_a) + abs(val_b)) / 2
        diff = abs(val_a - val_b)
        if avg_mag > 0 and diff / avg_mag < 0.05:
            dim_edges[dim] = "even"
            even_dims += 1
        elif val_a > val_b:
            dim_edges[dim] = team_a
            a_dims += 1
        else:
            dim_edges[dim] = team_b
            b_dims += 1

    dim_winner = team_a if a_dims > b_dims else (team_b if b_dims > a_dims else None)

    # Decision logic
    prob_margin = abs(prob_a_pct - 50)

    if prob_margin <= 2:
        # Dead even probability → always toss-up
        is_tossup = True
        predicted_winner = None
        reasoning = (f"Pure coin flip. Probability is {prob_a_pct}%-{prob_b_pct}% "
                     f"(within 2% margin). {team_a} leads {a_dims} dimensions, "
                     f"{team_b} leads {b_dims}. No meaningful edge for either side.")
    elif prob_winner != dim_winner and dim_winner is not None:
        # Signals disagree → toss-up only if probability isn't overwhelming
        if prob_margin <= 15:
            is_tossup = True
            predicted_winner = None
            reasoning = (f"Signals conflict. Probability favors {prob_winner} ({max(prob_a_pct,prob_b_pct)}%) "
                         f"but {dim_winner} dominates more dimensions ({max(a_dims,b_dims)}/6). "
                         f"{prob_winner}'s edge comes from a single large gap that inflates the "
                         f"weighted score, but {dim_winner} controls more aspects of the game. "
                         f"Too close to call.")
        else:
            # Probability is strong enough (>65%) to override dimension count
            is_tossup = False
            predicted_winner = prob_winner
            dim_list_winner = [DIM_LABELS[d] for d, v in dim_edges.items() if v == predicted_winner]
            other_team = team_b if predicted_winner == team_a else team_a
            reasoning = (f"{predicted_winner} is favored at {max(prob_a_pct,prob_b_pct)}% "
                         f"despite {dim_winner} leading more dimensions ({max(a_dims,b_dims)}/6). "
                         f"{predicted_winner}'s advantage in {', '.join(dim_list_winner)} "
                         f"is large enough to overcome the spread. Moderate confidence.")
    elif prob_margin <= 5 and abs(a_dims - b_dims) <= 1:
        # Marginal probability + close dimension count → toss-up
        is_tossup = True
        predicted_winner = None
        reasoning = (f"Marginal edge. Probability is only {max(prob_a_pct,prob_b_pct)}% "
                     f"and dimension count is close ({a_dims}-{b_dims}). "
                     f"Not enough separation to make a confident call.")
    else:
        # Both signals agree or one is dominant → confident pick
        is_tossup = False
        predicted_winner = prob_winner
        dim_list_winner = [DIM_LABELS[d] for d, v in dim_edges.items() if v == predicted_winner]
        dim_list_loser = [DIM_LABELS[d] for d, v in dim_edges.items() if v != predicted_winner and v != "even"]
        other_team = team_b if predicted_winner == team_a else team_a

        reasoning = (f"{predicted_winner} is favored at {max(prob_a_pct,prob_b_pct)}% "
                     f"and leads {max(a_dims,b_dims)}/6 dimensions "
                     f"({', '.join(dim_list_winner)}). "
                     f"{other_team} has edges in {', '.join(dim_list_loser) if dim_list_loser else 'none'}. "
                     f"Both signals align — clear advantage for {predicted_winner}.")

    return {
        "predicted_winner": predicted_winner,
        "is_tossup": is_tossup,
        "prob_a": prob_a_pct,
        "prob_b": prob_b_pct,
        "reasoning": reasoning,
        "dim_edges": dim_edges,
        "a_dims": a_dims,
        "b_dims": b_dims,
    }


def predict_match_goals(scores_a, scores_b):
    """
    Predict total goals in a match using xG-based model.

    Logic:
    - Team A's expected goals = average of (A's xG, A's goals_avg, B's xGC)
    - Team B's expected goals = average of (B's xG, B's goals_avg, A's xGC)
    - Apply a knockout discount (0.85) since knockout games are tighter
    - Total = team_a_expected + team_b_expected

    Returns dict with predicted totals and over/under probabilities.
    """
    if scores_a is None or scores_b is None:
        return {"total": 2.5, "over_1_5": 0.5, "over_2_5": 0.5, "over_3_5": 0.5}

    KNOCKOUT_FACTOR = 0.85  # Games are tighter in knockouts

    # Team A expected goals: blend of their attacking output vs B's defensive record
    a_exp = (scores_a["xg_avg"] + scores_a["goals_avg"] + scores_b["xgc_avg"]) / 3
    # Team B expected goals: blend of their attacking output vs A's defensive record
    b_exp = (scores_b["xg_avg"] + scores_b["goals_avg"] + scores_a["xgc_avg"]) / 3

    # Apply knockout discount
    a_exp *= KNOCKOUT_FACTOR
    b_exp *= KNOCKOUT_FACTOR

    total_exp = a_exp + b_exp

    # Use Poisson-approximation for over/under probabilities
    # P(total <= k) approximated using the CDF
    import math
    def poisson_cdf(lam, k):
        """P(X <= k) for Poisson distribution with mean lam."""
        total = 0
        for i in range(k + 1):
            total += (lam ** i) * math.exp(-lam) / math.factorial(i)
        return total

    over_1_5 = 1 - poisson_cdf(total_exp, 1)
    over_2_5 = 1 - poisson_cdf(total_exp, 2)
    over_3_5 = 1 - poisson_cdf(total_exp, 3)

    return {
        "total": round(total_exp, 2),
        "a_exp": round(a_exp, 2),
        "b_exp": round(b_exp, 2),
        "over_1_5": round(over_1_5, 2),
        "over_2_5": round(over_2_5, 2),
        "over_3_5": round(over_3_5, 2),
    }


def predict_r32(bracket, all_scores, actual_results=None, frozen_predictions=None):
    """
    Build R32 results using:
    - Frozen predictions (from r32_predictions_frozen.json) for the odds
    - Actual results for completed matches
    This ensures predictions don't change as new match data comes in.
    """
    results = {}
    # Index actual results by match number
    completed = {}
    if actual_results:
        for r in actual_results.get("completed", []):
            completed[r["match"]] = r

    # Index frozen predictions by match number
    frozen = {}
    if frozen_predictions:
        frozen = {int(k): v for k, v in frozen_predictions.items()}

    for match in bracket["r32"]:
        match_num = match["match"]
        team_a = match["team_a"]
        team_b = match["team_b"]

        # If match has actual result, use it
        if match_num in completed:
            actual = completed[match_num]
            score_str = f"{actual['score_a']}-{actual['score_b']}"
            if actual.get("penalties"):
                score_str += f" (pen {actual['pen_a']}-{actual['pen_b']})"
            elif actual.get("extra_time"):
                score_str += " (AET)"
            results[match_num] = {
                "team_a": team_a, "team_b": team_b,
                "winner": actual["winner"],
                "score": score_str,
                "completed": True,
                "prob_a": None, "prob_b": None,
                "date": match["date"], "venue": match["venue"],
            }
            continue

        # Use frozen predictions if available (don't recompute)
        if match_num in frozen:
            fp = frozen[match_num]
            prob_a = fp["prob_a"] / 100.0
            winner = fp.get("predicted_winner", team_a if prob_a >= 0.5 else team_b)
            results[match_num] = {
                "team_a": team_a, "team_b": team_b,
                "winner": winner,
                "prob_a": prob_a, "prob_b": round(1 - prob_a, 3),
                "completed": False,
                "date": match["date"], "venue": match["venue"],
            }
            continue

        # Fallback: compute live (shouldn't happen if frozen file exists)
        if team_a == "TBD" or team_b == "TBD":
            results[match_num] = {
                "team_a": team_a, "team_b": team_b,
                "winner": team_a if team_b == "TBD" else "TBD",
                "prob_a": 0.5, "prob_b": 0.5,
                "completed": False,
                "date": match["date"], "venue": match["venue"],
            }
            continue

        scores_a = all_scores.get(team_a)
        scores_b = all_scores.get(team_b)
        prob_a, prob_b = compute_win_probability(scores_a, scores_b)
        winner = team_a if prob_a >= 0.5 else team_b

        results[match_num] = {
            "team_a": team_a, "team_b": team_b,
            "winner": winner,
            "prob_a": prob_a, "prob_b": round(1 - prob_a, 3),
            "completed": False,
            "date": match["date"], "venue": match["venue"],
        }

    return results


def build_tooltip_html(team_a, team_b, all_scores):
    """Build a tooltip div showing per-dimension breakdown for a matchup."""
    scores_a = all_scores.get(team_a)
    scores_b = all_scores.get(team_b)
    if not scores_a or not scores_b:
        return ""

    DIM_LABELS = {
        "finishing": "Finishing", "defense": "Defense", "control": "Control",
        "creation": "Creation", "pressing": "Pressing", "physicality": "Physicality",
    }
    DIM_ORDER = ["finishing", "defense", "control", "creation", "pressing", "physicality"]

    short_a = team_a.replace("Bosnia and Herzegovina", "Bosnia")
    short_b = team_b.replace("Bosnia and Herzegovina", "Bosnia")

    lines = []
    a_wins = 0
    b_wins = 0
    for dim in DIM_ORDER:
        weight_pct = int(DIM_WEIGHTS[dim] * 100)
        val_a = scores_a[dim]
        val_b = scores_b[dim]
        diff = abs(val_a - val_b)
        avg_mag = (abs(val_a) + abs(val_b)) / 2
        # Consider it "even" if relative difference < 5%
        if avg_mag > 0 and diff / avg_mag < 0.05:
            edge = "Even"
        elif val_a > val_b:
            edge = short_a
            a_wins += 1
        else:
            edge = short_b
            b_wins += 1
        lines.append(
            f'{DIM_LABELS[dim]} ({weight_pct}%): {short_a} {val_a:.1f} vs {short_b} {val_b:.1f} → {edge}'
        )

    # Summary line
    if a_wins > b_wins:
        summary = f"Key: {short_a} dominates {a_wins}/6 dimensions"
    elif b_wins > a_wins:
        summary = f"Key: {short_b} dominates {b_wins}/6 dimensions"
    else:
        summary = "Key: Teams evenly matched across dimensions"

    tooltip_content = "<br>".join(lines) + f"<br><br>{summary}"
    return f'<div class="tooltip">{tooltip_content}</div>'


def generate_bracket_html(results, bracket, all_scores):
    """Generate bracket.html with traditional sports bracket layout."""

    nav_html = ' &middot; '.join([
        '<a href="dashboard.html" class="nav-link">Group Stage</a>',
        '<a href="r32.html" class="nav-link">Round of 32</a>',
        '<a href="r16.html" class="nav-link">Round of 16</a>',
        '<a href="trends.html" class="nav-link">Trends</a>',
        '<a href="bracket.html" class="nav-link active">Bracket</a>',
        '<a href="predictions.html" class="nav-link">Predictions</a>',
    ])

    # Split R32 into left and right halves
    # Left side: matches that feed into left-side R16 (89, 90, 93, 94)
    # R16-89: W74 vs W77 → left side includes M74 (Germany/Paraguay) and M77 (France/Sweden)
    # R16-90: W73 vs W75 → left side includes M73 (S.Africa/Canada) and M75 (Netherlands/Morocco)
    # R16-93: W83 vs W84 → left side includes M83 (Portugal/Croatia) and M84 (Spain/TBD)
    # R16-94: W81 vs W82 → left side includes M81 (USA/Bosnia) and M82 (Belgium/Senegal)
    left_r32_nums = [74, 77, 73, 75, 83, 84, 81, 82]
    # Right side: matches that feed into right-side R16 (91, 92, 95, 96)
    # R16-91: W76 vs W78 → M76 (Brazil/Japan) and M78 (Ivory Coast/Norway)
    # R16-92: W79 vs W80 → M79 (Mexico/Ecuador) and M80 (England/DR Congo)
    # R16-95: W86 vs W88 → M86 (Argentina/Cape Verde) and M88 (Australia/Egypt)
    # R16-96: W85 vs W87 → M85 (Switzerland/TBD) and M87 (Colombia/Ghana)
    right_r32_nums = [76, 78, 79, 80, 86, 88, 85, 87]

    # R16 left and right
    left_r16 = [89, 90, 93, 94]
    right_r16 = [91, 92, 95, 96]

    # QF
    left_qf = [97, 98]
    right_qf = [99, 100]

    # SF
    left_sf = [101]
    right_sf = [102]

    # Build matchup HTML for R32
    def r32_matchup_html(match_num):
        r = results.get(match_num)
        if not r:
            return '<div class="matchup empty"><div class="matchup-info">TBD</div></div>'

        team_a = r["team_a"]
        team_b = r["team_b"]
        winner = r["winner"]
        flag_a = FLAGS.get(team_a, "???")
        flag_b = FLAGS.get(team_b, "???")

        cls_a = "predicted-winner" if winner == team_a else "loser"
        cls_b = "predicted-winner" if winner == team_b else "loser"

        short_a = team_a.replace("Bosnia and Herzegovina", "Bosnia")
        short_b = team_b.replace("Bosnia and Herzegovina", "Bosnia")

        # Completed match — orange for predicted winner, green for actual winner
        if r.get("completed"):
            score = r.get("score", "")
            actual_winner = r["winner"]
            # Use frozen predictions for the original odds
            frozen = {}
            frozen_path_local = os.path.join(DATA_DIR, "r32_predictions_frozen.json")
            if os.path.exists(frozen_path_local):
                with open(frozen_path_local, "r", encoding="utf-8") as ff:
                    frozen = json.load(ff)
            fp = frozen.get(str(match_num), {})
            orig_pct_a = fp.get("prob_a", 50)
            orig_pct_b = fp.get("prob_b", 50)
            pred_winner = fp.get("predicted_winner", team_a)

            # Color logic: orange = predicted winner, green = actual winner
            # If prediction was a toss-up (<= 52%), don't show orange
            is_tossup = abs(orig_pct_a - 50) <= 2

            def get_cls(team):
                if team == actual_winner:
                    return "actual-winner"  # green
                elif team == pred_winner and not is_tossup:
                    return "predicted-winner"  # orange (clear prediction was wrong)
                else:
                    return "loser"

            cls_a = get_cls(team_a)
            cls_b = get_cls(team_b)
            adv_a = " ✓" if actual_winner == team_a else ""
            adv_b = " ✓" if actual_winner == team_b else ""

            return f'''<div class="matchup completed">
<div class="matchup-info">{r["venue"]} · {r["date"]}</div>
<div class="matchup-team {cls_a}"><span class="flag">{flag_a}</span><span class="team-name">{short_a}{adv_a}</span><span class="prob">{orig_pct_a}%</span></div>
<div class="matchup-team {cls_b}"><span class="flag">{flag_b}</span><span class="team-name">{short_b}{adv_b}</span><span class="prob">{orig_pct_b}%</span></div>
<div class="score-line">FT: {score}</div>
</div>'''

        # Prediction for upcoming match
        prob_a = r["prob_a"]
        prob_b = r["prob_b"]
        pct_a = round(prob_a * 100)
        pct_b = 100 - pct_a

        # If within 52/48 range, treat as toss-up — no highlight
        if abs(pct_a - 50) <= 2:
            cls_a = "tossup"
            cls_b = "tossup"

        if team_b == "TBD":
            return f'''<div class="matchup">
<div class="matchup-info">{r["venue"]} · {r["date"]}</div>
<div class="matchup-team winner"><span class="flag">{flag_a}</span><span class="team-name">{short_a}</span><span class="prob">BYE</span></div>
<div class="matchup-team loser"><span class="flag">{flag_b}</span><span class="team-name">{short_b}</span><span class="prob">—</span></div>
</div>'''

        return f'''<div class="matchup">
<div class="matchup-info">{r["venue"]} · {r["date"]}</div>
<div class="matchup-team {cls_a}"><span class="flag">{flag_a}</span><span class="team-name">{short_a}</span><span class="prob">{pct_a}%</span></div>
<div class="matchup-team {cls_b}"><span class="flag">{flag_b}</span><span class="team-name">{short_b}</span><span class="prob">{pct_b}%</span></div>
</div>'''

    # Build empty slot HTML for later rounds
    def empty_slot_html(match_info):
        """Show future round slot with predictions when both teams are known."""
        match_num = match_info.get("match", 0)
        team_a_ref = match_info.get("team_a", "")
        team_b_ref = match_info.get("team_b", "")

        # Load actual R16 results
        r16_results_path = os.path.join(DATA_DIR, "r16_results.json")
        r16_actual = {}
        if os.path.exists(r16_results_path):
            with open(r16_results_path, "r", encoding="utf-8") as ff:
                r16_data = json.load(ff)
            for r in r16_data.get("completed", []):
                r16_actual[r["match"]] = r

        # Resolve W## references ONLY if that match is actually completed
        def resolve(ref):
            if ref.startswith("W"):
                mn = int(ref[1:])
                # Check R32 results first
                r = results.get(mn)
                if r and r.get("completed") and r.get("winner") and r["winner"] != "TBD":
                    return r["winner"]
                # Check R16 results
                if mn in r16_actual:
                    return r16_actual[mn]["winner"]
            return None

        team_a = resolve(team_a_ref)
        team_b = resolve(team_b_ref)

        if match_num in r16_actual:
            actual = r16_actual[match_num]
            act_team_a = actual["team_a"]
            act_team_b = actual["team_b"]
            actual_winner = actual["winner"]
            score_str = f"{actual['score_a']}-{actual['score_b']}"
            if actual.get("penalties"):
                score_str += f" (pen {actual['pen_a']}-{actual['pen_b']})"
            elif actual.get("extra_time"):
                score_str += " (AET)"

            flag_a = FLAGS.get(act_team_a, "???")
            flag_b = FLAGS.get(act_team_b, "???")
            short_a = act_team_a.replace("Bosnia and Herzegovina", "Bosnia")
            short_b = act_team_b.replace("Bosnia and Herzegovina", "Bosnia")

            # Use frozen predictions for original odds
            r16_frozen_path = os.path.join(DATA_DIR, "r16_predictions_frozen.json")
            frozen = {}
            if os.path.exists(r16_frozen_path):
                with open(r16_frozen_path, "r", encoding="utf-8") as ff:
                    frozen = json.load(ff)
            fp = frozen.get(str(match_num), {})
            orig_pct_a = fp.get("prob_a", 50)
            orig_pct_b = fp.get("prob_b", 50)
            pred_winner = fp.get("predicted_winner", act_team_a)
            is_tossup = abs(orig_pct_a - 50) <= 2

            def get_cls(team):
                if team == actual_winner:
                    return "actual-winner"
                elif team == pred_winner and not is_tossup:
                    return "predicted-winner"
                else:
                    return "loser"

            cls_a = get_cls(act_team_a)
            cls_b = get_cls(act_team_b)
            adv_a = " ✓" if actual_winner == act_team_a else ""
            adv_b = " ✓" if actual_winner == act_team_b else ""

            return f'''<div class="matchup completed">
<div class="matchup-info">{match_info["venue"]} · {match_info["date"]}</div>
<div class="matchup-team {cls_a}"><span class="flag">{flag_a}</span><span class="team-name">{short_a}{adv_a}</span><span class="prob">{orig_pct_a}%</span></div>
<div class="matchup-team {cls_b}"><span class="flag">{flag_b}</span><span class="team-name">{short_b}{adv_b}</span><span class="prob">{orig_pct_b}%</span></div>
<div class="score-line">FT: {score_str}</div>
</div>'''

        # If both teams known, check for frozen predictions (R16 or QF)
        if team_a and team_b:
            # Try R16 predictions first, then QF predictions
            pred = None
            for pred_file in ["r16_predictions_frozen.json", "qf_predictions_frozen.json"]:
                pred_path = os.path.join(DATA_DIR, pred_file)
                if os.path.exists(pred_path):
                    with open(pred_path, "r", encoding="utf-8") as ff:
                        pred_data = json.load(ff)
                    pred = pred_data.get(str(match_num))
                    if pred:
                        break
            if pred:
                pct_a = pred["prob_a"]
                pct_b = pred["prob_b"]
                pred_winner = pred.get("predicted_winner", "")
                is_tossup = abs(pct_a - 50) <= 2
                if is_tossup:
                    cls_a = "tossup"
                    cls_b = "tossup"
                else:
                    cls_a = "predicted-winner" if pred_winner == team_a else "loser"
                    cls_b = "predicted-winner" if pred_winner == team_b else "loser"
                flag_a = FLAGS.get(team_a, "???")
                flag_b = FLAGS.get(team_b, "???")
                short_a = team_a.replace("Bosnia and Herzegovina", "Bosnia")
                short_b = team_b.replace("Bosnia and Herzegovina", "Bosnia")
                return f'''<div class="matchup">
<div class="matchup-info">{match_info["venue"]} · {match_info["date"]}</div>
<div class="matchup-team {cls_a}"><span class="flag">{flag_a}</span><span class="team-name">{short_a}</span><span class="prob">{pct_a}%</span></div>
<div class="matchup-team {cls_b}"><span class="flag">{flag_b}</span><span class="team-name">{short_b}</span><span class="prob">{pct_b}%</span></div>
</div>'''

        # Default: show known teams without prediction
        flag_a = FLAGS.get(team_a, "⬜") if team_a else "⬜"
        flag_b = FLAGS.get(team_b, "⬜") if team_b else "⬜"
        name_a = team_a.replace("Bosnia and Herzegovina", "Bosnia") if team_a else "—"
        name_b = team_b.replace("Bosnia and Herzegovina", "Bosnia") if team_b else "—"
        cls_a = "" if team_a else "tbd"
        cls_b = "" if team_b else "tbd"

        return f'''<div class="matchup empty-future">
<div class="matchup-info">{match_info["venue"]} · {match_info["date"]}</div>
<div class="matchup-team {cls_a}"><span class="flag">{flag_a}</span><span class="team-name">{name_a}</span></div>
<div class="matchup-team {cls_b}"><span class="flag">{flag_b}</span><span class="team-name">{name_b}</span></div>
</div>'''

    # Build lookup for bracket matches
    bracket_lookup = {}
    for rnd in ["r32", "r16", "qf", "sf", "final"]:
        for m in bracket[rnd]:
            bracket_lookup[m["match"]] = m

    # Generate individual matchup HTML strings
    l_r32 = [r32_matchup_html(n) for n in left_r32_nums]
    r_r32 = [r32_matchup_html(n) for n in right_r32_nums]
    l_r16 = [empty_slot_html(bracket_lookup[n]) for n in left_r16]
    r_r16 = [empty_slot_html(bracket_lookup[n]) for n in right_r16]
    l_qf = [empty_slot_html(bracket_lookup[n]) for n in left_qf]
    r_qf = [empty_slot_html(bracket_lookup[n]) for n in right_qf]
    l_sf = [empty_slot_html(bracket_lookup[n]) for n in left_sf]
    r_sf = [empty_slot_html(bracket_lookup[n]) for n in right_sf]
    final_html = empty_slot_html(bracket_lookup[104])

    # Assign individual slots for template
    l_r32_0, l_r32_1, l_r32_2, l_r32_3 = l_r32[0], l_r32[1], l_r32[2], l_r32[3]
    l_r32_4, l_r32_5, l_r32_6, l_r32_7 = l_r32[4], l_r32[5], l_r32[6], l_r32[7]
    r_r32_0, r_r32_1, r_r32_2, r_r32_3 = r_r32[0], r_r32[1], r_r32[2], r_r32[3]
    r_r32_4, r_r32_5, r_r32_6, r_r32_7 = r_r32[4], r_r32[5], r_r32[6], r_r32[7]
    l_r16_0, l_r16_1, l_r16_2, l_r16_3 = l_r16[0], l_r16[1], l_r16[2], l_r16[3]
    r_r16_0, r_r16_1, r_r16_2, r_r16_3 = r_r16[0], r_r16[1], r_r16[2], r_r16[3]
    l_qf_0, l_qf_1 = l_qf[0], l_qf[1]
    r_qf_0, r_qf_1 = r_qf[0], r_qf[1]
    l_sf_0 = l_sf[0]
    r_sf_0 = r_sf[0]

    filepath = os.path.join(PUBLIC_DIR, "bracket.html")
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>World Cup 2026 — Tournament Bracket</title>
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<style>
:root {{
    --wc-green:#3CAC3B;--wc-blue:#2A398D;--wc-red:#E61D25;
    --bg:#FAFAFA;--card-bg:#FFF;--card-border:#E2E4E2;
    --text-primary:#1A1A1A;--text-secondary:#3D3D3D;--text-muted:#666;
    --bar-bg:#ECEEED;--hover-shadow:rgba(42,57,141,.08);
    --win-green:#2D8A2C;--lose-gray:#999;
}}
@media(prefers-color-scheme:dark){{:root{{
    --bg:#0F1318;--card-bg:#1A1F27;--card-border:#2D333B;
    --text-primary:#FFFFFF;--text-secondary:#D4D4D4;--text-muted:#A0A0A0;
    --bar-bg:#2D333B;--hover-shadow:rgba(88,166,255,.1);
    --win-green:#56D364;--lose-gray:#555;
}}}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text-primary);padding:20px;min-height:100vh}}
h1{{text-align:center;font-size:1.7rem;color:var(--wc-blue);margin-bottom:4px}}
.subtitle{{text-align:center;color:var(--text-secondary);font-size:.82rem;margin-bottom:8px}}
.methodology{{font-size:0.72rem;color:var(--text-muted);text-align:center;margin-bottom:12px}}
.nav{{text-align:center;margin-bottom:24px;font-size:.85rem}}
.nav-link{{color:var(--text-secondary);text-decoration:none;padding:4px 10px;border-radius:4px}}
.nav-link:hover{{background:var(--bar-bg)}}
.nav-link.active{{color:var(--wc-blue);font-weight:600;background:rgba(42,57,141,.08)}}
@media(prefers-color-scheme:dark){{h1{{color:#79B8FF}}.nav-link.active{{color:#79B8FF;background:rgba(88,166,255,.12)}}}}

/* Bracket layout */
.bracket-scroll{{overflow-x:auto;overflow-y:visible;padding-bottom:20px}}
.bracket-wrapper{{display:flex;align-items:stretch;justify-content:center;gap:8px;padding:10px 0;min-width:max-content}}
.round{{display:flex;flex-direction:column;justify-content:space-around}}
.round-label{{text-align:center;font-size:.68rem;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px;white-space:nowrap}}

/* Matchup cards */
.matchup{{background:var(--card-bg);border:1px solid var(--card-border);border-radius:8px;width:195px;transition:transform .15s,box-shadow .15s}}
.matchup:hover{{transform:translateY(-1px);box-shadow:0 3px 10px var(--hover-shadow)}}
.matchup-info{{text-align:center;font-size:.58rem;color:var(--text-primary);padding:3px 6px;background:var(--bar-bg);border-bottom:1px solid var(--card-border);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.matchup-team{{display:flex;align-items:center;padding:5px 8px;font-size:.74rem;gap:5px}}
.matchup-team .flag{{font-size:.65rem;flex-shrink:0;font-weight:700;color:var(--text-secondary);min-width:28px}}
.matchup-team .team-name{{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.matchup-team .prob{{margin-left:auto;font-size:.62rem;font-weight:600;opacity:.7;flex-shrink:0}}
.matchup-team.winner{{font-weight:700;color:var(--win-green)}}
.matchup-team.winner .prob{{opacity:1}}
.matchup-team.actual-winner{{font-weight:700;color:var(--win-green)}}
.matchup-team.actual-winner .prob{{opacity:1}}
.matchup-team.predicted-winner{{font-weight:700;color:#E89B2D}}
.matchup-team.predicted-winner .prob{{opacity:1}}
.matchup-team.loser{{color:var(--lose-gray)}}
.matchup-team.tossup{{font-weight:600;color:var(--text-primary)}}
.matchup-team.tossup .prob{{opacity:.8}}
.matchup-team.tbd{{color:var(--text-muted);font-style:italic}}
.goals-line{{font-size:.58rem;color:var(--text-primary);text-align:center;padding:3px 6px;background:var(--bar-bg);border-top:1px solid var(--card-border)}}

/* Tooltip - removed, see predictions page instead */

/* Empty future matchups */
.empty-future{{opacity:.6;border-style:dashed}}

/* Completed matches */
.matchup.completed{{border-color:var(--win-green);border-left:3px solid var(--win-green)}}
.score-line{{font-size:.6rem;color:var(--text-primary);text-align:center;padding:3px 6px;background:var(--bar-bg);border-top:1px solid var(--card-border);font-weight:600}}

/* Bracket pair grouping — each pair stacks 2 matchups and centers them */
.bracket-pair{{display:flex;flex-direction:column;justify-content:center;gap:8px;flex:1;position:relative}}
.bracket-group{{display:flex;flex-direction:column;justify-content:center;gap:8px;flex:1}}
.round.final-col{{justify-content:center}}

/* Connector lines for LEFT side R32 pairs */
.left-side .bracket-pair{{padding-right:16px}}
.left-side .bracket-pair::after{{
    content:'';position:absolute;right:0;top:25%;bottom:25%;
    border-right:2px solid var(--card-border);
}}
.left-side .bracket-pair .matchup{{position:relative}}
.left-side .bracket-pair .matchup::after{{
    content:'';position:absolute;right:-16px;top:50%;
    width:16px;height:0;border-top:2px solid var(--card-border);
}}

/* Connector lines for RIGHT side R32 pairs */
.right-side .bracket-pair{{padding-left:16px}}
.right-side .bracket-pair::before{{
    content:'';position:absolute;left:0;top:25%;bottom:25%;
    border-left:2px solid var(--card-border);
}}
.right-side .bracket-pair .matchup{{position:relative}}
.right-side .bracket-pair .matchup::before{{
    content:'';position:absolute;left:-16px;top:50%;
    width:16px;height:0;border-top:2px solid var(--card-border);
}}
.round.r16-col,.round.qf-col,.round.sf-col,.round.final-col{{padding-top:20px}}

/* Legend */
.legend{{display:flex;justify-content:center;gap:16px;margin:16px 0;flex-wrap:wrap;font-size:.72rem;color:var(--text-secondary)}}
.legend-item{{display:flex;align-items:center;gap:4px}}
.leg-box{{width:12px;height:12px;border-radius:2px}}
.leg-winner{{background:var(--win-green)}}
.leg-predicted{{background:#E89B2D}}
.leg-tossup{{background:var(--text-primary)}}
.leg-empty{{background:var(--bar-bg);border:1px dashed var(--card-border)}}

/* Trophy */
.trophy{{text-align:center;font-size:2.5rem;margin:10px 0}}
</style>
</head>
<body>
<h1>⚽ World Cup 2026 — Tournament Bracket</h1>
<p class="subtitle">R32 predictions based on 6-dimension performance model · R16→Final shown as empty slots</p>
<p class="methodology">Only Round of 32 matchups are predicted. Later rounds show venue &amp; date placeholders.</p>
<div class="nav">{nav_html}</div>
<div class="legend">
<div class="legend-item"><div class="leg-box leg-winner"></div>Actual winner</div>
<div class="legend-item"><div class="leg-box leg-predicted"></div>Predicted winner</div>
<div class="legend-item"><div class="leg-box leg-tossup"></div>Toss-up (≤52%)</div>
<div class="legend-item"><div class="leg-box leg-empty"></div>TBD (future rounds)</div>
</div>

<div class="bracket-scroll">
<div class="bracket-wrapper">
<!-- LEFT SIDE: R32 → R16 → QF → SF -->
<div class="round left-side">
<div class="round-label">Round of 32</div>
<div class="bracket-group">
<div class="bracket-pair">{l_r32_0}{l_r32_1}</div>
<div class="bracket-pair">{l_r32_2}{l_r32_3}</div>
<div class="bracket-pair">{l_r32_4}{l_r32_5}</div>
<div class="bracket-pair">{l_r32_6}{l_r32_7}</div>
</div>
</div>

<div class="round left-side">
<div class="round-label">Round of 16</div>
<div class="bracket-group">
<div class="bracket-pair">{l_r16_0}</div>
<div class="bracket-pair">{l_r16_1}</div>
<div class="bracket-pair">{l_r16_2}</div>
<div class="bracket-pair">{l_r16_3}</div>
</div>
</div>

<div class="round left-side">
<div class="round-label">Quarterfinals</div>
<div class="bracket-group">
<div class="bracket-pair">{l_qf_0}</div>
<div class="bracket-pair">{l_qf_1}</div>
</div>
</div>

<div class="round left-side">
<div class="round-label">Semifinals</div>
<div class="bracket-group">
<div class="bracket-pair">{l_sf_0}</div>
</div>
</div>

<!-- CENTER: FINAL -->
<div class="round final-col">
<div class="round-label">Final</div>
<div class="bracket-group">
<div class="trophy">🏆</div>
{final_html}
</div>
</div>

<!-- RIGHT SIDE: SF → QF → R16 → R32 -->
<div class="round right-side">
<div class="round-label">Semifinals</div>
<div class="bracket-group">
<div class="bracket-pair">{r_sf_0}</div>
</div>
</div>

<div class="round right-side">
<div class="round-label">Quarterfinals</div>
<div class="bracket-group">
<div class="bracket-pair">{r_qf_0}</div>
<div class="bracket-pair">{r_qf_1}</div>
</div>
</div>

<div class="round right-side">
<div class="round-label">Round of 16</div>
<div class="bracket-group">
<div class="bracket-pair">{r_r16_0}</div>
<div class="bracket-pair">{r_r16_1}</div>
<div class="bracket-pair">{r_r16_2}</div>
<div class="bracket-pair">{r_r16_3}</div>
</div>
</div>

<div class="round right-side">
<div class="round-label">Round of 32</div>
<div class="bracket-group">
<div class="bracket-pair">{r_r32_0}{r_r32_1}</div>
<div class="bracket-pair">{r_r32_2}{r_r32_3}</div>
<div class="bracket-pair">{r_r32_4}{r_r32_5}</div>
<div class="bracket-pair">{r_r32_6}{r_r32_7}</div>
</div>
</div>
</div>
</div>
<p style="text-align:center;font-size:.7rem;color:var(--text-muted);margin-top:8px">← Scroll horizontally to see full bracket →</p>

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

    # Load actual R32 results
    print("\n[3] Loading R32 results...")
    r32_results_path = os.path.join(DATA_DIR, "r32_results.json")
    actual_results = None
    if os.path.exists(r32_results_path):
        with open(r32_results_path, "r", encoding="utf-8") as f:
            actual_results = json.load(f)
        completed_count = len(actual_results.get("completed", []))
        print(f"    {completed_count} matches completed, {len(actual_results.get('upcoming', []))} upcoming")
    else:
        print("    No results file found — all predictions")

    # Load frozen predictions (so odds don't change with new data)
    print("\n[3b] Loading frozen predictions...")
    frozen_path = os.path.join(DATA_DIR, "r32_predictions_frozen.json")
    frozen_predictions = None
    if os.path.exists(frozen_path):
        with open(frozen_path, "r", encoding="utf-8") as f:
            frozen_predictions = json.load(f)
        print(f"    Loaded {len(frozen_predictions)} frozen R32 predictions")
    else:
        print("    No frozen file — will compute live")

    # Predict R32 (uses frozen predictions + actual results for completed)
    print(f"\n[4] Building R32 bracket ({len(all_scores)} teams)...")
    results = predict_r32(bracket, all_scores, actual_results, frozen_predictions)

    # Print R32 results/predictions
    print("\n    Round of 32:")
    for match in bracket["r32"]:
        r = results[match["match"]]
        if r.get("completed"):
            print(f"    M{match['match']}: {r['team_a']:20s} vs {r['team_b']:20s} → {r['winner']} (FINAL: {r['score']})")
        elif r["team_b"] == "TBD":
            print(f"    M{match['match']}: {r['team_a']:20s} vs {'TBD':20s} → {r['winner']} (BYE)")
        else:
            prob = max(r["prob_a"], r["prob_b"])
            print(f"    M{match['match']}: {r['team_a']:20s} vs {r['team_b']:20s} → {r['winner']} ({prob:.0%})")

    # Generate HTML
    print("\n[5] Generating bracket page...")
    generate_bracket_html(results, bracket, all_scores)

    print("\n" + "=" * 60)
    print("  Done!")
    print("=" * 60)


if __name__ == "__main__":
    main()
