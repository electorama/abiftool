#!/usr/bin/env python3
from abiflib import *
import re

'''
# ALTERNATIVE NAME 1: Bob Kiss
# ALTERNATIVE NAME 2: Andy Montroll
# ALTERNATIVE NAME 3: James Simpson
# ALTERNATIVE NAME 4: Dan Smith
# ALTERNATIVE NAME 5: Kurt Wright
# ALTERNATIVE NAME 6: Write-In
840: 5,{1,2,3,4,6}
355: 1,2,{3,4,5,6}
326: 1,{2,3,4,5,6}
'''

def _extract_alt_names_from_preflib_str(preflib_str):
    lines = preflib_str.splitlines()

    alt_names = []
    regex = r"^# ALTERNATIVE NAME (\d+): (.*)$"
    for line in lines:
        if match := re.search(regex, line):
            alt_names.append(match.group(2))

    return alt_names

def _extract_rankings_from_preflib_str(preflib_str, shortnames=None):
    # 840: 5,{1,2,3,4,6}
    # [1'BobKiss', 2'AndyMontroll', 3'JamesSimpson',
    #  4'DanSmith', 5'KurtWright', 6'Write-In']
    # 840: KurtWright>BobKiss=AndyMontrol=JamesSimpson=DanSmith=Write-In

    lines = preflib_str.splitlines()

    retval = ''
    regex = r"^(\d+): (.*)"

    numopt = len(shortnames)
    for line in lines:
        if match := re.search(regex, line):
            qty = match.group(1)
            rankpart = match.group(2)
            i=0
            tierarray = []
            for part in re.split(r'({[^}]*}|,)', rankpart):
                if not part or part == ',' or part.isspace():
                    continue
                candnums = []
                tierstr = ""
                for j, subpart in enumerate(re.finditer(r'(\d+)', part)):
                    candnums.append(subpart.group(1))
                tiertoks = [shortnames[int(n) - 1] for n in candnums]
                tierstr += "=".join(tiertoks)
                tierarray.append(tierstr)

                i += 1

            rankstr = ">".join(tierarray)
            retval += f'{qty}:{rankstr}\n'

    return retval

def convert_preflib_str_to_abif(preflib_str):
    retval = ""
    alt_names = _extract_alt_names_from_preflib_str(preflib_str)
    shortnames = []
    for o in alt_names:
        optname = re.sub(' ', '', o)
        shortnames.append(optname)
    for i, o in enumerate(alt_names):
        retval += f'={shortnames[i]}:[{o}]\n'
    retval += f'# ---------------\n'

    retval += str(
        _extract_rankings_from_preflib_str(preflib_str,
                                           shortnames=shortnames)
                  )
 
    return retval


def main():
    """Convert PrefLib file to .abif file"""
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument('input_file', help='Input PrefLib tally file')

    args = parser.parse_args()

    preflib_str = ""
    with open(args.input_file) as f:
        preflib_str += f.read()

    outstr = ""
    outstr += convert_preflib_str_to_abif(preflib_str)

    print(outstr)


if __name__ == "__main__":
    main()
