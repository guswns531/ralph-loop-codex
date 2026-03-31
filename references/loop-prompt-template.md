# Loop Prompt Template

Use this template when the task needs a Ralph-style working brief.

```text
Task:
<one short paragraph describing the fixed goal>

Constraints:
- <repo or environment constraints>
- <files or boundaries to respect>
- <style or safety requirements>

Done when:
- <observable condition 1>
- <observable condition 2>
- <tests/build/repro that must pass>

Hard stop:
- max iterations: <n>
- if still blocked: summarize what failed, what was tried, and the smallest next step
```
