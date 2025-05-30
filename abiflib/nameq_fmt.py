#!/usr/bin/env python3
''' nameq.py - funcitons for working with Brian Olson's '.nameq' format '''

# Copyright (c) 2024 Rob Lanphier
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

from abiflib.core import ABIF_VERSION
from urllib.parse import parse_qs, quote_plus


def convert_nameq_to_jabmod(inputstr):
    """Converts Brian Olson's .nameq format to jabmod (JSON ABIF model)."""

    abifmodel = {}
    abifmodel["metadata"] = {}
    abifmodel["metadata"]["version"] = ABIF_VERSION
    abifmodel["candidates"] = {}
    nameq_votelines = []

    ballotcount = 0
    for line in inputstr.splitlines():
        ballotcount += 1
        qs = line.strip()
        vl = {
            "qty": 1,
            "prefs": {},
            "nameq": qs,
        }
        qp = parse_qs(qs)
        for key, value in qp.items():
            if len(key) < 1:
                key = "null"
            vl["prefs"][key] = {}
            vl["prefs"][key]["rank"] = int(value[0])
            abifmodel["candidates"][key] = key 
        nameq_votelines.append(vl)

    abifmodel["votelines"] = nameq_votelines
    abifmodel["metadata"]["ballotcount"] = ballotcount

    return abifmodel


def convert_jabmod_to_nameq(abifmodel):
    """Converts jabmod (JSON ABIF model) to Brian Olson's .nameq format."""

    retval = ""
    for vl in abifmodel['votelines']:
        for i in range(vl['qty']):
            nqarray = []
            for prefkey, pv in vl['prefs'].items():
                pk = quote_plus(prefkey)
                nqarray.append(f"{pk}={pv['rank']}")
            retval += "&".join(nqarray)
            retval += "\n"
    return retval
