from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.git_tools.git_tools")
logger.debug("Loaded tool module: git_tools.git_tools")

import subprocess
from app.utils.groq import tool


def _run(args):
    return subprocess.check_output(["git"] + args, text=True, errors="ignore")


@tool(
    name="git_status",
    description="Git status.",
    params={},
)
def git_status():
    return _run(["status", "-sb"])


@tool(
    name="git_diff",
    description="Git diff.",
    params={"args": {"type": "array", "description": "Extra args (optional)"}},
)
def git_diff(args: list[str] | None = None):
    return _run(["diff"] + (args or []))


@tool(
    name="git_log",
    description="Git log.",
    params={"n": {"type": "integer", "description": "Number of commits"}},
)
def git_log(n: int = 10):
    return _run(["log", f"-n{n}", "--oneline"])


@tool(
    name="git_branch",
    description="Git branch list.",
    params={},
)
def git_branch():
    return _run(["branch"])


@tool(
    name="git_commit",
    description="Git commit.",
    params={"message": {"type": "string"}},
)
def git_commit(message: str):
    return _run(["commit", "-am", message])


@tool(
    name="git_run",
    description="Run arbitrary git command.",
    params={"args": {"type": "array"}},
)
def git_run(args: list[str]):
    return _run(args)


@tool(
    name="git_add",
    description="Git add files.",
    params={"paths": {"type": "array", "description": "Paths to add"}},
)
def git_add(paths: list[str]):
    return _run(["add"] + paths)


@tool(
    name="git_checkout",
    description="Git checkout a branch or ref.",
    params={
        "ref": {"type": "string"},
        "create": {"type": "boolean", "description": "Create new branch (optional)"},
    },
)
def git_checkout(ref: str, create: bool = False):
    args = ["checkout"]
    if create:
        args += ["-b"]
    args.append(ref)
    return _run(args)


@tool(
    name="git_pull",
    description="Git pull.",
    params={
        "remote": {"type": "string", "description": "Remote name (optional)"},
        "branch": {"type": "string", "description": "Branch name (optional)"},
        "rebase": {"type": "boolean", "description": "Use --rebase (optional)"},
    },
)
def git_pull(remote: str = "", branch: str = "", rebase: bool = False):
    args = ["pull"]
    if rebase:
        args.append("--rebase")
    if remote:
        args.append(remote)
    if branch:
        args.append(branch)
    return _run(args)


@tool(
    name="git_push",
    description="Git push.",
    params={
        "remote": {"type": "string", "description": "Remote name (optional)"},
        "branch": {"type": "string", "description": "Branch name (optional)"},
        "set_upstream": {"type": "boolean", "description": "Set upstream (optional)"},
    },
)
def git_push(remote: str = "", branch: str = "", set_upstream: bool = False):
    args = ["push"]
    if set_upstream:
        args.append("-u")
    if remote:
        args.append(remote)
    if branch:
        args.append(branch)
    return _run(args)


@tool(
    name="git_fetch",
    description="Git fetch.",
    params={
        "remote": {"type": "string", "description": "Remote name (optional)"},
        "prune": {"type": "boolean", "description": "Prune (optional)"},
    },
)
def git_fetch(remote: str = "", prune: bool = False):
    args = ["fetch"]
    if prune:
        args.append("--prune")
    if remote:
        args.append(remote)
    return _run(args)


@tool(
    name="git_merge",
    description="Git merge a ref into current branch.",
    params={"ref": {"type": "string"}},
)
def git_merge(ref: str):
    return _run(["merge", ref])


@tool(
    name="git_reset",
    description="Git reset to a ref.",
    params={
        "ref": {"type": "string", "description": "Target ref"},
        "mode": {"type": "string", "description": "soft|mixed|hard (optional)"},
    },
)
def git_reset(ref: str, mode: str = "mixed"):
    return _run(["reset", f"--{mode}", ref])


@tool(
    name="git_show",
    description="Git show a ref.",
    params={
        "ref": {"type": "string", "description": "Commit/tag/ref"},
        "pretty": {"type": "string", "description": "Pretty format (optional)"},
    },
)
def git_show(ref: str = "HEAD", pretty: str = ""):
    args = ["show"]
    if pretty:
        args += [f"--pretty={pretty}"]
    args.append(ref)
    return _run(args)


@tool(
    name="git_stash",
    description="Git stash operations.",
    params={
        "action": {"type": "string", "description": "list|push|pop|apply|drop"},
        "message": {"type": "string", "description": "Message for push (optional)"},
    },
)
def git_stash(action: str = "list", message: str = ""):
    if action == "list":
        return _run(["stash", "list"])
    if action == "push":
        args = ["stash", "push"]
        if message:
            args += ["-m", message]
        return _run(args)
    if action == "pop":
        return _run(["stash", "pop"])
    if action == "apply":
        return _run(["stash", "apply"])
    if action == "drop":
        return _run(["stash", "drop"])
    return "unknown action"


@tool(
    name="git_tag_list",
    description="List git tags.",
    params={},
)
def git_tag_list():
    return _run(["tag", "-l"])


@tool(
    name="git_tag_create",
    description="Create a git tag.",
    params={
        "name": {"type": "string"},
        "ref": {"type": "string", "description": "Target ref (optional)"},
    },
)
def git_tag_create(name: str, ref: str = ""):
    args = ["tag", name]
    if ref:
        args.append(ref)
    return _run(args)


@tool(
    name="git_tag_delete",
    description="Delete a git tag.",
    params={"name": {"type": "string"}},
)
def git_tag_delete(name: str):
    return _run(["tag", "-d", name])


@tool(
    name="git_remote_list",
    description="List git remotes.",
    params={},
)
def git_remote_list():
    return _run(["remote", "-v"])


@tool(
    name="git_remote_add",
    description="Add a git remote.",
    params={
        "name": {"type": "string"},
        "url": {"type": "string"},
    },
)
def git_remote_add(name: str, url: str):
    return _run(["remote", "add", name, url])


@tool(
    name="git_remote_remove",
    description="Remove a git remote.",
    params={"name": {"type": "string"}},
)
def git_remote_remove(name: str):
    return _run(["remote", "remove", name])
