#!/usr/bin/env python3
from abif import *
import re

def _extract_option_names_from_tally_sheet(tally_sheet):
    lines = tally_sheet.splitlines()

    option_names = []
    regex = r"Option (\d+).*:\s+(.*)"
    for line in lines:
        if mg := re.search(regex, line):
            option_names.append(mg.group(2))

    return option_names

def _extract_vline_rankings_from_tally_sheet(tally_sheet):
    lines = tally_sheet.splitlines()

    retval = []
    regex = r"^V: ([-\d]+)\s+"
    for line in lines:
        if mg := re.search(regex, line):
            retval.extend([list(mg.group(1))])

    return retval

def convert_debtally_to_abif(debtallysheet):
    retval = ""
    option_names = _extract_option_names_from_tally_sheet(debtallysheet)
    short_option_names = []
    for o in option_names:
        o2 = re.sub('None of the above', 'NOTA', o)
        optname = re.sub(' ', '', o2)
        short_option_names.append(optname)
    for i, o in enumerate(option_names):
        retval += f'={short_option_names[i]}:[{o}]\n'
    retval += f'# ---------------\n'

    votes = _extract_vline_rankings_from_tally_sheet(debtallysheet)

    numopt = len(option_names)
    for v in votes:
        tiers = []
        for r in range(numopt):
            strrank = str(r + 1)
            crs = [i for i, ir in enumerate(v) if ir == strrank]
            if(crs):
                names = [short_option_names[i] for i in crs]
                tiers.append(f'{"=".join(names)}')
        tierstr = ">".join(tiers)
        retval += f'1:{tierstr}\n'
    return retval


def main():
    """Convert Debian tally sheet to crude .abif file"""
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument('input_file', help='Input Debian tally file')

    args = parser.parse_args()

    debtallysheet = ""
    with open(args.input_file) as f:
        debtallysheet += f.read()

    outstr = ""
    outstr += convert_debtally_to_abif(debtallysheet)
        
    print(outstr)


if __name__ == "__main__":
    main()
