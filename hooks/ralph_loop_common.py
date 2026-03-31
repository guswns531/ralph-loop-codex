#!/usr/bin/env python3

import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


STATE_RELATIVE_PATH = Path(".codex/ralph-loop.local.md")
ACTIVATION_TOKENS = {"/ralph-loop", "$ralph-loop-codex"}
CANCEL_TOKENS = {"/cancel-ralph"}
PROMISE_RE = re.compile(r"<promise>(.*?)</promise>", re.DOTALL)
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def resolve_project_root(cwd: str) -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        root = result.stdout.strip()
        if root:
            return Path(root)
    except Exception:
        pass
    return Path(cwd)


def state_path_for_cwd(cwd: str) -> Path:
    return resolve_project_root(cwd) / STATE_RELATIVE_PATH


def quote_yaml_string(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def unquote_yaml_string(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
        inner = value[1:-1]
        return inner.replace('\\"', '"').replace("\\\\", "\\")
    return value


def parse_frontmatter(text: str):
    match = FRONTMATTER_RE.match(text)
    if not match:
        return None, None
    frontmatter_text, prompt_text = match.groups()
    frontmatter = {}
    for raw_line in frontmatter_text.splitlines():
        if ":" not in raw_line:
            continue
        key, value = raw_line.split(":", 1)
        frontmatter[key.strip()] = value.strip()
    return frontmatter, prompt_text


def load_state(path: Path):
    if not path.exists():
        return None
    try:
        frontmatter, prompt_text = parse_frontmatter(path.read_text())
    except Exception:
        return None
    if frontmatter is None:
        return None
    return {
        "frontmatter": frontmatter,
        "prompt_text": prompt_text,
    }


def save_state(
    path: Path,
    *,
    iteration: int,
    session_id: str,
    max_iterations: int,
    completion_promise,
    prompt_text: str,
    started_at: str = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if completion_promise is not None and completion_promise != "null":
        completion_promise_yaml = quote_yaml_string(completion_promise)
    else:
        completion_promise_yaml = "null"
    if started_at is None:
        started_at = utc_now_iso()
    prompt_text = prompt_text.lstrip("\n").rstrip("\n")
    contents = (
        "---\n"
        "active: true\n"
        f"iteration: {iteration}\n"
        f"session_id: {session_id}\n"
        f"max_iterations: {max_iterations}\n"
        f"completion_promise: {completion_promise_yaml}\n"
        f'started_at: "{started_at}"\n'
        "---\n\n"
        f"{prompt_text}\n"
    )
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(contents)
    os.replace(tmp_path, path)


def update_iteration(path: Path, next_iteration: int) -> bool:
    state = load_state(path)
    if not state:
        return False
    frontmatter = state["frontmatter"]
    prompt_text = state["prompt_text"]
    max_iterations = parse_int(frontmatter.get("max_iterations", ""))
    if max_iterations is None:
        return False
    completion_raw = frontmatter.get("completion_promise", "null")
    completion_promise = None if completion_raw == "null" else unquote_yaml_string(completion_raw)
    save_state(
        path,
        iteration=next_iteration,
        session_id=frontmatter.get("session_id", ""),
        max_iterations=max_iterations,
        completion_promise=completion_promise,
        prompt_text=prompt_text,
        started_at=unquote_yaml_string(frontmatter.get("started_at", "")),
    )
    return True


def delete_state(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def parse_promise_text(message: str) -> str:
    if not message:
        return ""
    match = PROMISE_RE.search(message)
    if not match:
        return ""
    return " ".join(match.group(1).split())


def parse_int(value: str):
    value = value.strip()
    if not value.isdigit():
        return None
    return int(value)


def activation_usage() -> str:
    return (
        "Usage: /ralph-loop \"TASK\" [--max-iterations N] [--completion-promise \"TEXT\"]\n"
        "Alt:   $ralph-loop-codex \"TASK\" [--max-iterations N] [--completion-promise \"TEXT\"]"
    )
