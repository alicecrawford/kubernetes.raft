#!/usr/bin/env python3

import json
import os
import requests
import subprocess
import sys


from urllib.parse import urljoin


class Argocd:
    def __init__(self, server, token, argocd="argocd"):
        self._server = server
        self._token = token
        self._argocd = argocd

        self._auth = ["--server", server, "--auth-token", token]

    def get_apps(self):
        cmd = [self._argocd, "app", "list", "-o", "name"]
        p = subprocess.run(cmd + self._auth, capture_output=True)

        if p.returncode != 0:
            raise RuntimeError()


class Forgejo:
    def __init__(self, api_url, token):
        self._api_url = api_url
        self._token = token

    def add_pr_comment(self, repo, pr_number, comment):
        j = json.dumps({"body": comment})
        h = {
            "Authorization": "token " + self._token,
            "Content-Type": "application/json",
        }
        url = urljoin(self._api_url, "repos", repo, "issues", pr_number, "comments")
        r = requests.post(url, headers=h, data=j)

        print("Response:")
        for k in dir(r):
            v = getattr(k, r)
            print(f"{k}: {v}")

    def add_commit_comment(self, repo, commit, comment):
        j = json.dumps({"message": comment})
        h = {
            "Authorization": "token " + self._token,
            "Content-Type": "application/json",
        }
        url = urljoin(self._api_url, "repos", repo, "git/notes", commit)
        r = requests.post(url, headers=h, data=j)

        print("Response:")
        for k in dir(r):
            v = getattr(k, r)
            print(f"{k}: {v}")


def main():
    forgejo = Forgejo(sys.env["API_URL"], sys.env["AUTH_TOKEN"])
    argocd = Argocd(sys.env["ARGOCD_SERVER"], sys.env["AROGCD_TOKEN"])

    cmt = """
  this is a big comment
  with big comment things
  """
    if sys.env["EVENT_NAME"] == "pull_request":
        forgejo.add_pr_comment(sys.env["REPO"], sys.env["PR_NUMBER"], cmt + "it's a pr")
    else:
        forgejo.add_commit_comment(
            sys.env["REPO"], sys.env["COMMIT_SHA"], cmt + "it's a commit"
        )


if __name__ == "__main__":
    main()
