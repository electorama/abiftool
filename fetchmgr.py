#!/usr/bin/env python3
'''fetchmgr.py - managing data fetching and conversion to ABIF

This tool manages election-data downloads from many different sources
and optionally converts the data to ABIF.
'''
# Copyright (C) 2023, 2024, 2025 Rob Lanphier
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

import abiflib
import argparse
import json
import os
import requests
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from pprint import pprint

def update_repository(gitrepo_url, subdir):
    if not os.path.exists(subdir):
        print(f"Directory '{subdir}' isn't there.")
        return

    startdir = os.getcwd()
    os.chdir(subdir)
    try:
        subprocess.run(["git", "pull"])
        print(f"Updating repository {subdir} from {gitrepo_url} (git pull)")
    except subprocess.CalledProcessError as e:
        print(f"Could not update repository {gitrepo_url}")
        print("Error:", e)
    os.chdir(startdir)


def checkout_repository(gitrepo_url, subdir):
    if os.path.exists(subdir):
        print(f"Directory '{subdir}' exists.")
        return update_repository(gitrepo_url, subdir)

    try:
        subprocess.run(["git", "clone", gitrepo_url, subdir])
        print(f"Repository cloned from {gitrepo_url} to {subdir}")
    except subprocess.CalledProcessError as e:
        print(f"Could not clone repository {gitrepo_url}")
        print("Error:", e)


def fetch_url_to_subdir(url=None, subdir=None, localpath=None, metaurl=None, desc=None):
    if not url or not subdir or not localpath:
        err = "err:"
        err += f"url: {url}\n"
        err += f"subdir: {subdir}\n"
        err += f"localpath: {localpath}\n"
        raise BaseException(err)
    sys.stderr.write(f"Fetching {url} to {subdir}\n")
    sys.stderr.write(f"  {desc}\n")
    sys.stderr.write(f"  See the following URL to learn more about this election:\n")
    sys.stderr.write(f"  {metaurl}\n")
    response = requests.get(url)

    if response.status_code == 200:
        d, f = os.path.split(localpath)

        if not os.path.exists(d):
            os.makedirs(d)

        if os.path.exists(d):
            with open(localpath, "wb") as f:
                f.write(response.content)
        else:
            print(f"d {d} f {f}")
            raise Exception(f"Bad URL: {response.status_code}")

    return response


def fetch_web_items(fetchspec):
    subdir = fetchspec['download_subdir']
    if not os.path.exists(subdir):
        os.makedirs(subdir)

    response = False
    localpaths = []
    for urldict in fetchspec['web_urls']:
        if 'localcopies' in urldict.keys():
            for i, l in enumerate(urldict['localcopies']):
                localpaths.append("REPLACETHIS")
                localpaths[i] = os.path.join(subdir, urldict['localcopies'][i])

        else:
            localpath = os.path.join(subdir, urldict['localcopy'])

        if 'urls' in urldict.keys():
            for i, suburl in enumerate(urldict['urls']):
                #print(f"{i=} {suburl=}")
                if not os.path.exists(localpaths[i]):
                    response = fetch_url_to_subdir(url=suburl,
                                                   subdir=subdir,
                                                   localpath=localpaths[i],
                                                   metaurl=urldict['metaurls'][0],
                                                   desc=urldict['desc'])
                else:
                    sys.stderr.write(f"Skipping download of existing {localpaths[i]}\n")
        else:
            if not os.path.exists(localpath):
                response = fetch_url_to_subdir(url=urldict['url'],
                                               subdir=subdir,
                                               localpath=localpath,
                                               metaurl=urldict['metaurls'][0],
                                               desc=urldict['desc'])
            else:
                sys.stderr.write(f"Skipping download of existing {localpath}\n")
    return response


def convert_files_to_abif(fromfmt, input_files, output_file, fetchdesc=None):
    if fetchdesc:
        metadata = {"description": fetchdesc}
    else:
        metadata = {}

    inputblobs = []
    for i, f in enumerate(input_files):
        try:
            inputblobs.append(Path(f).read_text())
        except FileNotFoundError:
            print(f"Error: Input file '{f}' not found.")
            sys.exit(1)

    abiftext = abiflib.convert_text_to_abif(fromfmt, inputblobs,
                                            metadata=metadata)
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    Path(output_file).write_text(abiftext)
    return True


