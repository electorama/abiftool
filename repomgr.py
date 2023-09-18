#!/usr/bin/env python3
'''repomgr.py - vaguely manages subdirectory repositories

This tool doesn't really manage anything.  It just checks out
repositories in associated .json files.
'''
import argparse
import json
import os
import subprocess


def checkout_repository(repo_url, subdir):
    if os.path.exists(subdir):
        print(f"Directory '{subdir}' already exists.")
        return

    try:
        subprocess.run(["git", "clone", repo_url, subdir])
        print(f"Repository cloned from {repo_url} to {subdir}")
    except subprocess.CalledProcessError as e:
        print(f"Could not clone repository {repo_url}")
        print("Error:", e)


def read_repospec(repospec_fn):
    if not os.path.exists(repospec_fn):
        print(f"Repo spec '{repospec_fn}' not found.")
        raise

    with open(repospec_fn, "r") as repospec_fh:
        repospec = json.load(repospec_fh)

    repo_url = repospec.get("repo_url")
    subdir = repospec.get("subdir")

    if not repo_url:
        print(f"{repospec_fn}: Invalid repo_url: {repo_url}")
        raise

    if not subdir:
        print(f"{repospec_fn}: Invalid subdir: {subdir}")
        raise

    return (repo_url, subdir)


def main():
    parser = argparse.ArgumentParser(
        description="repomgr: Manage data repositories")
    parser.add_argument(
        "repospec",
        nargs="+",
        default=None,
        help="JSON file(s) describing repository to clone",
    )

    args = parser.parse_args()
    for repospec_fn in args.repospec:
        (repo_url, subdir) = read_repospec(repospec_fn)
        checkout_repository(repo_url, subdir)


if __name__ == "__main__":
    main()
