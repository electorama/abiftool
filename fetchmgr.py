#!/usr/bin/env python3
'''fetchmgr.py - vaguely managing data fetching

This tool doesn't really manage anything.  It just checks out
git repositories or wgets urls in associated .json files.
'''
import argparse
import json
import os
import subprocess


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

    gitrepo_url = fetchspec.get("gitrepo_url")
    subdir = fetchspec.get("subdir")

    if not gitrepo_url:
        print(f"{fetchspec_fn}: Invalid gitrepo_url: {gitrepo_url}")
        raise

    if not subdir:
        print(f"{fetchspec_fn}: Invalid subdir: {subdir}")
        raise

    return (gitrepo_url, subdir)


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
        (gitrepo_url, subdir) = read_fetchspec(fetchspec_fn)
        checkout_repository(gitrepo_url, subdir)


if __name__ == "__main__":
    main()
