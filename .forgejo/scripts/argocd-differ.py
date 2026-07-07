#!/usr/bin/env python3

import json
import os
import requests
import subprocess


class Argocd:
    def __init__(self, server, token, repo_url, ref_name, argocd="argocd"):
        self._server = server
        self._token = token
        self._argocd = argocd
        self._repo_url = repo_url
        self._ref_name = ref_name

        self._auth = ["--server", server, "--auth-token", token]

    def get_apps(self):
        cmd = [self._argocd, "app", "list", "-o", "json"]
        p = subprocess.run(cmd + self._auth, capture_output=True)

        if p.returncode != 0:
            raise RuntimeError(
                "argocd list exited with return code %d: %s - %s",
                p.returncode,
                p.stderr.decode("utf-8"),
                p.stdout.decode("utf-8"),
            )

        apps = json.loads(p.stdout.decode("utf-8"))
        return apps

    def get_diff(self, app):
        name = app["metadata"]["name"]
        ret = {
            "name": name,
            "namespace": app["spec"]["destination"]["namespace"],
            "project": app["spec"]["project"],
            "diff": "",
            "stderr": "",
            "return": -1,
        }

        revision_args = []
        if "source" in app["spec"]:
            if app["spec"]["source"]["repoURL"] == self._repo_url:
                revision_args += ["--revision", self._ref_name]
        elif "sources" in app["spec"]:
            for i, src in enumerate(app["spec"]["sources"]):
                if src["repoURL"] == self._repo_url:
                    pos = i + 1
                    revision_args += [
                        "--source-positions",
                        f"{pos}",
                        "--revisions",
                        self._ref_name,
                    ]

        cmd = [self._argocd, "app", "diff", name, "--server-side-generate"]
        cmd += self._auth
        cmd += revision_args
        p = subprocess.run(cmd, capture_output=True)
        ret["return"] = p.returncode
        ret["diff"] = p.stdout.decode("utf-8")
        ret["stderr"] = p.stderr.decode("utf-8")

        if p.returncode not in (0, 1):
            raise RuntimeError(
                "argocd diff for %s exited with return code %d: %s - %s",
                name,
                p.returncode,
                p.stderr.decode("utf-8"),
                p.stdout.decode("utf-8"),
            )
        return ret

    def refresh_app(self, app):
        name = app["metadata"]["name"]

        cmd = [self._argocd, "app", "get", name, "--refresh"] + self._auth
        p = subprocess.run(cmd, capture_output=True)

        if p.returncode != 0:
            raise RuntimeError(
                "argocd sync for %s exited with return code %d: %s - %s",
                name,
                p.returncode,
                p.stderr.decode("utf-8"),
                p.stdout.decode("utf-8"),
            )

    def dry_run(self, app):
        name = app["metadata"]["name"]

        ret = {
            "name": name,
            "namespace": app["spec"]["destination"]["namespace"],
            "project": app["spec"]["project"],
            "stdout": "",
            "stderr": "",
            "return": -1,
        }

        cmd = [self._argocd, "app", "sync", name, "--dry-run", "--server-side"]
        cmd += self._auth

        p = subprocess.run(cmd, capture_output=True)
        ret["return"] = p.returncode
        ret["stdout"] = p.stdout.decode("utf-8")
        ret["stderr"] = p.stderr.decode("utf-8")

        if p.returncode != 0:
            raise RuntimeError(
                "argocd diff for %s exited with return code %d: %s - %s",
                name,
                p.returncode,
                p.stderr.decode("utf-8"),
                p.stdout.decode("utf-8"),
            )

        return ret


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
    argocd = Argocd(
        os.environ["ARGOCD_SERVER"],
        os.environ["ARGOCD_TOKEN"],
        os.environ["REPO_URL"],
        os.environ["REF_NAME"],
    )

    artifact_dir = os.environ["ARTIFACT_DIR"]
    os.makedirs(artifact_dir, exist_ok=True)

    results = []

    for app in argocd.get_apps():
        res = {"name": app["metadata"]["name"], "dry_run": {}}
        argocd.refresh_app(app)
        res["diff"] = argocd.get_diff(app)
        if res["diff"]["return"] == 1:
            res["dry_run"] = argocd.dry_run(app)

        results.append(res)

    with open(os.path.join(artifact_dir, "diff-output.json"), "w") as fp:
        json.dump(results, fp, indent=2, sort_keys=True)

    comment = "ArgoCD diff check results\n"

    for res in results:
        if res["diff"]["return"] == 1:
            name = res["name"]
            namespace = res["diff"]["namespace"]
            project = res["diff"]["project"]
            comment += f"Diff found for {namespace}/{name} "
            comment += f"in project {project}\n"
            comment += "\n```diff\n"
            comment += res["diff"]["diff"].strip()
            comment += "```\n"

    if os.environ["EVENT_NAME"] == "pull_request":
        forgejo.add_pr_comment(os.environ["REPO"], os.environ["PR_NUMBER"], comment)
    else:
        forgejo.add_commit_comment(
            os.environ["REPO"], os.environ["COMMIT_SHA"], comment
        )


if __name__ == "__main__":
    main()
