#!/usr/bin/env python
import argparse
import logging
import re
from os import getenv, path
from pprint import pprint
from sys import exit

import requests

log = logging.getLogger(__name__)

RE_LOG_HEADER = re.compile(r"## streamlink\s+(\d+\.\d+\.\d+(?:-\S+)?)\s+\(\d{4}-\d{2}-\d{2}\)\n+", flags=re.IGNORECASE)
RE_GITLOG = re.compile(r"(.*?)(```text\n.*?\n```)", re.DOTALL)
TEMPLATE = """
{changelog}

## Installation

See the detailed [installation instructions](https://streamlink.github.io/install.html) on Streamlink's website.

## Supporting Streamlink

If you think that this application is helpful, please consider supporting the maintainers by [donating via the Open collective](https://opencollective.com/streamlink). Not only becoming a backer, but also a sponsor for the (open source) project.


{gitlog}
"""


def github_api_call(method, repo, url, api_key, **kwargs):
    url = "https://api.github.com/repos/{0}/releases/{1}".format(repo, url)
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": repo,
        "Authorization": "token {0}".format(api_key)
    }
    return (requests.get if method != "PATCH" else requests.patch)(url, headers=headers, **kwargs)


def main(tag, repo, api_key, dry_run=False):
    try:
        cl_path = path.abspath(path.join(path.dirname(__file__), "../CHANGELOG.md"))
        log.debug("Opening changelog file: {}".format(cl_path))

        with open(cl_path, 'r') as fh:
            contents = fh.read()
            if not contents:
                raise ValueError("Missing changelog file")

        log.debug("Parsing change log file")
        changelogs = RE_LOG_HEADER.split(contents)[1:]
        changelogs = {v: changelogs[i + 1] for i, v in enumerate(changelogs) if i % 2 == 0}

        log.debug("Found {} change logs".format(len(changelogs)))

        if tag not in changelogs:
            raise KeyError("Missing changelog for current release")

        log.debug("Getting the current release ID for {}#{}".format(repo, tag))
        res = github_api_call("GET", repo, "tags/{0}".format(tag), api_key)
        if res.status_code >= 400:
            log.debug("Release ID fetch failed:")
            log.debug(res.text)
            raise ValueError("Unable to get release ID, check API KEY")

        data = res.json()
        if "id" not in data:
            raise KeyError("Missing id from Github API response")

        changelog, gitlog = RE_GITLOG.search(changelogs[tag]).groups()

        # Update release name and body
        payload = {
            "name": "Streamlink {0}".format(tag),
            "body": TEMPLATE.format(changelog=changelog.strip(), gitlog=gitlog.strip(), version=tag)
        }
        if not dry_run:
            github_api_call("PATCH", repo, data["id"], api_key, json=payload)
        else:
            print("[dry-run] Would have updated the GitHub release with the following:")
            pprint(payload)

        print("Github release {} has been successfully updated".format(tag))
        return 0

    except Exception:
        log.exception("Failed to update release info.")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update release information for GitHub Release")
    parser.add_argument("--debug", help="Enable debug logging", action="store_true")
    parser.add_argument("-n", "--dry-run", help="Do nothing, but say what would have happened (--api-key not required)", action="store_true")
    parser.add_argument("--tag", help="The TAG to update, by default uses env.TRAVIS_TAG", default=getenv("TRAVIS_TAG"))
    parser.add_argument("--repo", help="The REPO to update, by default uses env.TRAVIS_REPO_SLUG", default=getenv("TRAVIS_REPO_SLUG"))
    parser.add_argument("--api-key", help="The APIKEY to update, by default uses env.RELEASES_API_KEY", default=getenv("RELEASES_API_KEY"))

    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.debug else logging.INFO)

    if args.tag and args.repo and args.api_key:
        exit(main(args.tag, args.repo, args.api_key, args.dry_run))
    else:
        parser.error("--tag, --repo, and --api-key are all required options")
