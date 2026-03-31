#!/usr/bin/env python3

import json
from pathlib import Path


def remove_command_hook(hooks_block, command: str):
    new_block = []
    for group in hooks_block:
        hooks = [item for item in group.get("hooks", []) if item.get("command") != command]
        if hooks:
            new_group = dict(group)
            new_group["hooks"] = hooks
            new_block.append(new_group)
    return new_block


def main() -> None:
    codex_home = Path.home() / ".codex"
    hooks_dir = codex_home / "hooks"
    hooks_json_path = codex_home / "hooks.json"

    for filename in [
        "ralph_loop_common.py",
        "ralph_loop_user_prompt_submit.py",
        "ralph_loop_stop.py",
    ]:
        (hooks_dir / filename).unlink(missing_ok=True)

    if hooks_json_path.exists():
        data = json.loads(hooks_json_path.read_text())
        hooks = data.get("hooks", {})
        hooks["UserPromptSubmit"] = remove_command_hook(
            hooks.get("UserPromptSubmit", []),
            "python3 ~/.codex/hooks/ralph_loop_user_prompt_submit.py",
        )
        hooks["Stop"] = remove_command_hook(
            hooks.get("Stop", []),
            "python3 ~/.codex/hooks/ralph_loop_stop.py",
        )
        data["hooks"] = hooks
        hooks_json_path.write_text(json.dumps(data, indent=2) + "\n")

    print("Uninstalled Ralph Loop Codex hook files and hook registrations.")
    print("Left ~/.codex/config.toml unchanged; remove codex_hooks = true manually if you no longer want hooks enabled.")


if __name__ == "__main__":
    main()
