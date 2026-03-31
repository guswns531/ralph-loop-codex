# Ralph Loop Codex

Ralph Loop Codex is a hook-backed Codex skill that implements a Ralph-style iterative development loop inside a single Codex session.

Run one command once, keep the task prompt frozen, and let Codex continue iterating on the same goal until the completion condition is genuinely true or a hard stop is reached.

## Status

This repository packages:

- a Codex skill
- the Ralph hook implementations
- an installer
- an uninstaller

The folder is self-contained. You can move or clone it anywhere and install from the folder itself.

## Why This Exists

The original Ralph idea is simple:

> "Ralph is a Bash loop"

The core mechanism is to keep feeding the same task back to the agent while the workspace changes underneath it. Tests fail, files change, logs accumulate, and each next pass uses the repo state as feedback.

This project adapts that model to Codex using official Codex hooks.

## Prior Work And Attribution

This project builds on and is inspired by:

- Anthropic's Claude Code Ralph Wiggum plugin: https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum
- fstandhartinger/ralph-wiggum: https://github.com/fstandhartinger/ralph-wiggum

The Codex implementation here is a separate adaptation built around Codex hooks, project-local state, and a self-contained installer.

## How It Works

The implementation uses two Codex hooks:

- `UserPromptSubmit`
- `Stop`

High-level flow:

1. You start a loop with `/ralph-loop "TASK" ...` or `$ralph-loop-codex "TASK" ...`
2. `UserPromptSubmit` parses the command and writes `.codex/ralph-loop.local.md`
3. Codex works on the task normally
4. When Codex tries to stop, the `Stop` hook checks completion
5. If the task is not complete, `Stop` returns `decision: "block"` and re-injects the same frozen prompt
6. The repo state persists between passes, so each iteration can learn from previous work
7. The loop ends only when the completion promise matches or `--max-iterations` is reached

The self-reference is not "feeding the assistant's output back into itself." It is "reusing the same task while the files created by previous attempts remain in the workspace."

## Files

- `SKILL.md`: skill instructions for Codex
- `hooks/ralph_loop_common.py`: shared state and parsing helpers
- `hooks/ralph_loop_user_prompt_submit.py`: loop activation and cancellation
- `hooks/ralph_loop_stop.py`: completion detection and continuation
- `scripts/install.py`: installs hooks into `~/.codex`
- `scripts/uninstall.py`: removes the Ralph-specific hook files and registrations
- `references/`: prompt and iteration templates

## Installation

From this directory:

```bash
python3 scripts/install.py
```

This script:

- copies the bundled hook files into `~/.codex/hooks`
- updates `~/.codex/hooks.json`
- ensures `codex_hooks = true` is set in `~/.codex/config.toml`

To verify installation:

```bash
python3 scripts/install.py --check
```

To uninstall:

```bash
python3 scripts/uninstall.py
```

## Usage

Start a loop:

```text
/ralph-loop "Implement feature X and make all tests pass." --completion-promise "DONE" --max-iterations 12
```

Or:

```text
$ralph-loop-codex "Implement feature X and make all tests pass." --completion-promise "DONE" --max-iterations 12
```

Cancel a loop:

```text
/cancel-ralph
```

## State File

The loop stores project-local state in:

```text
.codex/ralph-loop.local.md
```

Example shape:

```md
---
active: true
iteration: 1
session_id: ...
max_iterations: 12
completion_promise: "DONE"
started_at: "2026-03-31T06:50:30Z"
---

Implement feature X and make all tests pass.
```

The frontmatter stores loop state. The markdown body stores the frozen task prompt that gets replayed on each incomplete stop.

## Prompting Guidance

Ralph works best when the task is:

- concrete
- verifiable
- iterative
- narrow enough to converge

Good prompt traits:

- clear done conditions
- real verification steps
- explicit hard stop
- explicit promise output when complete

Example:

```text
$ralph-loop-codex "Implement feature X following TDD:
1. write failing tests
2. implement the feature
3. run tests
4. if any fail, debug and fix
5. repeat until all green
Output <promise>DONE</promise> when complete." --completion-promise "DONE" --max-iterations 12
```

## Good Fits

- failing tests or builds with a plausible path to green
- feature work with crisp acceptance criteria
- refactors backed by tests
- parity or migration work with differential verification
- greenfield work where you want Codex to keep pushing in the same session

## Bad Fits

- vague product ideation
- design-heavy work requiring human taste
- tasks with no stable success criteria
- one-shot factual questions
- production incidents where blind iteration is riskier than diagnosis

## Safety Notes

This tool gives Codex a stronger retry loop. It does not make the task safer by itself.

Recommended:

- always set `--max-iterations`
- use a real completion promise
- prefer isolated or disposable repos for experimentation
- review changes before merging

## License

MIT. See [LICENSE](LICENSE).
