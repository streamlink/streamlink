#!/usr/bin/env python
import argparse
import logging
from os import getenv, path
from pprint import pformat
import re
from sys import exit

import requests

log = logging.getLogger(__name__)

root = path.normpath(path.join(path.dirname(__file__), ".."))

TEMPLATE = path.join(root, ".github", "release_template.md")
CHANGELOG = path.join(root, "CHANGELOG.md")

RE_LOG_HEADER = re.compile(r"## streamlink\s+(\d+\.\d+\.\d+(?:-\S+)?)\s+\(\d{4}-\d{2}-\d{2}\)\n+", re.IGNORECASE)
RE_GITLOG = re.compile(r"(.*?)(```text\n.*?\n```)", re.DOTALL)
RE_GIT_REF_TAG = re.compile(r"^refs/tags/(.+)$")


def get_default_repo_from_env():
    return getenv("GITHUB_REPOSITORY")


def get_default_tag_from_env():
    return (lambda match: match.group(1) if match else None)(re.search(RE_GIT_REF_TAG, getenv("GITHUB_REF", "")))


def get_default_dist_dir_from_env():
    return getenv("STREAMLINK_DIST_DIR")


def main(repo, tag, assets, api_key, dry_run=False):
    primary_headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": repo,
        "Authorization": "token {}".format(api_key)
    }

    def github_api_call(host="api.github.com", method="GET", endpoint="/", headers=None, raise_failure=True, **kwargs):
        req = requests.post if method == "POST" else requests.patch if method == "PATCH" else requests.get
        url = "https://{host}{endpoint}".format(host=host, endpoint=endpoint)

        response = req(url, headers={**(headers or {}), **primary_headers}, **kwargs)
        if raise_failure and response.status_code >= 400:
            log.debug("Github API request failed:")
            log.debug(response.text)
            raise Exception("Github API request {} '{}' returned {}", method, endpoint, response.status_code)

        return response

    def get_response_json_key(response, key):
        data = response.json()
        if key not in data:
            raise KeyError("Missing key '{}' in Github API response".format(key))

        return data[key]

    def get_id(response):
        return get_response_json_key(response, "id")

    def get_release_id():
        log.debug("Checking for existing release in {} tagged by {}".format(repo, tag))
        response = github_api_call(
            endpoint="/repos/{repo}/releases/tags/{tag}".format(repo=repo, tag=tag),
            raise_failure=False
        )

        return None if response.status_code >= 400 else get_id(response)

    def get_changelog(changelog_file):
        log.debug("Opening changelog file: {}".format(changelog_file))
        with open(changelog_file, "r") as fh:
            contents = fh.read()
            if not contents:
                raise ValueError("Missing changelog file")

        log.debug("Parsing changelog file")
        changelogs = RE_LOG_HEADER.split(contents)[1:]
        changelogs = {v: changelogs[i + 1] for i, v in enumerate(changelogs) if i % 2 == 0}

        log.debug("Found {} changelogs".format(len(changelogs)))
        if tag not in changelogs:
            raise KeyError("Missing changelog for current release")

        return RE_GITLOG.search(changelogs[tag]).groups()

    def get_release_template(template_file):
        log.debug("Opening release template file: {}".format(template_file))
        with open(template_file, "r") as fh:
            contents = fh.read()
            if not contents:
                raise ValueError("Missing release template file")

        return contents

    def get_file_handles():
        handles = {}
        for asset in assets:
            basename = path.basename(asset)
            if not path.isfile(asset):
                continue
            handles[basename] = open(asset, "rb")

        return handles

    try:
        if not dry_run:
            res = github_api_call(endpoint="/user", raise_failure=False)
            if res.status_code >= 400:
                raise ValueError("Invalid or missing Github API key")

        template = get_release_template(TEMPLATE)
        changelog, gitlog = get_changelog(CHANGELOG)
        filehandles = get_file_handles()

        payload = {
            "tag_name": tag,
            "name": "Streamlink {}".format(tag),
            "body": template.format(changelog=changelog.strip(), gitlog=gitlog.strip(), version=tag)
        }
        release_id = get_release_id()

        if not release_id:
            if dry_run:
                log.info("dry-run: Would have created GitHub release {}#{} with:\n{}".format(repo, tag, pformat(payload)))
            else:
                log.info("Creating new Github release {}#{}".format(repo, tag))
                res = github_api_call(
                    method="POST",
                    endpoint="/repos/{repo}/releases".format(repo=repo),
                    json=payload
                )
                log.info("Successfully created new Github release {}#{}".format(repo, tag))
                release_id = get_id(res)
        else:
            if dry_run:
                log.info("dry-run: Would have updated GitHub release {}#{} with:\n{}".format(repo, tag, pformat(payload)))
            else:
                log.info("Updating existing Github release {}#{}".format(repo, tag))
                github_api_call(
                    method="PATCH",
                    endpoint="/repos/{repo}/releases/{release_id}".format(repo=repo, release_id=release_id),
                    json=payload
                )
                log.info("Successfully updated existing Github release {}#{}".format(repo, tag))

        for filename, filehandle in filehandles.items():
            if dry_run:
                log.info("dry-run: Would have uploaded '{}' to Github release {}#{}".format(filename, repo, tag))
            else:
                log.info("Uploading '{}' to Github release {}#{}".format(filename, repo, tag))
                github_api_call(
                    host="uploads.github.com",
                    method="POST",
                    endpoint="/repos/{repo}/releases/{release_id}/assets".format(repo=repo, release_id=release_id),
                    headers={"Content-Type": "application/octet-stream"},
                    params={"name": filename},
                    data=filehandle
                )
                log.info("Successfully uploaded '{}' to Github release {}#{}".format(filename, repo, tag))

        log.info("Done")
        return 0

    except Exception:
        log.exception("Failed to create or update release info. Exiting.")
        return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create or update a GitHub Release and upload release assets")
    parser.add_argument(
        "--debug",
        help="Enable debug logging",
        action="store_true"
    )
    parser.add_argument(
        "-n", "--dry-run",
        help="Do nothing, but say what would have happened (--api-key not required)",
        action="store_true"
    )
    parser.add_argument(
        "--api-key",
        help="The Github API key. Default: env.RELEASES_API_KEY",
        default=getenv("RELEASES_API_KEY")
    )
    parser.add_argument(
        "--repo",
        help="The REPO. If unset, tries to read from env vars set by the CI service instance",
        default=get_default_repo_from_env()
    )
    parser.add_argument(
        "--tag",
        help="The TAG. If unset, tries to read from env vars set by the CI service instance",
        default=get_default_tag_from_env()
    )
    parser.add_argument(
        "assets",
        nargs="*",
        help="Upload new assets from the given paths"
    )

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="[%(levelname)s] %(message)s"
    )

    if args.repo and args.tag and (args.api_key or args.dry_run):
        exit(main(args.repo, args.tag, args.assets, args.api_key, args.dry_run))
    else:
        parser.error("--tag, --repo, and --api-key are all required options")
