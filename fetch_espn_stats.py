"""
Automated World Cup 2026 Stats Fetcher using ESPN's public API.

Fetches match results and detailed team statistics from ESPN's core API,
updates each team's CSV file, then runs the ratings computation.

Usage:
    python fetch_espn_stats.py                  # Fetch all matches (full tournament)
    python fetch_espn_stats.py --date 20260616  # Fetch matches for a specific date
    python fetch_espn_stats.py --today          # Fetch today's completed matches
    python fetch_espn_stats.py --loop 30        # Poll every 30 minutes continuously

No API key required.
"""

import json
import csv
import os
import sys
import time
import argparse
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

# ============ CONFIGURATION ============
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.environ.get("REPO_DIR", SCRIPT_DIR)

DATA_DIR = os.path.join(REPO_DIR, "data")
BASE_URL = "https://sports.core.api.espn.com/v2/sports/soccer/leagues/fifa.world"
SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"

# Tournament date range
TOURNAMENT_START = "20260611"
TOURNAMENT_END = "20260720"

# CSV header — expanded with full ESPN stats
CSV_HEADER = [
    # Match info
    "Match Number", "Date", "Time (EST)", "Opponent",
    # Offensive
    "Goals", "Shots", "Shots on target", "Shots off target", "Shots on post",
    "Shot Accuracy", "Attempts inside box", "Attempts outside box",
    "Headed shots", "Headed goals", "Left footed shots", "Right footed shots",
    "Free kick shots", "Free kick goals", "Penalty kicks", "Penalty kick goals",
    "Possession", "Possession time", "Passes", "Accurate passes", "Pass Accuracy",
    "Long balls", "Accurate long balls", "Long ball pct",
    "Crosses", "Accurate crosses", "Cross pct",
    "Through balls", "Accurate through balls",
    "Assists", "Shot assists", "Offsides",
    "xG", "xG non-penalty", "xG open play", "xG set play",
    "xG on target", "xA", "xA open play", "xA set play",
    "Big chances created", "Big chances missed",
    "Final third entries", "Penalty area entries",
    "Successful final third passes", "Total final third passes",
    "Touches in opp box", "Dispossessed", "Unsuccessful touches",
    "Fouled in final third", "Total fastbreaks",
    "Accurate throws", "Total throws",
    "Total back zone pass", "Total fwd zone pass",
    # General (selected)
    "Fouls committed", "Fouls suffered", "Yellow cards", "Red cards",
    "Corners won", "Corners conceded",
    "Aerials won", "Aerials lost", "Aerial duel pct",
    "Duels", "Duels won", "Duels lost", "Duel win pct",
    "Ground duels", "Ground duels won",
    "Contests won", "Total contests", "Touches", "Pass pct",
    # Defensive (all)
    "Blocked shots", "Effective clearances", "Total clearances",
    "Tackles won", "Tackles lost", "Total tackles", "Tackle pct",
    "Interceptions", "Ball recoveries",
    "Poss won att 3rd", "Poss won mid 3rd", "Poss won def 3rd",
    "Attempts conceded inside box", "Attempts conceded outside box",
    "PPDA", "FK fouls lost", "Challenges lost", "Defensive actions",
    # Goalkeeping (all)
    "Clean sheet", "Goals conceded", "Saves", "Save pct",
    "Shots faced", "Crosses claimed", "Unclaimed crosses", "Punches", "Smothers",
    "PK faced", "PK saved", "PK save pct", "PK conceded",
    "Shootout kicks faced", "Shootout saves", "Shootout save pct",
    "xG conceded", "xG conceded non-pen",
    "xG on target conceded", "xG on target conceded non-pen",
    "Accurate sweeper actions", "Total sweeper actions",
    "Good high claims", "Total high claims",
    "Accurate goal kicks", "Goal kicks",
    "Accurate keeper throws", "Keeper throws",
    "Goals prevented", "Shots on goal against",
]


def fetch_json(url, retries=3):
    """Fetch JSON from a URL with retry logic."""
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError) as e:
            if attempt < retries - 1:
                print(f"    Retry {attempt + 1}/{retries} for {url}: {e}")
                time.sleep(2)
            else:
                print(f"    FAILED: {url} — {e}")
                return None


