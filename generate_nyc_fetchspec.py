import json
import re

with open('all_columns.txt', 'r') as f:
    content = f.read()

contests = set()
for line in content.splitlines():
    if "Choice" in line:
        parts = line.split(" Choice ")
        contest_name = parts[0]
        contests.add(contest_name)

web_urls = []
for contest in sorted(list(contests)):
    slug = contest.lower().replace(' ', '-').replace(':', '')
    if "mayor" in slug:
        abifloc = f"nyc2025-primary-dem-mayor-citywide.abif"
    else:
        abifloc = f"nyc2025-primary-{slug}.abif"

    web_urls.append({
        "url": "https://www.vote.nyc/sites/default/files/pdf/election_results/2025/20250624Primary%20Election/rcv/2025_Primary_CVR_2025-07-17.zip",
        "localcopy": "2025_Primary_CVR_2025-07-17.zip",
        "metaurls": [
            "https://vote.nyc/page/election-results-summary"
        ],
        "desc": f"2025 NYC Primary Election - {contest}",
        "abifloc": abifloc,
        "contest_string": contest
    })

fetchspec = {
  "download_subdir": "downloads/newyork",
  "abifloc_subdir": "localabif/newyork",
  "srcfmt": "nycdems",
  "web_urls": web_urls
}

with open('fetchspecs/nyc-elections-2025-all.fetchspec.json', 'w') as f:
    json.dump(fetchspec, f, indent=2)