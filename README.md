# obsidian_brain_project

옵시디언(Obsidian) 볼트를 Claude Code / Gemini CLI(Antigravity) 같은 터미널 AI 에이전트가 MCP로 직접 읽고 정리하게 만드는 설정 템플릿. 카파시(Karpathy)의 LLM Wiki 패턴(원본 RAW → 정제 Wiki)을 옵시디언 위에 구현한 것.

실제 볼트 데이터(노트 내용)는 포함하지 않는다. 여기 있는 건 **규칙 파일과 커맨드 파일**뿐이다.

## 만든 이유
요즘 claude code나 gemini cli 같은거에 옵시디언 붙이기가 유행이던데 뒤늦게 따라 할라 보니까 좀 귀찮은 작업이고, 왠지 md 파일들이 자꾸 바뀔거같아서, 이후 구글 드라이브 연동이 되어있지만, 로컬로 또 설정할지도 몰라서 게시함

## 구조

```
CLAUDE.md            전역 규칙 (코딩 원칙 + 옵시디언 트리거 포인터 + 출력 언어)
Wiki.md               옵시디언 관련 전체 규칙 (RAW 라이프사이클, Wiki 승격, frontmatter,
                      MCP 도구 표준, 임계값 정본, 정본/배포 매핑표) — 볼트 루트에 배치
_dashboard.md         볼트 상태판 (Dataview) — 볼트 루트에 배치
commands/
  ingest.md           RAW → Wiki 승격 슬래시 커맨드
  query.md             Wiki 검색·질문답변 슬래시 커맨드
  lint.md               Wiki/RAW 상태 진단 슬래시 커맨드
  log.md                DEV_LOG.md append 슬래시 커맨드
rules/
  doc-folders.md      document/·docs/ 폴더 컨벤션 (경로 기반 lazy-load)
```

`document/`는 이 저장소를 다루면서 생긴 개인 작업 기록(FINDINGS 등)이 쌓이는 곳이라
`.gitignore`로 제외돼 있다 — 템플릿 범위가 아니다.

## 사전 준비

1. 옵시디언 설치, 볼트 열기
2. 커뮤니티 플러그인 설치: **Local REST API with MCP** (Adam Coddington), **Smart Connections** (선택, 의미 기반 검색용)
3. Local REST API 플러그인에서 API 키·포트 확인 (기본 HTTPS 27124)

## 설치

```bash
# 전역 규칙
cp CLAUDE.md ~/.claude/CLAUDE.md
cp -r commands ~/.claude/commands
cp -r rules ~/.claude/rules

# 볼트 루트
cp Wiki.md <옵시디언_볼트_경로>/Wiki.md
cp _dashboard.md <옵시디언_볼트_경로>/_dashboard.md
mkdir -p <옵시디언_볼트_경로>/Trash
```

`CLAUDE.md`의 `Vault path`를 실제 볼트 경로로 바꿀 것. `Wiki.md`·`_dashboard.md`·
`commands/*.md` 안의 `BellFollow`는 예시 볼트 이름이므로 본인 볼트 이름으로
전체 치환할 것(경로 기준이라 이름이 안 맞으면 동작하지 않는다).

수정한 뒤엔 repo가 정본, 위 배포 경로들이 사본이 된다 — 어느 쪽을 고치든
`Wiki.md`의 "정본과 배포본" 매핑표를 따라 반대쪽에도 반영할 것.

### Claude Code MCP 등록

```bash
claude mcp add obsidian --scope user --transport http https://127.0.0.1:27124/mcp/ \
  --header "Authorization: Bearer <API_KEY>"
```

### 안티그래비티(Gemini CLI) MCP 등록

`~/.gemini/config/mcp_config.json`:
```jsonc
{
  "mcpServers": {
    "obsidian-mcp": {
      "serverUrl": "https://127.0.0.1:27124/mcp/",
      "accessToken": "<API_KEY>"
    }
  }
}
```
서버 이름은 언더스코어(`_`) 대신 하이픈(`-`) 사용 — Gemini CLI가 언더스코어를 FQN 구분자로 오인식함.

## 핵심 원칙

- **RAW status는 4단계**: `inbox`(안 읽음) → `raw`(근거로 채택) → `linked`(Wiki 승격) 또는 `local`(재사용 가치 없어 Wiki 노트 없이 종결). 전이·삭제 규칙은 상태별로 다르다 — `Wiki.md`의 "RAW status 라이프사이클" 참조.
- **삭제 금지는 도구가 아니라 행위 기준이다.** `raw`/`linked`/`local` 상태 RAW는 MCP 도구든 셸 명령이든 파일 탐색기든 어떤 수단으로도 삭제하지 않는다 — 정리는 `Trash/` 이동뿐. 단, 이건 문서화된 규칙이지 OS 레벨 강제가 아니다(권한 시스템으로 경로 단위 차단은 안 됨).
- **moc(허브) 노트는 사람만 만든다.** 에이전트는 기존 moc에 링크를 추가하는 것까지만 한다.
- **새 Wiki 카테고리는 임의로 만들지 않는다.** 사람에게 제안하고 확인받는다.
- **RAW의 `project` 필드는 git 레포명 기준.** 로컬 폴더명은 신뢰하지 않는다. git 레포가 아니거나 remote가 없으면 조용히 넘어가지 않고 사람에게 물어본다.
- **임계값·MCP 도구명은 `Wiki.md` 한 곳이 정본.** 다른 문서는 참조만 하고 숫자·도구명을 복제하지 않는다.
- 규칙 파일(Wiki.md)은 매번 다시 읽는다 — 기억으로 재구성하지 않는다.

## 트러블슈팅 (실제로 겪은 문제들)

- **`claude mcp get obsidian`이 `Failed to connect`** — Node.js는 시스템 인증서 저장소를 신뢰하지 않는다. self-signed 인증서를 윈도우 "신뢰할 수 있는 루트 인증 기관"에 등록해도 Node 기준으론 안 먹힌다. `$env:NODE_TLS_REJECT_UNAUTHORIZED = "0"`을 PowerShell 프로필(`$PROFILE`)에 등록해 우회했다. (로컬호스트 한정 트레이드오프이며, 다른 원격 서버 접속 시 보안 위험이 있음을 인지할 것.)
- **연결은 Connected인데 도구가 하나도 안 잡힘** — `claude mcp remove` → `claude mcp add`로 재등록하면 캐시된 스키마가 초기화되며 해결됐다.
- **Gemini CLI(안티그래비티)에서 "no connector can handle spec" 에러** — 필드명이 `httpUrl`/`headers.Authorization`이 아니라 `serverUrl`/`accessToken`이어야 함 (Supabase 커넥터와 동일 스키마).
- **HTTP 서버 전환 시 Unauthorized** — 이 플러그인은 비암호화(HTTP) 엔드포인트에서 Bearer 인증이 정상 작동하지 않는 것으로 보임. HTTPS + 인증서 신뢰 등록이 정석 경로.
- **자연어 기반 "규칙 파일 먼저 읽어라" 참조는 세션이 길어지면 놓칠 수 있음(Instruction Drift)** — 경로 기반 트리거(`.claude/rules/*.md` + `paths:` frontmatter)가 확실한 지연 로딩 방식이며, 웹 콘텐츠 저장처럼 경로가 아닌 트리거는 CLAUDE.md에 조건을 명시적으로 나열해 인식 실패 확률을 낮췄다.