def get_scoreboard(date_str=None):
    """Get the scoreboard for a given date (YYYYMMDD format) or today."""
    url = SCOREBOARD_URL
    if date_str:
        url += f"?dates={date_str}"
    return fetch_json(url)


def get_team_stats(event_id, team_id):
    """Fetch detailed team statistics for a specific match."""
    url = f"{BASE_URL}/events/{event_id}/competitions/{event_id}/competitors/{team_id}/statistics"
    return fetch_json(url)


def extract_stat(stats_data, category_name, stat_name):
    """Extract a specific stat value from the ESPN statistics response."""
    if not stats_data or "splits" not in stats_data:
        return None
    categories = stats_data["splits"].get("categories", [])
    for cat in categories:
        if cat["name"] == category_name:
            for stat in cat["stats"]:
                if stat["name"] == stat_name:
                    return stat["value"]
    return None


def parse_competition(competition):
    """Parse a competition (match) from the scoreboard response."""
    status = competition.get("status", {})
    state = status.get("type", {}).get("state", "")

    # Only process completed matches
    if state != "post":
        return None

    competitors = competition.get("competitors", [])
    if len(competitors) != 2:
        return None

    event_id = competition["id"]
    date_str = competition.get("date", "")

    # Parse date to EST
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        est_time = dt - timedelta(hours=4)  # UTC to EST (approximate, ignores DST)
        date_formatted = est_time.strftime("%-m/%-d/%Y") if os.name != "nt" else est_time.strftime("%#m/%#d/%Y")
        time_est = est_time.strftime("%H:%M")
    except (ValueError, OSError):
        date_formatted = date_str[:10]
        time_est = ""

    match_info = {
        "event_id": event_id,
        "date": date_formatted,
        "time_est": time_est,
        "teams": {}
    }

    for comp in competitors:
        team_data = comp.get("team", {})
        team_id = comp["id"]
        team_name = team_data.get("displayName", "Unknown")
        score = int(comp.get("score", 0))
        home_away = comp.get("homeAway", "")

        match_info["teams"][team_id] = {
            "name": team_name,
            "score": score,
            "home_away": home_away,
            "espn_id": team_id,
        }

    return match_info


