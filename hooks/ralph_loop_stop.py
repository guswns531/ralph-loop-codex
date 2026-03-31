#!/usr/bin/env python3

import json
import sys

from ralph_loop_common import (
    delete_state,
    load_state,
    parse_int,
    parse_promise_text,
    state_path_for_cwd,
    unquote_yaml_string,
    update_iteration,
)


def main():
    payload = json.load(sys.stdin)
    state_path = state_path_for_cwd(payload["cwd"])
    state = load_state(state_path)
    if not state:
        return

    frontmatter = state["frontmatter"]
    prompt_text = state["prompt_text"].lstrip("\n").rstrip("\n")

    state_session = frontmatter.get("session_id", "")
    hook_session = payload.get("session_id") or ""
    if state_session and hook_session and state_session != hook_session:
        return

    iteration = parse_int(frontmatter.get("iteration", ""))
    if iteration is None:
        delete_state(state_path)
        print(
            json.dumps(
                {
                    "systemMessage": (
                        "⚠️  Ralph loop: State file corrupted. Problem: 'iteration' field is not a valid number. "
                        "Ralph loop is stopping. Run /ralph-loop again to start fresh."
                    )
                }
            )
        )
        return

    max_iterations = parse_int(frontmatter.get("max_iterations", ""))
    if max_iterations is None:
        delete_state(state_path)
        print(
            json.dumps(
                {
                    "systemMessage": (
                        "⚠️  Ralph loop: State file corrupted. Problem: 'max_iterations' field is not a valid number. "
                        "Ralph loop is stopping. Run /ralph-loop again to start fresh."
                    )
                }
            )
        )
        return

    completion_raw = frontmatter.get("completion_promise", "null")
    completion_promise = None if completion_raw == "null" else unquote_yaml_string(completion_raw)
    last_message = payload.get("last_assistant_message") or ""

    if completion_promise:
        promise_text = parse_promise_text(last_message)
        if promise_text == completion_promise:
            delete_state(state_path)
            print(
                json.dumps(
                    {
                        "systemMessage": f"✅ Ralph loop: Detected <promise>{completion_promise}</promise>"
                    }
                )
            )
            return

    if max_iterations > 0 and iteration >= max_iterations:
        delete_state(state_path)
        print(
            json.dumps(
                {
                    "systemMessage": f"🛑 Ralph loop: Max iterations ({max_iterations}) reached."
                }
            )
        )
        return

    next_iteration = iteration + 1
    if not prompt_text:
        delete_state(state_path)
        print(
            json.dumps(
                {
                    "systemMessage": (
                        "⚠️  Ralph loop: State file corrupted or incomplete. Problem: No prompt text found. "
                        "Ralph loop is stopping. Run /ralph-loop again to start fresh."
                    )
                }
            )
        )
        return

    if not update_iteration(state_path, next_iteration):
        delete_state(state_path)
        print(
            json.dumps(
                {
                    "systemMessage": "⚠️  Ralph loop: Failed to update state file. Ralph loop is stopping."
                }
            )
        )
        return

    if completion_promise:
        stop_rule = (
            f"🔄 Ralph iteration {next_iteration} | To stop: output <promise>{completion_promise}</promise> "
            "(ONLY when statement is TRUE - do not lie to exit!)"
        )
    else:
        stop_rule = f"🔄 Ralph iteration {next_iteration} | No completion promise set - loop runs infinitely"

    output = {
        "decision": "block",
        "reason": prompt_text,
        "systemMessage": stop_rule,
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
