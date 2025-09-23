import json
import os
import re
from typing import List
import argparse


ZIP_URL = (
    "https://www.vote.nyc/sites/default/files/pdf/election_results/2025/"
    "20250624Primary%20Election/rcv/2025_Primary_CVR_2025-07-17.zip"
)
LOCALCOPY = "2025_Primary_CVR_2025-07-17.zip"
METAURL = "https://vote.nyc/page/election-results-summary"
DOWNLOAD_SUBDIR = "downloads/newyork"
ABIFLOC_SUBDIR = "localabif/newyork"


def slugify(s: str) -> str:
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s


def make_item(contest_string: str, abif_suffix: str) -> dict:
    return {
        "url": ZIP_URL,
        "localcopy": LOCALCOPY,
        "metaurls": [METAURL],
        "desc": f"2025 NYC Primary Election - {contest_string}",
        "abifloc": f"nyc2025-primary-{abif_suffix}.abif",
        "contest_string": contest_string,
    }


def council_items_for_party(party: str, districts: List[int]) -> List[dict]:
    items = []
    for d in districts:
        # Prefer zero-padded in both abif name and contest string to avoid ambiguity
        d2 = f"{d:02d}"
        contest = f"{party} Council Member District {d2}"
        abif_suffix = slugify(f"{party} council member d{d2}")
        item = make_item(contest, abif_suffix)
        item['district'] = d
        items.append(item)
    return items


def borough_president_items_for_party(party: str) -> List[dict]:
    items = []
    # NYC standard phrasing is "<Borough> Borough President"
    boroughs = [
        "Manhattan",
        "Bronx",
        "Brooklyn",
        "Queens",
        "Staten Island",
    ]
    for b in boroughs:
        contest = f"{party} {b} Borough President"
        abif_suffix = slugify(f"{party} {b} borough president")
        items.append(make_item(contest, abif_suffix))
    return items


def citywide_items_for_party(party: str, offices: List[str]) -> List[dict]:
    items = []
    for office in offices:
        contest = f"{party} {office}"
        suffix = slugify(f"{party} {office}")
        # Keep historical special-case name for DEM Mayor to avoid breaking paths
        if party == "DEM" and office.lower() == "mayor":
            items.append(
                make_item(contest_string=contest, abif_suffix="dem-mayor-citywide")
            )
        else:
            items.append(make_item(contest_string=contest, abif_suffix=suffix))
    return items


def parse_all_columns_if_present() -> List[str]:
    """If all_columns.txt exists, extract distinct contest strings from it.

    Expected line format contains " Choice "; everything before that is the
    contest string, which may already include borough/district identifiers.
    """
    path = "all_columns.txt"
    if not os.path.exists(path):
        return []
    contests = set()
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if " Choice " not in line:
                continue
            contest = line.split(" Choice ", 1)[0].strip()
            if contest:
                contests.add(contest)
    return sorted(contests)


def build_web_urls() -> List[dict]:
    # If we have a pre-scanned column list, use it verbatim — most precise.
    discovered = parse_all_columns_if_present()
    if discovered:
        items = []
        for contest in discovered:
            # Derive a stable abif filename from the exact contest string
            suffix = slugify(contest)
            # Preserve legacy mayor filename if it matches
            if contest.lower() == "dem mayor":
                items.append(make_item(contest, "dem-mayor-citywide"))
            else:
                items.append(make_item(contest, suffix))
        return items

    # Fallback: enumerate contests explicitly so we don’t collapse districts.
    items: List[dict] = []

    # DEM citywide offices (RCV): Mayor, Public Advocate, Comptroller
    items += citywide_items_for_party("DEM", ["Mayor", "Public Advocate", "Comptroller"])

    # DEM borough presidents (5 separate contests)
    items += borough_president_items_for_party("DEM")

    # DEM council districts (51 separate contests)
    items += council_items_for_party("DEM", list(range(1, 52)))

    # GOP: include known RCV-eligible primaries commonly present
    # Comptroller is included in the existing spec; add council districts too
    items += citywide_items_for_party("REP", ["Comptroller"])  # add more if needed
    items += council_items_for_party("REP", list(range(1, 52)))

    return items


def main():
    parser = argparse.ArgumentParser(description="Generate NYC fetchspecs")
    parser.add_argument("--single-contest-string", help="Exact contest string to include (e.g., 'DEM Council Member District 08')")
    parser.add_argument("--party", choices=["DEM", "REP"], help="Party for structured single mode")
    parser.add_argument("--office", help="Office title for structured single mode (e.g., 'Council Member', 'Mayor', 'Comptroller', 'Public Advocate', '<Borough> Borough President')")
    parser.add_argument("--district", type=int, help="District number for Council Member contests")
    parser.add_argument("--borough", help="Borough for Borough President contests")
    parser.add_argument("--fanout", choices=["byfile", "precinct"], help="Write many raw ABIFs per ZIP (to a directory) instead of one file")
    parser.add_argument("--outfile", default="fetchspecs/nyc-elections-2025.fetchspec.json", help="Output fetchspec path")
    args = parser.parse_args()

    # Build web_urls either default (all) or single per args
    if args.single_contest_string or args.office or args.party:
        if args.single_contest_string:
            contest = args.single_contest_string
        else:
            parts = []
            if not args.party or not args.office:
                parser.error("Structured single requires --party and --office")
            parts.append(args.party)
            # Normalize some common office terms
            office = args.office.strip()
            if office.lower() == 'borough president' and args.borough:
                parts.append(args.borough)
                parts.append('Borough President')
            else:
                parts.append(office)
            if office.lower().startswith('council member') and args.district:
                parts.append(f"District {args.district:02d}")
            contest = " ".join(parts)

        suffix = slugify(contest)
        item = make_item(contest, suffix)
        # Ensure district field is present if Council Member + number
        m = re.search(r"district\s*(\d+)", contest, flags=re.IGNORECASE)
        if m:
            try:
                item['district'] = int(m.group(1))
            except Exception:
                pass
        web_urls = [item]
        # If fanout is requested, adapt to directory-based outputs
        if args.fanout:
            web_urls[0]['fanout'] = 'precinct' if args.fanout == 'precinct' else 'byfile'
            web_urls[0]['abifloc_dir'] = f"nyc2025-primary-{suffix}"
            # Keep abifloc too for compatibility if some tools expect it
            web_urls[0]['abifloc'] = f"{web_urls[0]['abifloc_dir']}.abif"
    else:
        web_urls = build_web_urls()

    fetchspec = {
        "download_subdir": DOWNLOAD_SUBDIR,
        "abifloc_subdir": ABIFLOC_SUBDIR,
        "srcfmt": "nycdems",
        "web_urls": web_urls,
    }

    outpath = args.outfile
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    with open(outpath, "w") as f:
        json.dump(fetchspec, f, indent=2)
    print(f"Wrote {outpath} with {len(web_urls)} contest entries")


if __name__ == "__main__":
    main()
