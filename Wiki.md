# Vault Overview
이 문서는 BellFollow 볼트에서 하는 모든 작업(RAW 저장, Wiki 정리, 검색)의 단일 규칙 문서다.
옵시디언 관련 작업 시 항상 이 문서부터 읽고 시작한다. 기억으로 재구성하지 말고 매번 이 파일을 확인한다.

**중요**: 이 옵시디언 vault의 루트는 `obsidians`이고, `BellFollow`는 그 안의 하위 폴더다. 이 문서(Wiki.md)를 포함해 아래 모든 경로(Raw/, Wiki/, Archive/, Trash/)는 vault 루트 기준 상대경로이므로 앞에 `BellFollow/`를 반드시 붙여서 접근한다. `BellFollow/Wiki.md`처럼 찾을 것 — 루트에서 `Wiki.md`만 찾으면 실패한다.

# 정본과 배포본
`obsidian_brain_project` repo가 정본이다. 배포 경로는 아래 매핑표를 따른다.
repo 쪽 파일을 고치면 그 즉시 대응하는 배포 경로로 복사한다 — 습관에 맡기지 않고 이 표로 강제한다.

| repo | 배포 경로 |
|---|---|
| `CLAUDE.md` | `~/.claude/CLAUDE.md` |
| `rules/doc-folders.md` | `~/.claude/rules/doc-folders.md` |
| `commands/ingest.md` | `~/.claude/commands/ingest.md` |
| `commands/lint.md` | `~/.claude/commands/lint.md` |
| `commands/log.md` | `~/.claude/commands/log.md` |
| `commands/query.md` | `~/.claude/commands/query.md` |
| `hooks/doc_writer.py` | `~/.claude/hooks/doc_writer.py` |
| `hooks/raw_writer.py` | `~/.claude/hooks/raw_writer.py` |
| `Wiki.md` | 볼트 `BellFollow/Wiki.md` |
| `_dashboard.md` | 볼트 `BellFollow/_dashboard.md` |

(예외 없음 — `hooks/doc_writer.py`도 위 표와 같은 규칙을 따른다. repo가 정본, `~/.claude/hooks/`는 배포본이다.)

# Vault Directory Architecture
- BellFollow/Raw/: 미가공 원본 자료. 본문은 수정하지 않는다. 삭제·이동은 "RAW status 라이프사이클" 절을 따른다. status는 inbox → raw → linked 또는 inbox → raw → local 4단계로 전이한다.
- BellFollow/Wiki/<프로젝트>/: 정제된 지식. 하위 폴더 depth = 위계.
  - BellFollow/Wiki/maple-autochess/, BellFollow/Wiki/nan-hackathon/, BellFollow/Wiki/overseas-platform/, BellFollow/Wiki/wellog/, BellFollow/Wiki/career/, BellFollow/Wiki/general/, BellFollow/Wiki/meta/
  - `meta/`: 특정 프로젝트에 속하지 않는, 볼트·문서·에이전트 규칙 설계 자체에 관한 지식.
  - 새 카테고리가 필요하면 임의로 만들지 말고 사람에게 제안한다.
- BellFollow/Archive/: 당장 안 쓰지만 보존할 자료. 링크/정리 대상 아님.
- BellFollow/Trash/: 폐기 대기. 에이전트는 이동 제안만 하고 삭제는 사람이 한다.

# RAW status 라이프사이클

| status | 의미 | 부여 | 전이 트리거 | 방치 감지 | 삭제 |
|---|---|---|---|---|---|
| `inbox` | 안 읽음. 채택 판단 전 | 사람(수집 시) / 훅 자동(`raw_writer.py`) | `/ingest` [A] | `/lint` + 대시보드 | **가능** → Trash |
| `raw` | 근거로 채택. `/ingest` 대상 | 사람 / `/ingest findings` | `/ingest` [B] | `/lint` 항목7 + 대시보드 | 금지 |
| `linked` | Wiki 승격 완료. Wiki가 참조 중 | `/ingest` | 없음 (**종결**) | 불필요 | 절대 금지 |
| `local` | `/ingest`가 검토했으나 재사용 가치 없음. Wiki 노트 없음 | `/ingest` | 없음 (**종결**) | 불필요 (아래 참조) | 금지 |
| `discarded` | `/ingest` [A]에서 사람이 폐기 선택. Wiki 노트 없음 | `/ingest` [A] | 없음 (**종결**) | 불필요 | 금지(local과 동일 근거) |

`local`의 재검토는 **의도적으로 하지 않는다.** Wiki 카테고리가 늘거나 다른 프로젝트가
생겨서 예전 `local` 판정이 뒤집힐 수는 있지만, 그 빈도가 낮고 손실도 작다
(원본은 RAW에 남아 있으므로 정보가 사라진 게 아니다). 상시 감지 장치를 붙이는 비용이
얻는 것보다 크다. 필요해지면 그때 수동으로 뽑는다:

