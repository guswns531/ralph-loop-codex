---
name: ralph-loop-codex
description: Use when the user wants Codex to run a Ralph-style iterative development loop with a frozen prompt, explicit stop conditions, and hook-backed continuation until the completion condition is genuinely true.
---

# Ralph Loop Codex

Implementation of the Ralph Wiggum technique for iterative, self-referential development loops in Codex.

Use this for well-defined coding tasks with clear success criteria and real verification signals.

Do not use this for one-shot questions, ambiguous design work, or tasks without a credible way to tell whether progress is real.

## Install

This skill folder is self-contained. To install or refresh the required hooks from the skill directory itself, run:

```bash
python3 scripts/install.py
```

That script copies the bundled hook files into `~/.codex/hooks`, updates `~/.codex/hooks.json`, and enables `codex_hooks = true` in `~/.codex/config.toml`.

To check whether installation appears complete:

```bash
python3 scripts/install.py --check
```

To uninstall the Ralph-specific hook files and hook registrations:

```bash
python3 scripts/uninstall.py
```

Before using this skill, verify installation. If the hooks are not installed, tell the user to run `python3 scripts/install.py` from the skill folder before trying `/ralph-loop` or `$ralph-loop-codex`.

## Activation

Start a loop in your current session by sending one of these as the user prompt:

```text
/ralph-loop "TASK" --completion-promise "DONE" --max-iterations 12
```

```text
$ralph-loop-codex "TASK" --completion-promise "DONE" --max-iterations 12
```

Cancel with:

```text
/cancel-ralph
```

The loop happens inside your current session. The Stop hook blocks normal stopping and feeds the SAME PROMPT back until completion.

## Core Rule

Freeze the task statement. Improve the workspace, not the prompt.

The Ralph idea is not "say something new each round." It is "keep attacking the same goal while the repo state changes underneath you." Each pass should learn from files, diffs, test failures, logs, and previous attempts.

This Codex version uses hooks:

- `UserPromptSubmit` parses the Ralph command and writes `.codex/ralph-loop.local.md`
- `Stop` checks whether the loop is genuinely complete
- if not complete, `Stop` returns `decision: "block"` and re-injects the same prompt text

This creates the self-referential loop:

- the prompt stays fixed
- previous work persists in files
- each iteration sees the changed repo state
- Codex keeps iterating until the promise is genuinely true or the hard stop is reached

## Default Workflow

1. Freeze the loop prompt.
Turn the user's request into a short working brief with scope, constraints, and a concrete done condition. Use [loop-prompt-template.md](references/loop-prompt-template.md) when the task is underspecified.

2. Define two stop conditions.
Set:
- a semantic stop: what must be true to call the task done
- a hard stop: max iterations, time box, or a blocker-report threshold

Do not start deep loop work without a hard stop on open-ended tasks.

3. Establish verification first.
Prefer tests, repro steps, linters, builds, contract checks, or executable fixtures. If no automatic check exists, create the smallest reliable one you can.

4. Iterate in narrow passes.
For each pass:
- inspect the current state
- choose the next smallest change that should reduce the failure surface
- make the change
- run the relevant verification
- use the result to choose the next pass

5. Claim completion only when true.
If a completion promise is set, only output `<promise>TEXT</promise>` when that statement is completely and unequivocally true. If the hard stop is reached first, stop cleanly and report blockers rather than faking success.

## Prompt Writing

Good Ralph prompts have:

- clear completion criteria
- automatic verification where possible
- incremental, checkable goals
- a hard stop or escape hatch

Prefer:

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
- refactors that can be checked by existing tests
- parity or migration work with differential verification
- greenfield tasks where you want Codex to keep pushing in the same session

## Bad Fits

- product or design decisions requiring human taste
- tasks with no stable success criteria
- one-shot factual questions
- production incidents where blind iteration is riskier than diagnosis

## Notes

- `--max-iterations` defaults to unlimited if omitted
- `--completion-promise` is optional, but strongly recommended
- use `/cancel-ralph` to cancel an active loop

## References

- prompt scaffolding: [loop-prompt-template.md](references/loop-prompt-template.md)
- iteration notes: [iteration-ledger-template.md](references/iteration-ledger-template.md)