def build_team_row(match_info, team_id, opponent_id, stats_data, match_number):
    """Build a CSV row dict from ESPN stats for one team in one match."""
    team = match_info["teams"][team_id]
    opponent = match_info["teams"][opponent_id]

    def stat(cat, name):
        return extract_stat(stats_data, cat, name)

    def int_stat(cat, name):
        v = stat(cat, name)
        return int(v) if v is not None else ""

    def float_stat(cat, name, decimals=2):
        v = stat(cat, name)
        return round(v, decimals) if v is not None else ""

    def pct_str(cat, name):
        v = stat(cat, name)
        if v is not None:
            return f"{int(round(v * 100))}%" if v <= 1.0 else f"{int(round(v))}%"
        return ""

    # Possession is already 0-100 scale
    possession = stat("offensive", "possessionPct")
    possession_str = f"{int(round(possession))}%" if possession is not None else ""

    # Shot accuracy derived
    shots = stat("offensive", "totalShots")
    sot = stat("offensive", "shotsOnTarget")
    shot_accuracy = ""
    if shots and sot and shots > 0:
        shot_accuracy = f"{int(round(sot / shots * 100))}%"

    # Pass accuracy derived
    passes = stat("offensive", "totalPasses")
    acc_passes = stat("offensive", "accuratePasses")
    pass_accuracy = ""
    if passes and acc_passes and passes > 0:
        pass_accuracy = f"{int(round(acc_passes / passes * 100))}%"

    row = {
        # Match info
        "Match Number": match_number,
        "Date": match_info["date"],
        "Time (EST)": match_info["time_est"],
        "Opponent": normalize_team_name(opponent["name"]),
        # Offensive
        "Goals": team["score"],
        "Shots": int_stat("offensive", "totalShots"),
        "Shots on target": int_stat("offensive", "shotsOnTarget"),
        "Shots off target": int_stat("offensive", "shotsOffTarget"),
        "Shots on post": int_stat("offensive", "shotsOnPost"),
        "Shot Accuracy": shot_accuracy,
        "Attempts inside box": int_stat("offensive", "attemptsIbox"),
        "Attempts outside box": int_stat("offensive", "attemptsObox"),
        "Headed shots": int_stat("offensive", "shotsHeaded"),
        "Headed goals": int_stat("offensive", "headedGoals"),
        "Left footed shots": int_stat("offensive", "leftFootedShots"),
        "Right footed shots": int_stat("offensive", "rightFootedShots"),
        "Free kick shots": int_stat("offensive", "freeKickShots"),
        "Free kick goals": int_stat("offensive", "freeKickGoals"),
        "Penalty kicks": int_stat("offensive", "penaltyKickShots"),
        "Penalty kick goals": int_stat("offensive", "penaltyKickGoals"),
        "Possession": possession_str,
        "Possession time": float_stat("offensive", "possessionTime"),
        "Passes": int_stat("offensive", "totalPasses"),
        "Accurate passes": int_stat("offensive", "accuratePasses"),
        "Pass Accuracy": pass_accuracy,
        "Long balls": int_stat("offensive", "totalLongBalls"),
        "Accurate long balls": int_stat("offensive", "accurateLongBalls"),
        "Long ball pct": float_stat("offensive", "longballPct"),
        "Crosses": int_stat("offensive", "totalCrosses"),
        "Accurate crosses": int_stat("offensive", "accurateCrosses"),
        "Cross pct": float_stat("offensive", "crossPct"),
        "Through balls": int_stat("offensive", "totalThroughBalls"),
        "Accurate through balls": int_stat("offensive", "accurateThroughBalls"),
        "Assists": int_stat("offensive", "goalAssists"),
        "Shot assists": int_stat("offensive", "shotAssists"),
        "Offsides": int_stat("offensive", "offsides"),
        "xG": float_stat("offensive", "expectedGoals"),
        "xG non-penalty": float_stat("offensive", "expectedGoalsNonPenalty"),
        "xG open play": float_stat("offensive", "expectedGoalsOpenPlay"),
        "xG set play": float_stat("offensive", "expectedGoalsSetPlay"),
        "xG on target": float_stat("offensive", "expectedGoalsOnTarget"),
        "xA": float_stat("offensive", "expectedAssists"),
        "xA open play": float_stat("offensive", "expectedAssistsOpenPlay"),
        "xA set play": float_stat("offensive", "expectedAssistsSetPlay"),
        "Big chances created": int_stat("offensive", "bigChanceCreated"),
        "Big chances missed": int_stat("offensive", "bigChanceMissed"),
        "Final third entries": int_stat("offensive", "finalThirdEntries"),
        "Penalty area entries": int_stat("offensive", "penAreaEntries"),
        "Successful final third passes": int_stat("offensive", "successfulFinalThirdPasses"),
        "Total final third passes": int_stat("offensive", "totalFinalThirdPasses"),
        "Touches in opp box": int_stat("offensive", "touchesInOppBox"),
        "Dispossessed": int_stat("offensive", "dispossessed"),
        "Unsuccessful touches": int_stat("offensive", "unsuccessfulTouch"),
        "Fouled in final third": int_stat("offensive", "fouledFinalThird"),
        "Total fastbreaks": int_stat("offensive", "totalFastbreak"),
        "Accurate throws": int_stat("offensive", "accurateThrows"),
        "Total throws": int_stat("offensive", "totalThrows"),
        "Total back zone pass": int_stat("offensive", "totalBackZonePass"),
        "Total fwd zone pass": int_stat("offensive", "totalFwdZonePass"),
        # General (selected)
        "Fouls committed": int_stat("general", "foulsCommitted"),
        "Fouls suffered": int_stat("general", "foulsSuffered"),
        "Yellow cards": int_stat("general", "yellowCards"),
        "Red cards": int_stat("general", "redCards"),
        "Corners won": int_stat("general", "wonCorners"),
        "Corners conceded": int_stat("general", "lostCorners"),
        "Aerials won": int_stat("general", "aerialsWon"),
        "Aerials lost": int_stat("general", "aerialsLost"),
        "Aerial duel pct": float_stat("general", "aerialDuelPct"),
        "Duels": int_stat("general", "duels"),
        "Duels won": int_stat("general", "duelsWon"),
        "Duels lost": int_stat("general", "duelsLost"),
        "Duel win pct": float_stat("general", "duelWinPct"),
        "Ground duels": int_stat("general", "groundDuels"),
        "Ground duels won": int_stat("general", "groundDuelsWon"),
        "Contests won": int_stat("general", "wonContest"),
        "Total contests": int_stat("general", "totalContest"),
        "Touches": int_stat("general", "touches"),
        "Pass pct": float_stat("general", "passPct"),
        # Defensive (all)
        "Blocked shots": int_stat("defensive", "blockedShots"),
        "Effective clearances": int_stat("defensive", "effectiveClearance"),
        "Total clearances": int_stat("defensive", "totalClearance"),
        "Tackles won": int_stat("defensive", "effectiveTackles"),
        "Tackles lost": int_stat("defensive", "inneffectiveTackles"),
        "Total tackles": int_stat("defensive", "totalTackles"),
        "Tackle pct": float_stat("defensive", "tacklePct"),
        "Interceptions": int_stat("defensive", "interceptions"),
        "Ball recoveries": int_stat("defensive", "ballRecovery"),
        "Poss won att 3rd": int_stat("defensive", "possWonAtt3rd"),
        "Poss won mid 3rd": int_stat("defensive", "possWonMid3rd"),
        "Poss won def 3rd": int_stat("defensive", "possWonDef3rd"),
        "Attempts conceded inside box": int_stat("defensive", "attemptsConcededIbox"),
        "Attempts conceded outside box": int_stat("defensive", "attemptsConcededObox"),
        "PPDA": float_stat("defensive", "ppda", 1),
        "FK fouls lost": int_stat("defensive", "fkFoulLost"),
        "Challenges lost": int_stat("defensive", "challengeLost"),
        "Defensive actions": int_stat("defensive", "defensiveActions"),
        # Goalkeeping (all)
        "Clean sheet": int_stat("goalKeeping", "cleanSheet"),
        "Goals conceded": int_stat("goalKeeping", "goalsConceded"),
        "Saves": int_stat("goalKeeping", "saves"),
        "Save pct": float_stat("goalKeeping", "savePct"),
        "Shots faced": int_stat("goalKeeping", "shotsFaced"),
        "Crosses claimed": int_stat("goalKeeping", "crossesCaught"),
        "Unclaimed crosses": int_stat("goalKeeping", "unclaimedCrosses"),
        "Punches": int_stat("goalKeeping", "punches"),
        "Smothers": int_stat("goalKeeping", "smothers"),
        "PK faced": int_stat("goalKeeping", "penaltyKicksFaced"),
        "PK saved": int_stat("goalKeeping", "penaltyKicksSaved"),
        "PK save pct": float_stat("goalKeeping", "penaltyKickSavePct"),
        "PK conceded": int_stat("goalKeeping", "penaltyKickConceded"),
        "Shootout kicks faced": int_stat("goalKeeping", "shootOutKicksFaced"),
        "Shootout saves": int_stat("goalKeeping", "shootOutKicksSaved"),
        "Shootout save pct": float_stat("goalKeeping", "shootOutSavePct"),
        "xG conceded": float_stat("goalKeeping", "expectedGoalsConceded"),
        "xG conceded non-pen": float_stat("goalKeeping", "expectedGoalsNonPenaltyConceded"),
        "xG on target conceded": float_stat("goalKeeping", "expectedGoalsOnTargetConceded"),
        "xG on target conceded non-pen": float_stat("goalKeeping", "expectedGoalsOnTargetNonPenaltyConceded"),
        "Accurate sweeper actions": int_stat("goalKeeping", "accurateKeeperSweeper"),
        "Total sweeper actions": int_stat("goalKeeping", "totalKeeperSweeper"),
        "Good high claims": int_stat("goalKeeping", "goodHighClaim"),
        "Total high claims": int_stat("goalKeeping", "totalHighClaim"),
        "Accurate goal kicks": int_stat("goalKeeping", "accurateGoalKicks"),
        "Goal kicks": int_stat("goalKeeping", "goalKicks"),
        "Accurate keeper throws": int_stat("goalKeeping", "accurateKeeperThrows"),
        "Keeper throws": int_stat("goalKeeping", "keeperThrows"),
        "Goals prevented": float_stat("goalKeeping", "goalsPrevented"),
        "Shots on goal against": int_stat("goalKeeping", "shotsOnGoalAgainst"),
    }
    return row


