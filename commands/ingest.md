먼저 vault_read로 "BellFollow/Wiki.md"를 읽고, 적용할 규칙 중
status 라이프사이클과 임계값을 아래 형식으로 출력한 뒤 시작한다.

  Wiki.md 로드: status = inbox|raw|linked|local|discarded / 임계값 = inbox <N>일, raw <N>일, open <N>일

이 줄을 출력하지 않고 진행하지 마라. 읽기 실패 시 중단하고 보고한다.

읽은 규칙(Wiki frontmatter 스키마, RAW→Wiki 승격 규칙, 링크 규칙, MCP 도구 사용 표준)을 따른다.

인자 없이 `/ingest`를 실행하면 아래 [A][B] 순서로 처리한다.
`/ingest findings <project-path>`로 실행하면 [C]만 단독으로 처리한다.

## [A] inbox 처리 (status: inbox, 볼트 전역, cwd 무관)

A1. search_query로 BellFollow/Raw/ 전체에서 status가 inbox인 파일을 전부
    찾는다. 없으면 조용히 건너뛴다.
A2. captured 오름차순(오래된 것 먼저)으로 목록을 출력한다:

      - <project> | <captured> | <제목 또는 본문 첫 줄 발췌>

A3. 각 항목에 대해 사용자에게 다음 중 선택을 묻는다(일괄 처리 의향을 먼저
    물어도 된다):
    ⓐ 기존 Wiki 노트에 링크
    ⓑ 신규 Wiki 노트 생성
    ⓒ 폐기
A4. ⓐ/ⓑ: [B]2와 동일한 절차(요약 추출, Wiki 카테고리 판단, frontmatter 채우기,
    크로스링크)로 Wiki 노트를 만들거나 기존 노트에 링크를 걸고,
    vault_patch(targetType: frontmatter)로 해당 RAW의 status를
    inbox → linked로 바꾼다.
A5. ⓒ: vault_patch로 status를 inbox → discarded로 바꾼다. **삭제·Trash
    이동은 하지 않는다** — 파일은 그대로 두고 상태만 바꾼다. 검토했다는
    기록을 남기는 것 자체가 목적이다.

## [B] raw 처리 (status: raw)

B1. search_query로 JsonLogic 쿼리(예: `{"and": [{"in": ["BellFollow/Raw/", {"var": "path"}]}, {"==": [{"var": "frontmatter.status"}, "raw"]}]}`)를 실행해 status가 raw인 파일만 골라낸다. status가 이미 linked 또는 local인 파일은 건드리지 않는다.
B2. 각 파일에 대해:
   - vault_read로 내용을 읽고 핵심만 추출해 원문 대비 대폭 축약한다.
   - 재사용성 판단: 이 RAW의 내용 중 "다른 프로젝트에서도 쓸 수 있는 것"만
     Wiki 노트로 만든다. 전부 프로젝트 로컬 내용이면 Wiki 노트를 만들지 않고
     status를 raw → local 로 바꾼 뒤 그 사실을 보고한다.
   - question 분리: 원문에 제기됐으나 답이 나지 않은 사항이 있으면 별도 노트로
     만든다 — type: question, status: open, source_raw는 같은 RAW를 가리킨다.
     한 RAW에서 concept 1개 + question 0~N개가 나올 수 있다.
     본문에 "원문 시점 YYYY-MM-DD(RAW의 captured) 기준, 이후 해소 여부 미확인"을
     넣는다 — RAW는 시점 사료라 거기 적힌 미해결이 /ingest 실행 시점에도
     미해결이라는 보장이 없다(원문과 처리 사이 시차 동안 다른 문서에서 이미
     해소됐을 수 있다).
   - Wiki.md의 Wiki 카테고리 중 가장 맞는 폴더를 판단한다. 애매하면 general/에 넣고 이유를 보고한다.
   - Wiki frontmatter(title, type, up, aliases, tags, status, created, updated, source_raw)를 채운다. source_raw에는 원본 RAW 노트를 `[[위키링크]]`로 남긴다. up 필드 위키링크는 반드시 큰따옴표로 감싼다.
   - search_query로 관련 기존 Wiki 노트를 찾아 링크 규칙에 따라 [[크로스링크]]를 건다. 억지로 걸지 않는다.
   - vault_write로 새 노트를 BellFollow/Wiki/ 해당 경로에 저장한다(local로 판정된 경우 생략).
   - vault_patch(targetType: frontmatter)로 원본 RAW 파일의 status를 raw → linked(또는 local)로 바꾼다. RAW 원본은 이동·삭제·본문 수정하지 않는다.
B3. 마지막에 승격한 RAW 파일 목록, 생성된 Wiki 노트 경로(concept/question 구분), local로 판정된 RAW, 애매해서 general/로 보낸 항목을 요약 보고한다.

## [C] FINDINGS 승격 — `/ingest findings <project-path>` 전용

<project-path>를 생략하면 사용자에게 묻는다(cwd로 추측하지 않는다).

C0. <project-path>의 document/FINDINGS_*.md 중 RAW에 없는 것을 RAW로 올린다(status: raw).

   C0-a. 올릴 FINDINGS가 하나라도 있으면 **항상** 사용자에게 확인한다.
        조건부로 묻지 않는다 — 조건이 어긋나면 조용히 통과(fail-open)해서
        막으려던 사고가 그대로 난다.

          project-path = <경로>
          여기의 FINDINGS <N>건을 RAW로 올릴까요?
            - <파일명>

        아니라고 하면 중단한다.
   C0-b. <project-path>에 FINDINGS가 없으면 조용히 건너뛴다 (물을 것이 없으므로).
   C0-c. 같은 source를 가진 RAW가 이미 있으면 새로 만들지 않고 보고한다.
   C0-d. frontmatter의 project에는 출신 git 레포명을 넣는다(로컬 폴더명 아님).
        <project-path>에서 git remote로 확인하고, 확인 안 되면 사람에게 묻는다.
   C0-e. 날짜 점검: 집어가는 FINDINGS의 파일명·본문 날짜가 실제 작성일과
        맞는지 확인하고, 어긋나면 그 자리에서 정정한다.
   C0-f. 파일명은 Wiki.md의 RAW 파일 규칙(YYYY-MM-DD_<slug>.md, slug는 영문
        kebab-case)으로 변환해서 저장한다. 원래 파일명은 source 필드에 남기므로
        정보가 사라지지 않는다.
        예: document/FINDINGS_2026-08-19_vault_reorg.md
            → BellFollow/Raw/2026-08-19_vault-reorg.md

올라간 RAW는 status: raw이므로, 다음 `/ingest`(인자 없이) 실행 시 [B]에서 처리된다.

---

> 가정: /ingest는 status: raw 파일을 한 번의 실행으로 일괄 처리할 수 있다.
> 이 가정 때문에 raw 상태에는 경과일수 임계값 규칙을 두지 않고 /lint 감지와
> 대시보드 가시성만 둔다. 실사용 중 한 번에 처리 가능한 양에 한계가 드러나면
> (예: 컨텍스트 제한으로 10~15개), raw에도 임계값 규칙이 필요한지 재검토할 것.
> inbox도 같은 가정을 공유한다 — 세션 노트가 쌓이는 속도가 한 번에 처리
> 가능한 양을 넘으면 재검토할 것.
