#!/usr/bin/env python3
'''fetchmgr.py - vaguely managing data fetching

This tool doesn't really manage anything.  It just checks out
git repositories or wgets urls in associated .json files.
'''
import argparse
import json
import os
import requests
import subprocess
import sys


def checkout_repository(gitrepo_url, subdir):
    if os.path.exists(subdir):
        print(f"Directory '{subdir}' already exists.")
        return

    try:
        subprocess.run(["git", "clone", gitrepo_url, subdir])
        print(f"Repository cloned from {gitrepo_url} to {subdir}")
    except subprocess.CalledProcessError as e:
        print(f"Could not clone repository {gitrepo_url}")
        print("Error:", e)


def read_fetchspec(fetchspec_fn):
    if not os.path.exists(fetchspec_fn):
        print(f"Repo spec '{fetchspec_fn}' not found.")
        raise

    with open(fetchspec_fn, "r") as fetchspec_fh:
        fetchspec = json.load(fetchspec_fh)

    return fetchspec


def fetch_url_to_subdir(url=None, subdir=None, localpath=None):
    if not url or not subdir or not localpath:
        err = "err:"
        err += f"url: {url}\n"
        err += f"subdir: {subdir}\n"
        err += f"localpath: {localpath}\n"
        raise BaseException(err)
    sys.stderr.write(f"Fetching {url} to {subdir}\n")
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
    subdir = fetchspec['subdir']
    if not os.path.exists(subdir):
        os.makedirs(subdir)

    for urldict in fetchspec['web_urls']:
        localpath = os.path.join(subdir, urldict['local'])
        if os.path.exists(localpath):
            sys.stderr.write(f"Skipping existing {localpath}\n")
            continue
        response = fetch_url_to_subdir(url=urldict['url'],
                                       subdir=subdir,
                                       localpath=localpath)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="fetchmgr: Manage data fetching from repos or urls")
    parser.add_argument(
        "fetchspec",
        nargs="+",
        default=None,
        help="JSON file(s) describing fetch locations and mappings to local dirs",
    )

    args = parser.parse_args()
    for fetchspec_fn in args.fetchspec:
        fetchspec = read_fetchspec(fetchspec_fn)
        if 'gitrepo_url' in fetchspec.keys():
            checkout_repository(fetchspec['gitrepo_url'],
                                fetchspec['subdir'])
        elif 'web_urls' in fetchspec.keys():
            fetch_web_items(fetchspec)
        else:
            raise Exception(f"Need either gitrepo or web url(s)")


if __name__ == "__main__":
    main()
