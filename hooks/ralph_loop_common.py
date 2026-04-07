#!/usr/bin/env python3

import os
import re
from datetime import datetime, timezone
from pathlib import Path


STATE_DIR_RELATIVE_PATH = Path(".codex/ralph-loop")
ACTIVATION_TOKENS = {
    "/ralph-loop",
    "/ralph-loop-codex",
    "$ralph-loop",
    "$ralph-loop-codex",
    "ralph-loop",
}
CANCEL_TOKENS = {"/cancel-ralph", "$cancel-ralph", "cancel-ralph"}
APPROVE_TOKENS = {"/ralph-approve", "$ralph-approve", "ralph-approve"}
PROMISE_RE = re.compile(r"<promise>(.*?)</promise>", re.DOTALL)
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def state_dir_for_cwd(cwd: str) -> Path:
    return Path(cwd) / STATE_DIR_RELATIVE_PATH


def state_path_for_session(cwd: str, session_id: str) -> Path:
    safe_session_id = re.sub(r"[^A-Za-z0-9._-]", "_", session_id or "unknown-session")
    return state_dir_for_cwd(cwd) / f"{safe_session_id}.md"


def tasks_path_for_session(cwd: str, session_id: str) -> Path:
    safe_session_id = re.sub(r"[^A-Za-z0-9._-]", "_", session_id or "unknown-session")
    return state_dir_for_cwd(cwd) / f"{safe_session_id}.tsv"


def display_state_path(cwd: str, session_id: str) -> Path:
    return state_path_for_session(cwd, session_id).relative_to(Path(cwd))


def display_tasks_path(cwd: str, session_id: str) -> Path:
    return tasks_path_for_session(cwd, session_id).relative_to(Path(cwd))


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
    status: str,
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
        f"status: {status}\n"
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
        status=frontmatter.get("status", "active"),
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


def write_tasks_tsv(path: Path, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["id\tstatus\ttype\ttitle\tverify\tnotes"]
    for row in rows:
        cells = [
            str(row.get("id", "")),
            str(row.get("status", "")),
            str(row.get("type", "")),
            str(row.get("title", "")),
            str(row.get("verify", "")),
            str(row.get("notes", "")),
        ]
        lines.append("\t".join(cell.replace("\t", " ").replace("\n", " ").strip() for cell in cells))
    path.write_text("\n".join(lines) + "\n")


def load_tasks_tsv(path: Path):
    if not path.exists():
        return None
    lines = [line.rstrip("\n") for line in path.read_text().splitlines() if line.strip()]
    if not lines:
        return []
    header = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        values = line.split("\t")
        if len(values) < len(header):
            values.extend([""] * (len(header) - len(values)))
        rows.append(dict(zip(header, values)))
    return rows


def build_task_rows(task: str):
    task = task.strip()
    return [
        {
            "id": 1,
            "status": "todo",
            "type": "inspect",
            "title": f"Inspect the current code and constraints for: {task}",
            "verify": "Relevant files, tests, and constraints are identified.",
            "notes": "",
        },
        {
            "id": 2,
            "status": "todo",
            "type": "plan",
            "title": f"Refine the implementation plan for: {task}",
            "verify": "The TSV reflects a concrete sequence of verifiable steps.",
            "notes": "Split or rewrite rows if the task needs finer-grained work.",
        },
        {
            "id": 3,
            "status": "todo",
            "type": "implement",
            "title": f"Implement the required changes for: {task}",
            "verify": "Code changes are applied and aligned with the task.",
            "notes": "",
        },
        {
            "id": 4,
            "status": "todo",
            "type": "verify",
            "title": f"Verify that {task}",
            "verify": "Run the strongest relevant checks and confirm acceptance criteria.",
            "notes": "",
        },
    ]


def build_task_brief(task: str, completion_promise, max_iterations: int) -> str:
    promise_text = completion_promise or "Define an explicit promise before approval if needed."
    iteration_text = str(max_iterations) if max_iterations > 0 else "unlimited"
    task = task.strip()
    return (
        "Goal:\n"
        f"{task}\n\n"
        "Working rules:\n"
        "- Freeze this brief once approved.\n"
        "- Inspect the current workspace before making changes.\n"
        "- Prefer the smallest verifiable next step.\n"
        "- Run relevant verification after each meaningful change.\n"
        "- Stop only when the completion condition is genuinely satisfied.\n\n"
        "Done condition:\n"
        f"- Completion promise: {promise_text}\n"
        f"- Hard stop: {iteration_text} iterations\n"
    )


def build_loop_prompt(task_brief: str, tasks_display_path: Path, completion_promise) -> str:
    lines = [
        "Execute the approved Ralph loop brief below.",
        "",
        task_brief.strip(),
        "",
        "Task tracker rules:",
        f"- Use `{tasks_display_path}` as the source of truth for loop progress.",
        "- Before making substantial changes, review the TSV and choose the next unfinished row.",
        "- Update the TSV as you work. Valid statuses: todo, doing, done, blocked, skipped.",
        "- Do not claim completion while any required TSV row is not done.",
        "- If the TSV is too coarse or wrong, refine it in place before continuing.",
        "- Each completed row should have its verification condition actually satisfied.",
    ]
    if completion_promise:
        lines.extend(
            [
                "",
                "Completion rule:",
                f"- Once every required TSV row is done and verified, output `<promise>{completion_promise}</promise>`.",
                "- Do not output the promise early.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "Completion rule:",
                "- Once every required TSV row is done and verified, stop cleanly.",
                "- Do not stop while unfinished required rows remain.",
            ]
        )
    return "\n".join(lines)


def summarize_open_tasks(rows) -> str:
    if rows is None:
        return "Task TSV is missing."
    open_rows = [row for row in rows if row.get("status", "").strip().lower() not in {"done", "skipped"}]
    if not open_rows:
        return ""
    parts = []
    for row in open_rows[:5]:
        parts.append(f"{row.get('id', '?')}:{row.get('status', 'todo')}:{row.get('title', '').strip()}")
    suffix = " ..." if len(open_rows) > 5 else ""
    return "Open TSV rows: " + " | ".join(parts) + suffix


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
        "Alt:   $ralph-loop \"TASK\" [--max-iterations N] [--completion-promise \"TEXT\"]\n"
        "Alt:   ralph-loop \"TASK\" [--max-iterations N] [--completion-promise \"TEXT\"]\n"
        "Then:  $ralph-approve"
    )
