#!/usr/bin/env python

from sys import exit, stderr
from os import getenv, path
from re import split, IGNORECASE
from requests import get, patch


RE_LOG_HEADER = r"streamlink\s+(\d+\.\d+\.\d+(?:-\S+)?)\s+\(\d{4}-\d{2}-\d{2}\)\n(?:-|=){3,}\n+"


def checkEnvVar(v):
    if not getenv(v):
        raise AssertionError("Missing env var {0}\n".format(v))


def githubAPI(method, url, **kwargs):
    url = "https://api.github.com/repos/{0}/releases/{1}".format(getenv("TRAVIS_REPO_SLUG"), url)
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": getenv("TRAVIS_REPO_SLUG"),
        "Authorization": "token {0}".format(getenv("RELEASES_API_KEY"))
    }
    return (get if method != "PATCH" else patch)(url, headers=headers, **kwargs)


try:
    # Make sure that all required env vars are set
    [checkEnvVar(v) for v in ["TRAVIS_REPO_SLUG", "TRAVIS_TAG", "RELEASES_API_KEY"]]

    # Parse changelog file
    file = path.abspath("{0}/{1}".format(path.dirname(__file__), "../CHANGELOG.rst"))
    contents = open(file).read()
    if not contents:
        raise AssertionError("Missing changelog file")

    changelogs = split(RE_LOG_HEADER, contents, flags=IGNORECASE)[1:]
    changelogs = {v: changelogs[i + 1] for i, v in enumerate(changelogs) if i % 2 == 0}

    if not getenv("TRAVIS_TAG") in changelogs:
        raise AssertionError("Missing changelog for current release")

    # Get release ID
    res = githubAPI("GET", "tags/{0}".format(getenv("TRAVIS_TAG")))
    data = res.json()
    if "id" not in data:
        raise AssertionError("Missing id from Github API response")

    # Update release name and body
    payload = {
        "name": "Streamlink {0}".format(getenv("TRAVIS_TAG")),
        "body": changelogs[getenv("TRAVIS_TAG")]
    }
    githubAPI("PATCH", data["id"], json=payload)

    print("Github release {0} has been successfully updated".format(getenv("TRAVIS_TAG")))
    exit(0)

except Exception as e:
    stderr.write("{0}\n".format(str(e)))
    exit(1)