def read_existing_csv(team_name):
    """Read existing CSV for a team and return rows + opponents already recorded."""
    filepath = os.path.join(DATA_DIR, f"{team_name}.csv")
    if not os.path.exists(filepath):
        return [], set()

    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    existing_opponents = set()
    for row in rows:
        opp = row.get("Opponent", "").strip()
        goals = row.get("Goals", "").strip()
        if opp and goals:  # Only count as recorded if Goals is filled in
            existing_opponents.add(opp)

    return rows, existing_opponents


def write_team_csv(team_name, rows):
    """Write (overwrite) the team CSV with updated rows."""
    filepath = os.path.join(DATA_DIR, f"{team_name}.csv")
    try:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_HEADER, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        return True
    except PermissionError:
        print(f"    SKIPPED (file locked): {team_name}.csv")
        return False


def get_all_dates(start, end):
    """Generate a list of date strings (YYYYMMDD) between start and end."""
    dates = []
    current = datetime.strptime(start, "%Y%m%d")
    end_dt = datetime.strptime(end, "%Y%m%d")
    while current <= end_dt:
        dates.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    return dates


# ESPN team name → your CSV filename mapping
# This handles cases where ESPN uses a different display name
NAME_MAP = {
    "United States": "USA",
    "Korea Republic": "South Korea",
    "Côte d'Ivoire": "Ivory Coast",
    "Türkiye": "Turkey",
    "Congo DR": "DR Congo",
    "Curaçao": "Curacao",
    "Cabo Verde": "Cape Verde",
    "Czechia": "Czech Republic",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
}