```dataview
TABLE source, project FROM "BellFollow/Raw" WHERE status = "local"
```

전이: `inbox → raw → linked`, `inbox → raw → local`, 또는 `/ingest` [A]를
거치는 `inbox → linked`, `inbox → discarded`.
inbox → linked/discarded는 RAW 파일을 Trash로 옮기지 않고 상태만 바꾼다
(원본 보존 — source_raw 참조가 끊기지 않게).

**삭제 금지의 근거는 "RAW 폴더라서"가 아니라 "근거로 채택했으니까"다.**
`inbox`는 채택 이전 단계라 보존 의무가 발생하지 않는다. 삭제 허용은 원칙 위반이 아니라
같은 원칙의 일관된 적용이다.

**이 삭제 금지는 도구 이름이 아니라 행위를 금지한다.** raw/linked/local 상태의 RAW
파일은 MCP 도구든 Bash(`rm`/`mv`)든 파일 탐색기든 어떤 수단으로도 삭제하지 않는다.
정리가 필요하면 Trash/로 옮긴다. `additionalDirectories`에 볼트 경로가 포함돼 있어
Bash로 직접 삭제가 가능하고, 실제로 지금까지 이 세션의 테스트 노트 정리도 Bash `rm`
으로 이뤄졌다 — 도구 이름을 나열해 막는 방식은 우회 경로를 못 막는다(§스키마 변경
체크리스트 ⑤ 위반).

**vault_delete는 의도적으로 허용목록에 넣지 않는다.** Trash 경유 원칙을 도구 부재로
강제하기 위함이다. 삭제가 필요하다고 판단되면 원칙부터 재검토한다.

**이 조항은 규칙이며 기술적 강제가 아니다.** `permissions.deny`는 Bash 명령어
텍스트만 매칭할 뿐 경로 단위로 스코핑할 수 없고, `find -exec rm`·PowerShell
`Remove-Item`·Python `os.remove` 등으로 쉽게 우회된다. 경로 단위 강제는 sandbox
기능으로만 가능한데 아직 도입 안 했다. 그때까지는 이 문서를 읽고 따르는 것 —
즉 사람·에이전트의 규칙 준수뿐이 유일한 방어선이다.

**테스트 데이터 예외**: 파일명이 `_TEST_`로 시작하고 frontmatter에 `project: _test`인
RAW 노트는 status와 무관하게 Trash/로 이동한다(`vault_move`). 그것을 `source_raw`로
참조하는 Wiki 노트도 같은 방식으로 Trash/로 이동한다(`vault_move`).

근거: linked/local 삭제 금지의 목적은 두 가지다 — (a) 근거로 채택한 사료의 소실 방지
(b) Wiki→RAW 링크 보호. 테스트 데이터는 (a) 채택된 적이 없고, (b) 참조하는 Wiki 노트를
함께 Trash로 옮기므로 링크도 깨지지 않는다. 따라서 이 조항은 예외가 아니라 원칙의 정확한 적용이다.

# RAW: 저장 규칙
**RAW는 미가공 원본만 담는다.** 요약, 해석, 의견은 절대 넣지 않는다.
- 원문을 편집하지 않는다. 오탈자도 그대로 둔다.
- RAW 파일을 요약으로 덮어쓰지 않는다. 요약은 별도 Wiki 노트로 만들고 링크로 연결한다.
- 출처 없는 내용은 RAW에 넣지 않는다.

**묻지 않고 저장할 것:**
- 웹에서 가져온 문서 본문 (검색 결과 목록 제외)
- PDF·문서에서 추출한 발췌문
- 근거로 인용된 외부 자료

**저장하지 않을 것:**
- 직접 생성한 코드, 설명, 요약
- 대화 자체
- 언제든 재현 가능한 것 (레포 코드, 공식 문서 목차)

**예외**: `document/FINDINGS_*.md`(원인 규명 기록)는 위 "직접 생성" 배제 규칙에도
불구하고 RAW로 승격된다. 승격 경로는 `/ingest findings <project-path>` 참조.

**예외 2**: 훅 자동 생성 세션 노트(tags: session, status: inbox) — 사람 검토
전 단계, `/ingest`로 승격 또는 폐기.

**파일 규칙:**
- 파일명: `BellFollow/Raw/YYYY-MM-DD_<slug>.md` (slug는 영문 kebab-case)
- 필수 frontmatter:
```yaml
---
source: <URL 또는 파일 경로>
captured: YYYY-MM-DD
status: inbox | raw   # 수집만 한 상태면 inbox, 근거로 채택했으면 raw
project: <git 레포명>
tags: []
---
```
- 본문은 원문 그대로. 코멘트가 꼭 필요하면 `> [!note]` 콜아웃으로 분리.
- 저장 전 같은 `source`를 가진 기존 파일이 있는지 먼저 검색한다. 있으면 새로 만들지 말고 그 사실을 보고한다.

