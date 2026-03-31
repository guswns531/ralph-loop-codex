#!/usr/bin/env python3

import json
import shlex
import sys

from ralph_loop_common import (
    ACTIVATION_TOKENS,
    CANCEL_TOKENS,
    activation_usage,
    load_state,
    save_state,
    state_path_for_cwd,
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

    state_path = state_path_for_cwd(payload["cwd"])
    save_state(
        state_path,
        iteration=1,
        session_id=payload["session_id"],
        max_iterations=max_iterations,
        completion_promise=completion_promise,
        prompt_text=task,
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
        "You'll see your previous work in files, creating a self-referential loop where you iteratively improve on the same task.\n\n"
        f"To monitor: head -10 {state_path.relative_to(state_path.parent.parent)}\n\n"
        "⚠️  WARNING: This loop cannot be stopped naturally unless you reach --max-iterations or --completion-promise.\n\n"
        f"{task}\n\n"
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
    state_path = state_path_for_cwd(payload["cwd"])
    state = load_state(state_path)
    if not state:
        block("No active Ralph loop found.")
        return
    iteration = state["frontmatter"].get("iteration", "?")
    state_path.unlink(missing_ok=True)
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
    if command in ACTIVATION_TOKENS:
        activate(payload)


if __name__ == "__main__":
    main()