def normalize_team_name(espn_name):
    """Convert ESPN display name to your local CSV filename."""
    return NAME_MAP.get(espn_name, espn_name)


def fetch_and_update(date_str=None, force=False):
    """
    Fetch matches for a date (or today), get stats, and update CSVs.
    Returns number of new matches processed.
    """
    print(f"\n{'='*60}")
    print(f"  Fetching: {date_str or 'today'}")
    print(f"{'='*60}")

    scoreboard = get_scoreboard(date_str)
    if not scoreboard:
        print("  Failed to fetch scoreboard.")
        return 0

    events = scoreboard.get("events", [])
    if not events:
        print("  No events found for this date.")
        return 0

    new_matches = 0

    for event in events:
        competitions = event.get("competitions", [])
        for competition in competitions:
            match_info = parse_competition(competition)
            if not match_info:
                continue  # Not completed yet

            event_id = match_info["event_id"]
            team_ids = list(match_info["teams"].keys())
            if len(team_ids) != 2:
                continue

            team_a_id, team_b_id = team_ids[0], team_ids[1]
            team_a_name = normalize_team_name(match_info["teams"][team_a_id]["name"])
            team_b_name = normalize_team_name(match_info["teams"][team_b_id]["name"])

            print(f"\n  Match: {team_a_name} vs {team_b_name}")

            # Check if already recorded
            _, existing_a = read_existing_csv(team_a_name)
            _, existing_b = read_existing_csv(team_b_name)

            if team_b_name in existing_a and team_a_name in existing_b and not force:
                print(f"    Already recorded. Skipping.")
                continue

            # Fetch detailed stats for both teams
            print(f"    Fetching stats for {team_a_name}...")
            stats_a = get_team_stats(event_id, team_a_id)
            time.sleep(0.5)  # Be polite to the API

            print(f"    Fetching stats for {team_b_name}...")
            stats_b = get_team_stats(event_id, team_b_id)
            time.sleep(0.5)

            # Process team A
            if team_b_name not in existing_a or force:
                rows_a, _ = read_existing_csv(team_a_name)
                # Determine match number
                played_count = sum(1 for r in rows_a if r.get("Goals", "").strip())
                match_num = played_count + 1

                if stats_a:
                    new_row = build_team_row(match_info, team_a_id, team_b_id, stats_a, match_num)
                    # Replace existing row for this opponent or append
                    replaced = False
                    for i, row in enumerate(rows_a):
                        if row.get("Opponent", "").strip() == team_b_name:
                            rows_a[i] = new_row
                            replaced = True
                            break
                    if not replaced:
                        rows_a.append(new_row)

                    if write_team_csv(team_a_name, rows_a):
                        print(f"    ✓ Updated {team_a_name}.csv")
                else:
                    print(f"    ✗ No stats available for {team_a_name}")

            # Process team B
            if team_a_name not in existing_b or force:
                rows_b, _ = read_existing_csv(team_b_name)
                played_count = sum(1 for r in rows_b if r.get("Goals", "").strip())
                match_num = played_count + 1

                if stats_b:
                    new_row = build_team_row(match_info, team_b_id, team_a_id, stats_b, match_num)
                    replaced = False
                    for i, row in enumerate(rows_b):
                        if row.get("Opponent", "").strip() == team_a_name:
                            rows_b[i] = new_row
                            replaced = True
                            break
                    if not replaced:
                        rows_b.append(new_row)

                    if write_team_csv(team_b_name, rows_b):
                        print(f"    ✓ Updated {team_b_name}.csv")
                else:
                    print(f"    ✗ No stats available for {team_b_name}")

            new_matches += 1

    return new_matches