**project 필드 채우는 규칙:**
- 훅(`raw_writer.py`)은 git remote에서 자동 추출한다(실패하면 폴더명으로 폴백) — 매 세션 사람에게 묻지 않는다.
- Claude가 직접 저장하는 경우(외부 콘텐츠 fetch)는 기존대로 `git remote -v`로 확인하고, git 레포가 아니거나 remote가 없으면 사람에게 물어본다.
- **legacy 허용**: project 필드가 없는 과거 RAW 파일(2026-08-20 재정비 이전)은 소급 보정하지 않고 그대로 둔다.

# Wiki: 노트 Frontmatter Schema
RAW의 frontmatter(source/captured/status/tags)와는 별개 스키마다. Wiki/ 하위 노트는 다음을 쓴다:

```yaml
---
title: <노트 제목>
type: moc | concept | atomic | question
up: "[[상위 노트 제목]]"
aliases: [동의어1, 동의어2]
tags: [영역/세부, 영역/세부]
status: draft | reviewed | evergreen | open
created: YYYY-MM-DD
updated: YYYY-MM-DD
source_raw: "[[RAW 노트 제목]]"
---
```
- type: moc(허브, 사람이 수동 생성만) / concept(단일 주제 정리) / atomic(사실·스니펫 하나) / question(원문에 제기됐으나 답이 안 난 사항)
- up: 위키링크는 반드시 큰따옴표로 감쌀 것 (`up: "[[Index]]"`) — 따옴표 없으면 YAML 파싱 깨짐. 최상위는 생략.
- tags: 계층형 배열만 (`[knowledge/ai, dev/mcp]`). 인라인 #tag 난립 금지.
- aliases: 동의어/축약어로 중복 노트 방지.
- status: 생성 시 draft. 사람 검토 후에만 reviewed/evergreen으로 승격 — 에이전트가 임의 승격 금지. `open`은 type: question 전용 — 미해결 상태를 뜻하며 사람이 해소 전까지 유지.
- source_raw: RAW 승격으로 만들어진 노트일 때만, 원본 RAW 노트를 역참조.
- frontmatter 수정은 vault_patch(targetType: frontmatter)로만 수행.

# 프로젝트 매핑 (git 레포명 → Wiki 카테고리)
RAW의 `project`(git 레포명)와 Wiki 폴더 카테고리는 이름 체계가 다를 수 있어 매핑표로 관리한다.
- rag-expense-guide-bot
  · Wiki 폴더: general/   (전용 폴더 없음. 기존 허브 노트가 거기 있어 따름)
  · 태그: side-project/biz-expense-bot
  (2026-08-23 확인 완료)
- (새 레포 확인되면 이 표에 추가)

매핑에 없는 새 project 값을 만나면, 기존 Wiki 카테고리 목록에서 먼저 찾아보고 없으면 사람에게 새 카테고리를 제안한다. 임의로 조용히 새 카테고리를 만들지 않는다.

# RAW → Wiki 승격 규칙
1. RAW 파일 본문은 수정하지 않는다. 이동·삭제는 "RAW status 라이프사이클" 절의
   규칙을 따른다(inbox와 테스트 데이터는 예외가 있다).
2. 승격 노트는 BellFollow/Wiki/<프로젝트>/ 아래 새로 생성하고, frontmatter `source_raw`에 원본을 `[[위키링크]]`로 남긴다.
3. 승격 판정에 따라 status를 바꾼다 — vault_patch(targetType: frontmatter)로 status
   필드만 수정하고 다른 필드는 건드리지 않는다.
   - 재사용 가능한 내용이 있어 Wiki 노트를 만들었으면 raw → linked
   - 전부 프로젝트 로컬 내용이라 Wiki 노트를 안 만들었으면 raw → local
4. 이미 status가 linked 또는 local인 RAW 파일은 중복 승격하지 않는다 —
   처리 전 상태를 먼저 확인한다. 둘 다 종결 상태다.

# MCP Tool Usage Standards
실제 도구는 Obsidian "Local REST API with MCP" 플러그인이 제공하며, 도구는 16개
존재하나 이 세션엔 아래 7개만 허용돼 있다(settings.json 허용 목록 기준). 경로
인자는 전부 `path`이고, 값은 **볼트 루트 기준 상대경로**다(절대 파일시스템 경로
아님).

- 탐색: vault_list (디렉토리 나열, path 생략 시 루트)
- 구조 파악: vault_get_document_map (heading/block/frontmatter 키 맵 — vault_read·
  vault_patch로 부분 타겟팅하기 전에 먼저 호출해 대상을 식별한다)
