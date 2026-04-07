#!/usr/bin/env python3

import json
import shlex
import sys

from ralph_loop_common import (
    ACTIVATION_TOKENS,
    APPROVE_TOKENS,
    CANCEL_TOKENS,
    activation_usage,
    build_loop_prompt,
    build_task_brief,
    build_task_rows,
    display_state_path,
    display_tasks_path,
    load_state,
    parse_int,
    save_state,
    state_path_for_session,
    tasks_path_for_session,
    unquote_yaml_string,
    write_tasks_tsv,
)


def block(reason: str):
    print(json.dumps({"decision": "block", "reason": reason}))


def activate(payload):
    prompt = payload["prompt"]
    tokens = shlex.split(prompt)
    args = tokens[1:]

    prompt_parts = []
    max_iterations = 0
    completion_promise = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in {"-h", "--help"}:
            block(activation_usage())
            return
        if arg == "--max-iterations":
            if i + 1 >= len(args):
                block("Missing value for --max-iterations.\n" + activation_usage())
                return
            value = args[i + 1]
            if not value.isdigit():
                block(f"--max-iterations must be a non-negative integer, got: {value}")
                return
            max_iterations = int(value)
            i += 2
            continue
        if arg == "--completion-promise":
            if i + 1 >= len(args):
                block("Missing value for --completion-promise.\n" + activation_usage())
                return
            completion_promise = args[i + 1]
            i += 2
            continue
        prompt_parts.append(arg)
        i += 1

    task = " ".join(prompt_parts).strip()
    if not task:
        block("No Ralph task provided.\n" + activation_usage())
        return

    state_path = state_path_for_session(payload["cwd"], payload["session_id"])
    tasks_path = tasks_path_for_session(payload["cwd"], payload["session_id"])
    task_brief = build_task_brief(task, completion_promise, max_iterations)
    task_rows = build_task_rows(task)
    loop_prompt = build_loop_prompt(
        task_brief,
        display_tasks_path(payload["cwd"], payload["session_id"]),
        completion_promise,
    )
    write_tasks_tsv(tasks_path, task_rows)
    save_state(
        state_path,
        status="draft",
        iteration=1,
        session_id=payload["session_id"],
        max_iterations=max_iterations,
        completion_promise=completion_promise,
        prompt_text=loop_prompt,
    )

    additional_context = (
        "Ralph draft prepared for this session.\n\n"
        "Do not execute the task yet.\n"
        "Refine the brief below if needed, then ask the user for explicit approval to start the loop.\n"
        "Tell the user to run $ralph-approve to begin or $cancel-ralph to discard.\n\n"
        f"Draft file: {display_state_path(payload['cwd'], payload['session_id'])}\n\n"
        f"Task TSV: {display_tasks_path(payload['cwd'], payload['session_id'])}\n\n"
        "Generated loop brief:\n\n"
        f"{loop_prompt}"
    )

    output = {
        "systemMessage": "Ralph draft prepared. Awaiting user approval.",
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context,
        },
    }
    print(json.dumps(output))


def approve(payload):
    state_path = state_path_for_session(payload["cwd"], payload["session_id"])
    state = load_state(state_path)
    if not state:
        block("No pending Ralph draft found for this session. Start one with /ralph-loop first.")
        return

    frontmatter = state["frontmatter"]
    if frontmatter.get("status") == "active":
        block("Ralph loop is already active in this session.")
        return

    max_iterations_raw = frontmatter.get("max_iterations", "0")
    max_iterations = parse_int(max_iterations_raw)
    if max_iterations is None:
        block("Pending Ralph draft is corrupted: max_iterations is invalid. Start again with /ralph-loop.")
        return
    completion_raw = frontmatter.get("completion_promise", "null")
    completion_promise = None if completion_raw == "null" else unquote_yaml_string(completion_raw)
    loop_prompt = state["prompt_text"].lstrip("\n").rstrip("\n")

    save_state(
        state_path,
        status="active",
        iteration=1,
        session_id=payload["session_id"],
        max_iterations=max_iterations,
        completion_promise=completion_promise,
        prompt_text=loop_prompt,
        started_at=unquote_yaml_string(frontmatter.get("started_at", "")) or None,
    )

    if completion_promise:
        promise_rule = (
            f"To complete this loop, output this EXACT text:\n"
            f"  <promise>{completion_promise}</promise>\n"
            "ONLY when the statement is completely and unequivocally TRUE."
        )
    else:
        promise_rule = "No completion promise set - loop runs infinitely unless max iterations is reached."

    additional_context = (
        "🔄 Ralph loop activated in this session!\n\n"
        "Iteration: 1\n"
        f"Max iterations: {max_iterations if max_iterations > 0 else 'unlimited'}\n"
        f"Completion promise: {completion_promise if completion_promise else 'none (runs forever)'}\n\n"
        "The Stop hook is now active. When you try to stop, the SAME PROMPT will be fed back to you.\n"
        "You'll see your previous work in files and the TSV tracker, creating a self-referential loop where you iteratively improve on the same task.\n\n"
        f"To monitor: head -10 {display_state_path(payload['cwd'], payload['session_id'])}\n\n"
        f"Task TSV: {display_tasks_path(payload['cwd'], payload['session_id'])}\n\n"
        f"{loop_prompt}\n\n"
        f"{promise_rule}"
    )

    output = {
        "systemMessage": "🔄 Ralph loop activated in this session!",
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context,
        },
    }
    print(json.dumps(output))


def cancel(payload):
    state_path = state_path_for_session(payload["cwd"], payload["session_id"])
    tasks_path = tasks_path_for_session(payload["cwd"], payload["session_id"])
    state = load_state(state_path)
    if not state and not tasks_path.exists():
        block("No Ralph state found for this session.")
        return
    iteration = state["frontmatter"].get("iteration", "?") if state else "?"
    state_path.unlink(missing_ok=True)
    tasks_path.unlink(missing_ok=True)
    block(f"Cancelled Ralph loop (was at iteration {iteration}).")


def main():
    payload = json.load(sys.stdin)
    prompt = payload.get("prompt", "").strip()
    if not prompt:
        return

    try:
        tokens = shlex.split(prompt)
    except ValueError as exc:
        if prompt.startswith("/ralph-loop") or prompt.startswith("$ralph-loop-codex"):
            block(f"Failed to parse Ralph loop arguments: {exc}")
        return

    if not tokens:
        return

    command = tokens[0]
    if command in CANCEL_TOKENS:
        cancel(payload)
        return
    if command in APPROVE_TOKENS:
        approve(payload)
        return
    if command in ACTIVATION_TOKENS:
        activate(payload)


if __name__ == "__main__":
    main()