def fetch_all_tournament(force=False):
    """Fetch all completed matches across the entire tournament."""
    today = datetime.now().strftime("%Y%m%d")
    end = min(today, TOURNAMENT_END)
    dates = get_all_dates(TOURNAMENT_START, end)

    total_new = 0
    for date_str in dates:
        new = fetch_and_update(date_str, force=force)
        total_new += new
        if new > 0:
            time.sleep(1)  # Pause between days with matches

    return total_new


def run_ratings():
    """Run the compute_ratings.py script after updating."""
    print("\n" + "=" * 60)
    print("  Running ratings computation...")
    print("=" * 60)
    import subprocess
    result = subprocess.run(
        [sys.executable, os.path.join(SCRIPT_DIR, "compute_ratings.py")],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        env={**os.environ, "REPO_DIR": REPO_DIR},
    )
    if result.returncode == 0:
        print("  ✓ Ratings updated successfully.")
    else:
        print(f"  ✗ Ratings script failed:\n{result.stderr}")


def main():
    parser = argparse.ArgumentParser(description="Fetch World Cup 2026 stats from ESPN API")
    parser.add_argument("--date", help="Fetch for specific date (YYYYMMDD format)")
    parser.add_argument("--today", action="store_true", help="Fetch today's completed matches")
    parser.add_argument("--all", action="store_true", help="Fetch all tournament matches")
    parser.add_argument("--loop", type=int, metavar="MINUTES",
                        help="Run continuously, polling every N minutes")
    parser.add_argument("--force", action="store_true",
                        help="Re-fetch even if match already recorded")
    parser.add_argument("--no-ratings", action="store_true",
                        help="Skip running compute_ratings.py after fetch")
    args = parser.parse_args()

    print("=" * 60)
    print("  World Cup 2026 — ESPN API Auto-Fetcher")
    print("=" * 60)

    if args.loop:
        print(f"\n  Running in loop mode (every {args.loop} minutes)")
        print("  Press Ctrl+C to stop.\n")
        while True:
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"\n[{timestamp}] Polling...")
                new = fetch_and_update(force=args.force)
                if new > 0 and not args.no_ratings:
                    run_ratings()
                print(f"  Sleeping {args.loop} minutes...")
                time.sleep(args.loop * 60)
            except KeyboardInterrupt:
                print("\n\n  Stopped by user.")
                break
    elif args.all:
        total = fetch_all_tournament(force=args.force)
        print(f"\n  Total new matches processed: {total}")
        if total > 0 and not args.no_ratings:
            run_ratings()
    elif args.date:
        new = fetch_and_update(args.date, force=args.force)
        if new > 0 and not args.no_ratings:
            run_ratings()
    else:
        # Default: fetch today
        new = fetch_and_update(force=args.force)
        if new > 0 and not args.no_ratings:
            run_ratings()

    print("\n  Done!")


if __name__ == "__main__":
    main()
