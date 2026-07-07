#!/usr/bin/env python3

import json
import os
import requests
import subprocess


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

    def _send_request(self, url, data):
        h = {
            "Authorization": "token " + self._token,
            "Content-Type": "application/json",
        }
        r = requests.post(url, headers=h, data=data)

        r.raise_for_status()

    def add_pr_comment(self, repo, pr_number, comment):
        j = json.dumps({"body": comment})
        url = f"{self._api_url}/repos/{repo}/issues/{pr_number}/comments"
        self._send_request(url, j)

    def add_commit_comment(self, repo, commit, comment):
        j = json.dumps({"message": comment})
        url = f"{self._api_url}/repos/{repo}/git/notes/{commit}"
        self._send_request(url, j)


def main():
    forgejo = Forgejo(os.environ["API_URL"], os.environ["AUTH_TOKEN"])
    argocd = Argocd(os.environ["ARGOCD_SERVER"], os.environ["ARGOCD_TOKEN"])
    print(os.environ["REPO_URL"])


if __name__ == "__main__":
    main()