def convert_nameq_tarball_to_abif_files(tarball_fn, archive_subfiles, abifsubdir):
    """Extract nameq text files from tarball and write to subfiles
    """
    sys.stderr.write(f"Converting {tarball_fn}....\n")
    for file_to_fetch in archive_subfiles:
        with tarfile.open(tarball_fn, 'r') as tarball:
            member = tarball.getmember(file_to_fetch['archive_subfile'])
            file_obj = tarball.extractfile(member)
            text_content = file_obj.read().decode('utf-8', errors='replace')
        abifmodel = abiflib.convert_nameq_to_jabmod(text_content)
        consmodel = abiflib.consolidate_jabmod_voteline_objects(abifmodel)
        abifstr = abiflib.convert_jabmod_to_abif(consmodel)


        abifpath = Path(file_to_fetch['abifloc'])
        abifpath.parent.mkdir(parents=True, exist_ok=True)
        abifpath.write_text(abifstr)
        sys.stderr.write(".")
        sys.stderr.flush()
    sys.stderr.write("\n")
    successful_count = len(archive_subfiles)
    return successful_count


def process_extfilelist(dlsubdir=None, abifsubdir=None, extfilelist=None, srcfmt=None,
                        archive_subfiles=None):
    if not os.path.exists(abifsubdir):
        os.makedirs(abifsubdir)
    for extfile in extfilelist:
        if 'localcopies' in extfile.keys():
            infiles = [os.path.join(dlsubdir, x) for x in extfile['localcopies']]
        else:
            infiles = [os.path.join(dlsubdir, extfile['localcopy'])]
        srcfmt = extfile.get('srcfmt') or srcfmt
        fetchdesc = extfile.get('desc') or None
        if srcfmt == 'abif':
            outfile = os.path.join(abifsubdir, extfile['abifloc'])
            sys.stderr.write(f"Linking from {outfile} to {infiles[0]}\n")
            symlinkval = os.path.relpath(infiles[0], start=abifsubdir)
            try:
                os.symlink(src=symlinkval, dst=outfile)
            except FileExistsError:
                os.remove(outfile)
                os.symlink(src=symlinkval, dst=outfile)
        elif srcfmt == 'debtally' or srcfmt == 'preflib' or srcfmt == 'sftxt':
            outfile = os.path.join(abifsubdir, extfile['abifloc'])
            infilestr = " ".join(infiles)
            sys.stderr.write(f"Converting {infilestr} ({srcfmt}) to {outfile}\n")
            convert_files_to_abif(fromfmt=srcfmt,
                                  input_files=infiles,
                                  output_file=outfile,
                                  fetchdesc=fetchdesc)
        elif srcfmt == 'nameq_archive':
            tarball_fn = os.path.join(dlsubdir, extfile['localcopy'])
            convert_nameq_tarball_to_abif_files(tarball_fn=tarball_fn,
                                                archive_subfiles=archive_subfiles,
                                                abifsubdir=abifsubdir)
        else:
            raise Exception(f"Unknown srcfmt: {srcfmt}")
    return True


def process_fetchspec(fn):
    if not os.path.exists(fn):
        print(f"fetchspec '{fn}' not found.")
        raise
    with open(fn, "r") as fh:
        fetchspec = json.load(fh)
    if 'gitrepo_url' in fetchspec.keys():
        checkout_repository(fetchspec['gitrepo_url'],
                            fetchspec['download_subdir'])
    elif 'web_urls' in fetchspec.keys():
        fetch_web_items(fetchspec)
    else:
        raise Exception(f"Invalid fetchspec: {fetchspec.keys()=}")
    sys.stderr.write(f"Processing {fn}....\n")

    dlsubdir = fetchspec['download_subdir']
    abifsubdir = fetchspec.get('abifloc_subdir')
    extfilelist = fetchspec.get('web_urls') or fetchspec.get('extfiles')
    srcfmt = fetchspec.get('srcfmt')
    if abifsubdir and extfilelist:
        process_extfilelist(dlsubdir=dlsubdir,
                            abifsubdir=abifsubdir,
                            extfilelist=extfilelist,
                            srcfmt=srcfmt,
                            archive_subfiles=fetchspec.get('archive_subfiles'))
    return True


def main():
    parser = argparse.ArgumentParser(
        description="fetchmgr: managing data fetching and conversion to ABIF")
    parser.add_argument(
        "--abif", "-a",
        default=False,
        help="Generate ABIF files from downloaded election data")
    parser.add_argument(
        "fetchspec",
        nargs="*",
        default=None,
        help="JSON file(s) describing fetch locations and mappings to local dirs",
    )

    args = parser.parse_args()
    if len(args.fetchspec) < 1:
        print("Please provide at least one fetchspec (see fetchspecs/*)")
        sys.exit(1)
    for fetchspec_fn in args.fetchspec:
        process_fetchspec(fetchspec_fn)
    sys.stderr.write(f"Done\n")

if __name__ == "__main__":
    main()
