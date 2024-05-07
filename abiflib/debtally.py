#!/usr/bin/env python3
from abiflib import *
import base64
from hashlib import sha1
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


def _short_token(longstring, max_length=20, add_sha1=True):
    if len(longstring) <= max_length and re.match(r'^[A-Za-z0-9]+$', longstring):
        return longstring

    wordlist = []
    for word in longstring.split():
        wordlist.append(re.sub('[^A-Za-z0-9]+', '', word))
    word_lengths = [len(word) for word in wordlist]
    words_sorted = sorted(wordlist,
                          key=lambda word: (len(word), word), reverse=True)
    base_string = ''.join(words_sorted)[:max_length-4]

    checksum = sha1(longstring.encode('utf-8')).digest()[:4]
    checksum_encoded = base64.b32encode(checksum).decode('utf-8')
    retval = base_string + checksum_encoded[:4]
    return retval


def convert_debtally_to_abif(debtallysheet, metadata={}):
    retval = ""
    option_names = _extract_option_names_from_tally_sheet(debtallysheet)
    short_option_names = []

    devobj = LogfileSingleton()
    devobj.log(f"{metadata=}\n")

    for k in metadata.keys():
        retval += '{' + f'"{k}": "{metadata[k]}"' + '}\n'
    for o in option_names:
        o2 = re.sub('(?i)none of the above', 'NOTA', o)
        optname = _short_token(o2)
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
