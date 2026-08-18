# Vault Overview
이 문서는 BellFollow 볼트에서 하는 모든 작업(RAW 저장, Wiki 정리, 검색)의 단일 규칙 문서다.
옵시디언 관련 작업 시 항상 이 문서부터 읽고 시작한다. 기억으로 재구성하지 말고 매번 이 파일을 확인한다.

**중요**: 이 옵시디언 vault의 루트는 `obsidians`이고, `BellFollow`는 그 안의 하위 폴더다. 이 문서(Wiki.md)를 포함해 아래 모든 경로(RAW/, Wiki/, Archive/)는 vault 루트 기준 상대경로이므로 앞에 `BellFollow/`를 반드시 붙여서 접근한다. `BellFollow/Wiki.md`처럼 찾을 것 — 루트에서 `Wiki.md`만 찾으면 실패한다.

# Vault Directory Architecture
- BellFollow/RAW/: 미가공 원본 자료. 원본은 절대 삭제·이동·수정하지 않는다. frontmatter status가 raw → linked로만 바뀐다.
- BellFollow/Wiki/<프로젝트>/: 정제된 지식. 하위 폴더 depth = 위계.
  - BellFollow/Wiki/maple-autochess/, BellFollow/Wiki/nan-hackathon/, BellFollow/Wiki/overseas-platform/, BellFollow/Wiki/wellog/, BellFollow/Wiki/career/, BellFollow/Wiki/general/
  - 새 카테고리가 필요하면 임의로 만들지 말고 사람에게 제안한다.
- BellFollow/Archive/: 당장 안 쓰지만 보존할 자료. 링크/정리 대상 아님.

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

**파일 규칙:**
- 파일명: `BellFollow/RAW/YYYY-MM-DD_<slug>.md` (slug는 영문 kebab-case)
- 필수 frontmatter:
```yaml
---
source: <URL 또는 파일 경로>
captured: YYYY-MM-DD
status: raw
project: <git 레포명>
tags: []
---
```
- 본문은 원문 그대로. 코멘트가 꼭 필요하면 `> [!note]` 콜아웃으로 분리.
- 저장 전 같은 `source`를 가진 기존 파일이 있는지 먼저 검색한다. 있으면 새로 만들지 말고 그 사실을 보고한다.

**project 필드 채우는 규칙:**
- 로컬 폴더명이 아니라 실제 git 레포명을 쓴다 — `git remote -v` 또는 `git config --get remote.origin.url`로 확인한다. 로컬 폴더명은 사람마다 다르게 지을 수 있어 신뢰하지 않는다.
- 세션이 git 레포가 아니거나(초기화 안 됨) 원격(remote)이 등록 안 되어 있으면, project를 임의로 비우거나 추측하지 말고 사람에게 물어본다 — "이 프로젝트는 git 레포로 등록 안 된 것 같은데, project 값을 뭘로 채울지 / 지금 git 등록부터 할지" 확인한다.
- 확인 후에도 값이 정해지지 않으면 그 사실을 명시적으로 보고하고 다음 단계로 진행한다.

# Wiki: 노트 Frontmatter Schema
RAW의 frontmatter(source/captured/status/tags)와는 별개 스키마다. Wiki/ 하위 노트는 다음을 쓴다:

```yaml
---
title: <노트 제목>
type: moc | concept | atomic
up: "[[상위 노트 제목]]"
aliases: [동의어1, 동의어2]
tags: [영역/세부, 영역/세부]
status: draft | reviewed | evergreen
created: YYYY-MM-DD
updated: YYYY-MM-DD
source_raw: "[[RAW 노트 제목]]"
---
```
- type: moc(허브, 사람이 수동 생성만) / concept(단일 주제 정리) / atomic(사실·스니펫 하나)
- up: 위키링크는 반드시 큰따옴표로 감쌀 것 (`up: "[[Index]]"`) — 따옴표 없으면 YAML 파싱 깨짐. 최상위는 생략.
- tags: 계층형 배열만 (`[knowledge/ai, dev/mcp]`). 인라인 #tag 난립 금지.
- aliases: 동의어/축약어로 중복 노트 방지.
- status: 생성 시 draft. 사람 검토 후에만 reviewed/evergreen으로 승격 — 에이전트가 임의 승격 금지.
- source_raw: RAW 승격으로 만들어진 노트일 때만, 원본 RAW 노트를 역참조.
- frontmatter 수정은 obsidian_manage_frontmatter로만 수행.

