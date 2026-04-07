# Ralph Loop Codex

[English](README.md) | 한국어

Ralph Loop Codex는 Codex hooks를 이용해 Ralph 스타일의 반복 개발 루프를 단일 Codex 세션 안에서 실행하는 스킬입니다.

한 번 명령을 시작하면 작업 프롬프트를 고정한 채로, 완료 조건이 진짜로 충족되거나 하드 스톱에 도달할 때까지 같은 목표를 계속 반복합니다.

## 개요

이 저장소에는 다음이 포함되어 있습니다.

- Codex skill
- Ralph hook 구현
- 설치 스크립트
- 제거 스크립트

이 폴더는 self-contained 형태입니다. 다른 위치로 옮기거나 별도 저장소로 clone한 뒤, 폴더 안에서 바로 설치할 수 있습니다.

## 참고 및 Attribution

이 프로젝트는 다음 작업들에서 영감을 받고 영향을 받았습니다.

- Anthropic Claude Code Ralph Wiggum plugin: https://github.com/anthropics/claude-code/tree/main/plugins/ralph-wiggum
- fstandhartinger/ralph-wiggum: https://github.com/fstandhartinger/ralph-wiggum

현재 구현은 Codex hooks 기반으로 다시 구성한 adaptation입니다.

Codex hooks 공식 문서:

- https://developers.openai.com/codex/hooks

## 설치

이 디렉터리에서 실행:

```bash
python3 scripts/install.py
```

이 스크립트는 다음을 수행합니다.

- `hooks/*.py`를 `~/.codex/hooks`로 복사
- `~/.codex/hooks.json`에 Ralph용 hook 등록
- `~/.codex/config.toml`에 `codex_hooks = true` 보장

설치 확인:

```bash
python3 scripts/install.py --check
```

제거:

```bash
python3 scripts/uninstall.py
```

## 사용법

초안 생성:

일부 Codex 클라이언트에서는 `/...` 형태를 내장 slash command로 처리할 수 있으므로, 실제 사용은 `$...` 형태를 권장합니다.

```text
/ralph-loop "Implement feature X and make all tests pass." --completion-promise "DONE" --max-iterations 12
```

또는:

```text
$ralph-loop "Implement feature X and make all tests pass." --completion-promise "DONE" --max-iterations 12
```

또는:

```text
$ralph-loop-codex "Implement feature X and make all tests pass." --completion-promise "DONE" --max-iterations 12
```

초안 승인 후 루프 시작:

```text
$ralph-approve
```

루프 취소:

```text
$cancel-ralph
```

## 동작 방식

구현은 두 개의 Codex hook을 사용합니다.

- `UserPromptSubmit`
- `Stop`

흐름은 이렇습니다.

1. 사용자가 `/ralph-loop ...` 또는 `$ralph-loop-codex ...`를 보냅니다.
2. `UserPromptSubmit`가 명령을 파싱하고 `cwd/.codex/ralph-loop/<session_id>.md` 초안 상태 파일과 `cwd/.codex/ralph-loop/<session_id>.tsv` 작업 추적 파일을 만듭니다.
3. assistant가 TSV 기준 완료를 목표로 하는 작업 brief를 구체화하고 사용자 승인 요청을 합니다.
4. 사용자가 `/ralph-approve`를 보내면 같은 파일이 active 상태로 전환됩니다.
5. Codex가 작업을 진행합니다.
6. Codex가 멈추려 할 때 `Stop` hook이 completion 여부를 검사합니다.
7. 아직 미완료면 `decision: "block"`과 함께 같은 프롬프트를 다시 continuation prompt로 넣습니다.
8. 완료 promise가 정확히 맞거나 `--max-iterations`에 도달하면 루프가 끝납니다.

핵심은 assistant 출력을 그대로 다시 넣는 것이 아니라, 같은 작업 프롬프트를 유지하면서 이전 반복에서 바뀐 파일과 테스트 결과를 다음 반복의 입력 맥락으로 사용하는 것입니다.

## 상태 파일

세션 로컬 상태는 현재 `cwd` 아래 파일에 저장됩니다.

```text
.codex/ralph-loop/<session_id>.md
.codex/ralph-loop/<session_id>.tsv
```

예시:

```md
---
status: active
iteration: 1
session_id: ...
max_iterations: 12
completion_promise: "DONE"
started_at: "2026-03-31T06:50:30Z"
---

Implement feature X and make all tests pass.
```

frontmatter에는 loop 상태가 들어가고, 본문에는 승인 후 매 반복마다 다시 주입할 고정 프롬프트가 들어갑니다. TSV는 반복 중 해야 할 일을 추적하는 기준 파일입니다.

## 어떤 작업에 좋은가

- 테스트나 빌드 실패를 반복적으로 줄여나가는 작업
- 완료 기준이 분명한 기능 구현
- 테스트가 있는 리팩터링
- parity / migration처럼 검증 기반으로 밀어붙일 수 있는 작업

## 어떤 작업에는 맞지 않는가

- 제품 방향이나 디자인 감각이 중요한 작업
- 성공 기준이 모호한 작업
- 단발성 질문
- 무작정 반복하는 것이 더 위험한 프로덕션 장애 대응

## 주의사항

권장:

- 항상 `--max-iterations`를 설정하세요
- 가능하면 `--completion-promise`도 설정하세요
- 실험은 격리된 저장소에서 먼저 해보세요
- 변경사항은 직접 검토하세요

## 라이선스

MIT. 자세한 내용은 [LICENSE](LICENSE)를 참고하세요.
