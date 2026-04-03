from __future__ import annotations

import logging
logger = logging.getLogger("NoorRobot.Tools.codeExecutor.codeExecutor")
logger.debug("Loaded tool module: codeExecutor.codeExecutor")

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from app.utils.groq import tool


def _run_subprocess(
    args: list[str],
    timeout: int,
    cwd: str | None,
    env: dict | None,
    stdin: str | None = None,
):
    completed = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd,
        env=env,
        input=stdin,
    )
    return {
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


@tool(
    name="list_languages",
    description="List supported execution languages.",
    params={},
)
def list_languages():
    return ["python", "java", "c", "cpp", "js", "html", "css", "cmd", "powershell"]


@tool(
    name="execute_code",
    description="Execute code in a chosen language and return stdout/stderr.",
    params={
        "language": {"type": "string", "description": "python|cmd|powershell"},
        "code": {"type": "string", "description": "Code to execute"},
        "args": {"type": "array", "description": "Command-line args (optional)"},
        "stdin": {"type": "string", "description": "stdin content (optional)"},
        "timeout": {"type": "integer", "description": "Timeout in seconds (default 10)"},
        "cwd": {"type": "string", "description": "Working directory (optional)"},
        "env": {"type": "object", "description": "Environment variables dict (optional)"},
    },
)
def execute_code(
    language: str,
    code: str,
    args: list[str] | None = None,
    stdin: str | None = None,
    timeout: int = 10,
    cwd: str | None = None,
    env: dict | None = None,
):
    language = (language or "").lower().strip()
    timeout = int(timeout) if timeout is not None else 10
    cwd = cwd or None
    env_vars = os.environ.copy()
    if env:
        env_vars.update({str(k): str(v) for k, v in env.items()})
    args = args or []

    if language == "python":
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "code_exec.py"
            script_path.write_text(code, encoding="utf-8")
            return _run_subprocess(
                [os.environ.get("PYTHON", "python"), str(script_path)] + list(args),
                timeout=timeout,
                cwd=cwd,
                env=env_vars,
                stdin=stdin,
            )
    if language == "java":
        with tempfile.TemporaryDirectory() as tmpdir:
            src_path = Path(tmpdir) / "Main.java"
            src_path.write_text(code, encoding="utf-8")
            if _which("javac") is None or _which("java") is None:
                return {"exit_code": 127, "stdout": "", "stderr": "javac/java not found in PATH"}
            compile_res = _run_subprocess(
                ["javac", str(src_path)], timeout=timeout, cwd=tmpdir, env=env_vars, stdin=stdin
            )
            if compile_res["exit_code"] != 0:
                return compile_res
            return _run_subprocess(
                ["java", "Main"] + list(args), timeout=timeout, cwd=tmpdir, env=env_vars, stdin=stdin
            )
    if language in ("c", "cpp"):
        with tempfile.TemporaryDirectory() as tmpdir:
            ext = "c" if language == "c" else "cpp"
            src_path = Path(tmpdir) / f"main.{ext}"
            src_path.write_text(code, encoding="utf-8")
            exe_path = Path(tmpdir) / "a.exe"

            if _which("cl"):
                # MSVC
                cl_args = ["cl", "/nologo", str(src_path), "/Fe:" + str(exe_path)]
                if language == "cpp":
                    cl_args.insert(2, "/EHsc")
                compile_res = _run_subprocess(cl_args, timeout=timeout, cwd=tmpdir, env=env_vars, stdin=stdin)
                if compile_res["exit_code"] != 0:
                    return compile_res
                return _run_subprocess([str(exe_path)] + list(args), timeout=timeout, cwd=tmpdir, env=env_vars, stdin=stdin)

            compiler = "gcc" if language == "c" else "g++"
            if _which(compiler) is None:
                return {"exit_code": 127, "stdout": "", "stderr": f"{compiler} not found in PATH"}
            compile_res = _run_subprocess(
                [compiler, str(src_path), "-o", str(exe_path)],
                timeout=timeout,
                cwd=tmpdir,
                env=env_vars,
                stdin=stdin,
            )
            if compile_res["exit_code"] != 0:
                return compile_res
            return _run_subprocess([str(exe_path)] + list(args), timeout=timeout, cwd=tmpdir, env=env_vars, stdin=stdin)
    if language == "js":
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "script.js"
            script_path.write_text(code, encoding="utf-8")
            if _which("node") is None:
                return {"exit_code": 127, "stdout": "", "stderr": "node not found in PATH"}
            return _run_subprocess(
                ["node", str(script_path)] + list(args), timeout=timeout, cwd=tmpdir, env=env_vars, stdin=stdin
            )
    if language in ("html", "css"):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_name = "index.html" if language == "html" else "styles.css"
            file_path = Path(tmpdir) / file_name
            file_path.write_text(code, encoding="utf-8")
            return {
                "exit_code": 0,
                "stdout": f"Saved {language} to {file_path}",
                "stderr": "",
            }
    if language == "cmd":
        cmd_line = code
        if args:
            cmd_line = " ".join([code] + [str(a) for a in args])
        return _run_subprocess(
            ["cmd.exe", "/c", cmd_line], timeout=timeout, cwd=cwd, env=env_vars, stdin=stdin
        )
    if language == "powershell":
        ps_line = code
        if args:
            ps_line = " ".join([code] + [str(a) for a in args])
        return _run_subprocess(
            ["powershell.exe", "-NoLogo", "-NoProfile", "-Command", ps_line],
            timeout=timeout,
            cwd=cwd,
            env=env_vars,
            stdin=stdin,
        )

    raise ValueError(
        "Unsupported language. Use: python, java, c, cpp, js, html, css, cmd, powershell"
    )


@tool(
    name="execute_file",
    description="Execute a code file by language.",
    params={
        "language": {"type": "string", "description": "python|java|c|cpp|js|cmd|powershell"},
        "path": {"type": "string", "description": "File path"},
        "args": {"type": "array", "description": "Command-line args (optional)"},
        "stdin": {"type": "string", "description": "stdin content (optional)"},
        "timeout": {"type": "integer", "description": "Timeout in seconds (default 10)"},
        "cwd": {"type": "string", "description": "Working directory (optional)"},
        "env": {"type": "object", "description": "Environment variables dict (optional)"},
    },
)
def execute_file(
    language: str,
    path: str,
    args: list[str] | None = None,
    stdin: str | None = None,
    timeout: int = 10,
    cwd: str | None = None,
    env: dict | None = None,
):
    language = (language or "").lower().strip()
    args = args or []
    env_vars = os.environ.copy()
    if env:
        env_vars.update({str(k): str(v) for k, v in env.items()})
    path = str(Path(path).expanduser())

    if language == "python":
        return _run_subprocess(
            [os.environ.get("PYTHON", "python"), path] + list(args),
            timeout=timeout,
            cwd=cwd,
            env=env_vars,
            stdin=stdin,
        )
    if language == "java":
        if _which("javac") is None or _which("java") is None:
            return {"exit_code": 127, "stdout": "", "stderr": "javac/java not found in PATH"}
        src_path = Path(path)
        tmpdir = src_path.parent
        compile_res = _run_subprocess(
            ["javac", str(src_path)], timeout=timeout, cwd=str(tmpdir), env=env_vars, stdin=stdin
        )
        if compile_res["exit_code"] != 0:
            return compile_res
        return _run_subprocess(
            ["java", src_path.stem] + list(args), timeout=timeout, cwd=str(tmpdir), env=env_vars, stdin=stdin
        )
    if language in ("c", "cpp"):
        ext = "c" if language == "c" else "cpp"
        src_path = Path(path)
        if src_path.suffix.lower() != f".{ext}":
            return {"exit_code": 2, "stdout": "", "stderr": f"Expected .{ext} file"}
        out_path = src_path.with_suffix(".exe")
        if _which("cl"):
            cl_args = ["cl", "/nologo", str(src_path), "/Fe:" + str(out_path)]
            if language == "cpp":
                cl_args.insert(2, "/EHsc")
            compile_res = _run_subprocess(cl_args, timeout=timeout, cwd=str(src_path.parent), env=env_vars, stdin=stdin)
            if compile_res["exit_code"] != 0:
                return compile_res
            return _run_subprocess([str(out_path)] + list(args), timeout=timeout, cwd=str(src_path.parent), env=env_vars, stdin=stdin)
        compiler = "gcc" if language == "c" else "g++"
        if _which(compiler) is None:
            return {"exit_code": 127, "stdout": "", "stderr": f"{compiler} not found in PATH"}
        compile_res = _run_subprocess(
            [compiler, str(src_path), "-o", str(out_path)],
            timeout=timeout,
            cwd=str(src_path.parent),
            env=env_vars,
            stdin=stdin,
        )
        if compile_res["exit_code"] != 0:
            return compile_res
        return _run_subprocess([str(out_path)] + list(args), timeout=timeout, cwd=str(src_path.parent), env=env_vars, stdin=stdin)
    if language == "js":
        if _which("node") is None:
            return {"exit_code": 127, "stdout": "", "stderr": "node not found in PATH"}
        return _run_subprocess(["node", path] + list(args), timeout=timeout, cwd=cwd, env=env_vars, stdin=stdin)
    if language == "cmd":
        return _run_subprocess(["cmd.exe", "/c", path], timeout=timeout, cwd=cwd, env=env_vars, stdin=stdin)
    if language == "powershell":
        return _run_subprocess(["powershell.exe", "-NoLogo", "-NoProfile", "-File", path] + list(args), timeout=timeout, cwd=cwd, env=env_vars, stdin=stdin)
    raise ValueError("Unsupported language for execute_file")