# 프로젝트 매핑 (git 레포명 → Wiki 카테고리)
RAW의 `project`(git 레포명)와 Wiki 폴더 카테고리는 이름 체계가 다를 수 있어 매핑표로 관리한다.
- rag-expense-guide-bot → side-project/biz-expense-bot (이미 사용 중인 태그 슬러그, Wiki 폴더 위치는 재확인 필요)
- (새 레포 확인되면 이 표에 추가)

매핑에 없는 새 project 값을 만나면, 기존 Wiki 카테고리 목록에서 먼저 찾아보고 없으면 사람에게 새 카테고리를 제안한다. 임의로 조용히 새 카테고리를 만들지 않는다.

# RAW → Wiki 승격 규칙
1. RAW 파일 원본은 그대로 둔다 — 이동, 삭제, 덮어쓰기 금지.
2. 승격 노트는 BellFollow/Wiki/<프로젝트>/ 아래 새로 생성하고, frontmatter `source_raw`에 원본을 `[[위키링크]]`로 남긴다.
3. 승격이 끝나면 obsidian_manage_frontmatter로 RAW 노트의 `status`만 raw → linked로 바꾼다. 다른 필드는 건드리지 않는다.
4. 이미 status: linked인 RAW 파일은 중복 승격하지 않는다 — 처리 전 상태를 먼저 확인한다.

# MCP Tool Usage Standards
- 탐색/목록: obsidian_list_notes, obsidian_list_tags
- 검색: obsidian_search_notes (텍스트/Dataview/JSONLogic 중 질의에 맞는 모드)
- 읽기: obsidian_get_note (구조 파악 시 format: document-map 우선)
- 생성: obsidian_write_note
- 부분 수정: obsidian_patch_note 우선 → obsidian_append_to_note → obsidian_replace_in_note
- frontmatter만: obsidian_manage_frontmatter
- 태그만: obsidian_manage_tags
- 삭제: obsidian_delete_note — RAW 노트에는 절대 사용하지 않는다. Wiki 노트도 실행 전 반드시 사람 확인.

# Wikilink & Tag Creation Guidelines
1. 동일 프로젝트/고유명사 언급 시 [[정확한 노트 제목]]으로 링크.
2. 동일 기술스택/도구 3회 이상 언급 시 링크.
3. 안 맞으면 억지로 링크하지 않는다.
4. 위키링크는 완전 문자열 일치만 작동 (의미 기반 아님).
5. 느슨한 주제 묶음은 링크 대신 #태그(tags 배열)로.
6. 애매하면 #관련후보 태그만, 링크는 보류 → 다음 /lint에서 검토.
7. moc 노트는 에이전트가 새로 만들지 않는다 — 기존 moc에 링크 추가만.

# Error Prevention & Validation Protocol
1. 수정 전 obsidian_get_note(document-map)로 기존 구조 확인 후 진행.
2. 기존 노트 전체 덮어쓰기 지양, 부분 수정 도구 우선.
3. 위키링크 포함 frontmatter 값은 항상 큰따옴표.
4. 링크 대상 존재 불확실하면 걸지 말고 #관련후보로 보류.
5. 애매한 카테고리/신규 카테고리/moc 승격 판단은 자동 처리하지 말고 사람에게 확인.
6. 작업 종료 시 처리 파일 목록, 생성/수정 노트 경로, RAW status 변경 내역을 요약 보고한다.
