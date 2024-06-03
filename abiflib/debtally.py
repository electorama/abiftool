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

    votelines = []
    regex = r"^V: ([-\d]+)\s+(\S+).*$"
    for line in lines:
        if mg := re.search(regex, line):
            voterid = mg.group(2)
            rankarray = [ voterid ]
            rankarray.extend(list(mg.group(1)))
            votelines.extend([rankarray])
        #else:
        #    voterid = None
        #abiflib_test_log(f"LINE: {line}")
        #abiflib_test_log(f"{votelines=}")
        #abiflib_test_log(f"{voterid=}")
    return votelines


def _trunc_sha_str(basestr, trunclen=4):
    checksum = sha1(basestr.encode('utf-8')).digest()[:trunclen]
    checksum_encoded = base64.b32encode(checksum).decode('utf-8')
    return checksum_encoded[:trunclen]


def _short_token(longstring, max_length=20, add_sha1=False):
    if len(longstring) <= max_length and \
       re.match(r'^[A-Za-z0-9]+$', longstring):
        return longstring

    wordlist = []
    for word in longstring.split():
        wordlist.append(re.sub('[^A-Za-z0-9]+', '', word))

    if add_sha1:
        base_string = ''.join(wordlist)[:max_length-4]
        retval = base_string + _trunc_sha_str(longstring)
    else:
        retval = ''.join(wordlist)[:max_length]
    return retval


def _get_short_option_names(option_names):
    retval = []
    tokset = set()
    for o in option_names:
        o2 = re.sub('(?i)none of the above', 'NOTA', o)
        optname = _short_token(o2)
        if optname in tokset:
            optname = _short_token(o2, add_sha1=True)
        tokset.add(optname)
        retval.append(optname)
    return retval


def convert_debtally_to_abif(debtallysheet, metadata={}):
    retval = ""
    option_names = _extract_option_names_from_tally_sheet(debtallysheet)

    for k in metadata.keys():
        retval += '{' + f'"{k}": "{metadata[k]}"' + '}\n'
    short_option_names = _get_short_option_names(option_names)

    for i, o in enumerate(option_names):
        retval += f'={short_option_names[i]}:[{o}]\n'
    retval += f'# ---------------\n'

    votelist = _extract_vline_rankings_from_tally_sheet(debtallysheet)

    numopt = len(option_names)
    for vote in votelist:
        tiers = []
        voterid = vote[0]
        pref = vote[1:]
        for r in range(numopt):
            strrank = str(r + 1)
            crs = [i for i, ir in enumerate(pref) if ir == strrank]
            if (crs):
                names = [short_option_names[i] for i in crs]
                tiers.append(f'{"=".join(names)}')
        tierstr = ">".join(tiers)
        retval += f'1:{tierstr}'
        retval += f"  ##VID:{voterid}\n"
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
