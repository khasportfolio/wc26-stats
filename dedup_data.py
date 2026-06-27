"""
Deduplicate team CSVs.

Fixes issues where ESPN name normalization created duplicate rows for the same match.
For each team, if multiple rows exist for the same date, keep the one with the most
non-empty fields (the fully-fetched version).
"""

import csv
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(SCRIPT_DIR, "data")

SKIP_FILES = {"team_ratings.csv", "qualified_r32.txt", "team.txt"}

# Known ESPN name variants that map to the same opponent
NAME_VARIANTS = {
    "United States": "USA",
    "Türkiye": "Turkey",
    "Curaçao": "Curacao",
    "Czechia": "Czech Republic",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Congo DR": "DR Congo",
    "Côte d'Ivoire": "Ivory Coast",
    "Cabo Verde": "Cape Verde",
    "Korea Republic": "South Korea",
}


def normalize_opponent(name):
    return NAME_VARIANTS.get(name.strip(), name.strip())


def count_filled(row):
    """Count non-empty fields in a row."""
    return sum(1 for v in row.values() if v and str(v).strip())


def dedup_team(filepath):
    """Remove duplicate rows from a team CSV. Returns (original_count, deduped_count)."""
    with open(filepath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    if not rows:
        return 0, 0

    original_count = len(rows)

    # Group rows by (Date, normalized Opponent)
    seen = {}
    for row in rows:
        date = row.get("Date", "").strip()
        opponent = normalize_opponent(row.get("Opponent", ""))
        goals = row.get("Goals", "").strip()

        if not goals:
            continue  # Skip unplayed matches

        key = (date, opponent)
        if key not in seen:
            seen[key] = row
        else:
            # Keep the row with more data
            if count_filled(row) > count_filled(seen[key]):
                seen[key] = row

    deduped = list(seen.values())

    # Also normalize opponent names in the kept rows
    for row in deduped:
        row["Opponent"] = normalize_opponent(row.get("Opponent", ""))

    if len(deduped) < original_count:
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(deduped)

    return original_count, len(deduped)


def main():
    print("=" * 60)
    print("  Deduplicating team CSVs")
    print("=" * 60)

    fixed = 0
    for f in sorted(os.listdir(DATA_DIR)):
        if not f.endswith(".csv") or f in SKIP_FILES:
            continue
        filepath = os.path.join(DATA_DIR, f)
        orig, deduped = dedup_team(filepath)
        if deduped < orig:
            team = f.replace(".csv", "")
            print(f"  Fixed {team}: {orig} → {deduped} rows")
            fixed += 1

    if fixed == 0:
        print("  No duplicates found.")
    else:
        print(f"\n  Fixed {fixed} files.")


if __name__ == "__main__":
    main()