- 검색: search_query (JsonLogic 쿼리. 본문/태그/frontmatter 전부 조회 가능. 전문
  검색 전용 도구는 허용목록 밖이라 JsonLogic으로 흉내낸다 — 아래 판정 참조)
- 읽기: vault_read (path, 선택적으로 targetType/target으로 heading·block·
  frontmatter 부분만 읽기 가능 — 전체 대신 우선 고려)
- 생성/덮어쓰기: vault_write (path, content — 파일 전체를 새로 쓰거나 덮어씀)
- 부분 수정 전부(heading/block/frontmatter, replace/prepend/append/delete):
  vault_patch 하나로 통합. targetType으로 대상 종류를, operation으로 동작을
  지정한다. frontmatter 수정도 이 도구다 — 별도 frontmatter 전용 도구는 없다.
- 이동/정리: vault_move (path → destination). **RAW 파일은 삭제하지 않는다 —
  정리는 Trash/ 이동이며 그 수단이 이 도구다.** vault_delete는 의도적으로 허용목록 밖이다(위 "RAW status
  라이프사이클" 절 참조). RAW 노트 삭제 금지는 도구가 아니라 행위 기준이므로
  Bash 등 다른 수단으로도 마찬가지로 하지 않는다.

**허용목록 밖이라 못 쓰는 것**: vault_append(끝에 추가 — vault_patch의
operation:append로 대체), vault_delete(삭제 — 이 세션 권한으로 애초에 불가),
vault_copy, tag_list, search_simple, active_file_get_path,
command_list/command_execute, open_file.

**tag_list 판정**: 이 문서·ingest.md·lint.md·query.md 어디도 실제로 태그 목록
조회를 절차에 쓰지 않는다 — 지금까지 나열만 되고 안 쓰이던 항목이다. 허용목록
추가 불필요.

**search_simple 판정**: query.md의 "제목·태그·본문 검색"은 search_query의
JsonLogic으로 커버된다(예: `{"in": ["키워드", {"var": "content"}]}`로 본문
부분일치). 순위·형태소 분석은 없지만 지금 볼트 규모에서는 충분하다고 판단 —
허용목록 추가 불필요.

# Wikilink & Tag Creation Guidelines
1. 동일 프로젝트/고유명사 언급 시 [[정확한 노트 제목]]으로 링크.
2. 동일 기술스택/도구 3회 이상 언급 시 링크.
3. 안 맞으면 억지로 링크하지 않는다.
4. 위키링크는 완전 문자열 일치만 작동 (의미 기반 아님).
5. 느슨한 주제 묶음은 링크 대신 #태그(tags 배열)로.
6. 애매하면 #관련후보 태그만, 링크는 보류 → 다음 /lint에서 검토.
7. moc 노트는 에이전트가 새로 만들지 않는다 — 기존 moc에 링크 추가만.

# Error Prevention & Validation Protocol
1. 수정 전 vault_get_document_map으로 기존 구조 확인 후 진행.
2. 기존 노트 전체 덮어쓰기 지양, 부분 수정 도구 우선.
3. 위키링크 포함 frontmatter 값은 항상 큰따옴표.
4. 링크 대상 존재 불확실하면 걸지 말고 #관련후보로 보류.
5. 애매한 카테고리/신규 카테고리/moc 승격 판단은 자동 처리하지 말고 사람에게 확인.
6. 작업 종료 시 처리 파일 목록, 생성/수정 노트 경로, RAW status 변경 내역을 요약 보고한다.

# 임계값 정본

```
inbox 방치   : captured 기준 30일
raw 방치     : captured 기준 30일
open 방치    : updated 기준 60일
```

**이 숫자는 여기에만 둔다.** `/lint`, `_dashboard.md`, 그 외 어떤 문서도
숫자를 복제하지 말고 이 절을 참조한다.

# 스키마 변경 체크리스트

```
status / type 값을 새로 추가할 때 아래 5개에 전부 답한 뒤 추가한다.
하나라도 못 답하면 그 값은 아직 추가하지 않는다.

① 누가 이 값을 부여하나 — 사람 / 에이전트 / 파이프라인
② 다음 전이는 무엇이 트리거하나 — 명령어? 경과일수? 사람 판단?
③ 종결 상태인가 — 아니라면 방치 감지 장치는 무엇인가
④ 임계값이 있다면 정본은 어디에 한 벌만 두는가
⑤ 이 규칙이 막으려는 실패가 무엇이고, 조건이 그 실패와 직접 연결되는가
   — 우연히 같이 나타나는 신호를 조건으로 쓰지 말 것
```

⑤가 필요한 이유: "cwd가 git repo인가"(실제 원인은 작업 대상 불일치),
"FINDINGS 파일이 있는가"(실제 원인은 볼트 작업 이력) 둘 다 상관관계를 조건으로 써서
사고를 못 막는 가드를 만들 뻔했다.
