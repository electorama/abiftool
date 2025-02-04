#!/usr/bin/env python3
'''configmgr.py - tool for managing abiftool/awt config files

This utility may eventually be a tool for converting between various
awt and abiftool config formats.  Right now, it's a kludge while
working on importing Brian Olson's archive of elections.

'''
import argparse
import json
import os
import re
import yaml


def _fix_tag(oldtag, title=""):
    '''Either acts a passthrough or a kludge to split tags

    This function was created on 2025-02-03 as part of the import
    process of Brian Olson's election archives.
    '''
    newtags = set()
    if re.search(r"mayor", oldtag, flags=re.IGNORECASE):
        newtags.update(["mayor"])
    if re.search(r"^Alaska", oldtag) and re.search("^Alaska-U.S.", title):
        newtags.update(["AK", "federal"])
    elif re.search(r"^Alaska", oldtag):
        newtags.update(["AK", "local"])
    elif re.search(r"^AlamedaCounty", oldtag):
        newtags.update(["CA", "AlamedaCounty_CA"])
    elif re.search(r"^SanFrancisco", oldtag) or re.search(r"^san_francisco", oldtag):
        newtags.update(["CA", "SanFrancisco_CA", "SF"])
    elif re.search(r"^san_leandro", oldtag):
        newtags.update(["CA", "SanLeandro_CA"])
    elif re.search(r"^oakland", oldtag):
        newtags.update(["CA", "Oakland_CA"])
    elif re.search(r"^Maine", oldtag):
        newtags.update(["ME"])
    elif re.search(r"^ME_Primary", oldtag):
        newtags.update(["ME", "primary_election"])
    elif re.search(r"^Portland_ME", oldtag):
        newtags.update(["ME", "Portland_ME"])
    elif re.search(r"^Minneapolis", oldtag):
        newtags.update(["MN", "Minneapolis_MN"])
    elif re.search(r"^NYC", oldtag):
        newtags.update(["NY", "NYC_NY"])
    elif re.search(r"^Burlington_VT", oldtag):
        newtags.update(["VT", "Burlington_VT"])
    elif re.search(r"^Pierce_WA", oldtag):
        newtags.update(["WA", "PierceCounty_WA"])
    else:
        # oldtag = /^\d+/:
        newtags.update(oldtag)
    return newtags


def make_nameq_based_file_list(fetchspec):
    retval = []
    for abiffile in fetchspec['archive_subfiles']:
        entry = {}
        entry['filename'] = abiffile['abifloc']
        if match := re.search(r'([^/]+)\.abif$', entry['filename']):
            entry['id'] = match.group(1)
        else:
            entry['id'] = None
        entry['title'] = abiffile.get('title')
        if not entry['title']:
            entry['title'] = entry['id']
        if abiffile.get('tags'):
            fixedtags = set()
            for oldtag in set(abiffile['tags']):
                for newtag in _fix_tag(oldtag):
                    fixedtags.add(newtag)
            entry['tags'] = ', '.join(abiffile.get('tags'))
        else:
            entry['tags'] = None
        entry['desc'] = abiffile.get('desc')
        retval.append(entry)
    return retval


def convert_fetchspec_to_newdict(fn):
    retval = {}
    if not os.path.exists(fn):
        print(f"fetchspec '{fn}' not found.")
        raise
    with open(fn, "r") as fh:
        fetchspec = json.load(fh)
    retval['srcfmt'] = fetchspec.get('srcfmt')
    if retval['srcfmt'] == 'nameq_archive':
        retval = make_nameq_based_file_list(fetchspec)
    return retval


def main():
    parser = argparse.ArgumentParser(
        description="configmgr.py - tool for managing abiftool/awt config files")
    parser.add_argument("inputfile", default=None, help="Input file")

    args = parser.parse_args()
    if not args.inputfile:
        print("Please provide at least one input file")
        sys.exit(1)
    outstruct = convert_fetchspec_to_newdict(args.inputfile)
    print(yaml.dump(outstruct, sort_keys=False))


if __name__ == "__main__":
    main()
