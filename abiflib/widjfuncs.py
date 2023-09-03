#!/usr/bin/env python3
# widjfuncs.py - funcitons for working with Electowidget (.widj) files
#
# Copyright (C) 2023 Rob Lanphier
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

PRUNED_WIDJ_FIELDS = [
    "display_parameters", "display_results",
    "display_ballots", "allow_voting",
    "ballot_type", "max_rating", "min_rating",
    "count_subpage_ballots", "count_inline_ballots",
    "election_methods", "inline_ballot_type",
    "candidates", "inline_ballots"
]


def convert_widj_to_jabmod(widgetjson):
    """Converts electowidget JSON (widj) to the JSON ABIF model (jabmod)."""

    abifmodel = {}
    abifmodel["metadata"] = {}
    abifmodel["metadata"]["version"] = ABIF_VERSION
    abifmodel["candidates"] = {}

    # Fill in abifmodel["metadata"]
    for field in widgetjson:
        if field not in PRUNED_WIDJ_FIELDS:
            abifmodel["metadata"][field] = widgetjson[field]

    # Fill in abifmodel["candidates"]
    for candtoken, candidate_info in widgetjson["candidates"].items():
        abifmodel["candidates"][candtoken] = candidate_info["display_name"]

    # Fill in abifmodel["votelines"]
    abifmodel["votelines"] = _map_widj_ballots(widgetjson)

    return abifmodel


def _map_widj_ballots(widgetjson):
    """Maps widj ballots to abif voteline objects"""

    abif_votelines = []
    for ballot in widgetjson["inline_ballots"]:
        abif_ballot = {
            "qty": ballot["qty"],
            "prefs": {},
        }
        for candtoken, rating in ballot["vote"].items():
            abif_ballot["prefs"][candtoken] = {'rating': rating}
        abif_votelines.append(abif_ballot)

    return abif_votelines
