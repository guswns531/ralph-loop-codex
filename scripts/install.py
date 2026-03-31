#!/usr/bin/env python3

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def ensure_codex_hooks_enabled(config_path: Path) -> None:
    if config_path.exists():
        text = config_path.read_text()
    else:
        text = ""

    if "codex_hooks =" in text:
        lines = []
        for line in text.splitlines():
            if line.strip().startswith("codex_hooks ="):
                lines.append("codex_hooks = true")
            else:
                lines.append(line)
        new_text = "\n".join(lines).rstrip() + "\n"
    elif "[features]" in text:
        new_text = text.replace("[features]\n", "[features]\ncodex_hooks = true\n", 1)
    elif text.strip():
        new_text = text.rstrip() + "\n\n[features]\ncodex_hooks = true\n"
    else:
        new_text = "[features]\ncodex_hooks = true\n"

    config_path.write_text(new_text)


def config_has_codex_hooks_enabled(config_path: Path) -> bool:
    if not config_path.exists():
        return False
    for line in config_path.read_text().splitlines():
        if line.strip().startswith("codex_hooks ="):
            return line.split("=", 1)[1].strip().lower() == "true"
    return False


def install_hooks_json(hooks_json_path: Path) -> None:
    if hooks_json_path.exists():
        data = json.loads(hooks_json_path.read_text())
    else:
        data = {}

    hooks = data.setdefault("hooks", {})
    hooks["UserPromptSubmit"] = [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": "python3 ~/.codex/hooks/ralph_loop_user_prompt_submit.py",
                    "statusMessage": "Preparing Ralph loop",
                }
            ]
        }
    ]
    hooks["Stop"] = [
        {
            "hooks": [
                {
                    "type": "command",
                    "command": "python3 ~/.codex/hooks/ralph_loop_stop.py",
                    "statusMessage": "Checking Ralph loop",
                    "timeout": 30,
                }
            ]
        }
    ]

    hooks_json_path.write_text(json.dumps(data, indent=2) + "\n")


def hooks_json_is_installed(hooks_json_path: Path) -> bool:
    if not hooks_json_path.exists():
        return False
    try:
        data = json.loads(hooks_json_path.read_text())
    except Exception:
        return False
    hooks = data.get("hooks", {})
    user_hooks = hooks.get("UserPromptSubmit", [])
    stop_hooks = hooks.get("Stop", [])
    user_ok = any(
        item.get("command") == "python3 ~/.codex/hooks/ralph_loop_user_prompt_submit.py"
        for group in user_hooks
        for item in group.get("hooks", [])
    )
    stop_ok = any(
        item.get("command") == "python3 ~/.codex/hooks/ralph_loop_stop.py"
        for group in stop_hooks
        for item in group.get("hooks", [])
    )
    return user_ok and stop_ok


def backup_if_exists(path: Path) -> None:
    if not path.exists():
        return
    backup_path = path.with_name(f"{path.name}.bak-{utc_stamp()}")
    shutil.copy2(path, backup_path)


def hooks_files_installed(hooks_dst: Path) -> bool:
    return all(
        (hooks_dst / filename).exists()
        for filename in [
            "ralph_loop_common.py",
            "ralph_loop_user_prompt_submit.py",
            "ralph_loop_stop.py",
        ]
    )


def is_installed(codex_home: Path) -> bool:
    hooks_dst = codex_home / "hooks"
    hooks_json_path = codex_home / "hooks.json"
    config_path = codex_home / "config.toml"
    return (
        hooks_files_installed(hooks_dst)
        and hooks_json_is_installed(hooks_json_path)
        and config_has_codex_hooks_enabled(config_path)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Install Ralph Loop Codex hooks from this skill folder.")
    parser.add_argument("--check", action="store_true", help="Only check whether the hooks appear installed.")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parent.parent
    hooks_src = skill_dir / "hooks"

    codex_home = Path.home() / ".codex"
    hooks_dst = codex_home / "hooks"
    hooks_json_path = codex_home / "hooks.json"
    config_path = codex_home / "config.toml"

    if args.check:
        if is_installed(codex_home):
            print("Ralph Loop Codex hooks appear installed.")
            sys.exit(0)
        print("Ralph Loop Codex hooks are not fully installed.")
        print(f"Run: python3 {skill_dir / 'scripts' / 'install.py'}")
        sys.exit(1)

    hooks_dst.mkdir(parents=True, exist_ok=True)

    for filename in [
        "ralph_loop_common.py",
        "ralph_loop_user_prompt_submit.py",
        "ralph_loop_stop.py",
    ]:
        shutil.copy2(hooks_src / filename, hooks_dst / filename)

    backup_if_exists(hooks_json_path)
    backup_if_exists(config_path)

    install_hooks_json(hooks_json_path)
    ensure_codex_hooks_enabled(config_path)

    print("Installed Ralph Loop Codex hooks.")
    print(f"Skill dir: {skill_dir}")
    print(f"Hooks dir: {hooks_dst}")
    print(f"Hooks config: {hooks_json_path}")
    print(f"Codex config: {config_path}")


if __name__ == "__main__":
    main()
