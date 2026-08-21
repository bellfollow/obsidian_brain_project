먼저 vault_read로 "BellFollow/Wiki.md"를 읽고, 적용할 규칙 중
status 라이프사이클 4단계와 임계값을 아래 형식으로 출력한 뒤 시작한다.

  Wiki.md 로드: status = inbox|raw|linked|local / 임계값 = inbox <N>일, raw <N>일, open <N>일

이 줄을 출력하지 않고 진행하지 마라. 읽기 실패 시 중단하고 보고한다.

읽은 규칙(Wiki frontmatter 스키마, RAW→Wiki 승격 규칙, 링크 규칙, MCP 도구 사용 표준)을 따른다.

0. cwd의 document/FINDINGS_*.md 중 RAW에 없는 것을 RAW로 올린다(status: raw).

   0-a. 올릴 FINDINGS가 하나라도 있으면 **항상** 사용자에게 확인한다.
        조건부로 묻지 않는다 — 조건이 어긋나면 조용히 통과(fail-open)해서
        막으려던 사고가 그대로 난다.

          cwd = <경로>
          여기의 FINDINGS <N>건을 RAW로 올릴까요?
            - <파일명>
          (참고) 이번 세션의 볼트 작업: <수정한 노트 경로 요약, 있으면>

        아니라고 하면 0단계를 건너뛰고 1단계로 간다.
        볼트 작업 내역은 판단 근거로 함께 보여주되, 확인창을 띄우는 조건은 아니다.
   0-b. cwd에 FINDINGS가 없으면 조용히 건너뛴다 (물을 것이 없으므로).
   0-c. 같은 source를 가진 RAW가 이미 있으면 새로 만들지 않고 보고한다.
   0-d. frontmatter의 project에는 출신 git 레포명을 넣는다(로컬 폴더명 아님).
        git remote로 확인하고, 확인 안 되면 사람에게 묻는다.
   0-e. 날짜 점검: 집어가는 FINDINGS의 파일명·본문 날짜가 실제 작성일과
        맞는지 확인하고, 어긋나면 그 자리에서 정정한다.
   0-f. 파일명은 Wiki.md의 RAW 파일 규칙(YYYY-MM-DD_<slug>.md, slug는 영문
        kebab-case)으로 변환해서 저장한다. 원래 파일명은 source 필드에 남기므로
        정보가 사라지지 않는다.
        예: document/FINDINGS_2026-08-19_vault_reorg.md
            → BellFollow/RAW/2026-08-19_vault-reorg.md

이후 BellFollow/RAW/ 안의 승격 대상 파일을 처리하라.

1. search_query로 JsonLogic 쿼리(예: `{"and": [{"in": ["BellFollow/RAW/", {"var": "path"}]}, {"==": [{"var": "frontmatter.status"}, "raw"]}]}`)를 실행해 status가 raw인 파일만 골라낸다. status가 이미 linked 또는 local인 파일은 건드리지 않는다.
2. 각 파일에 대해:
   - vault_read로 내용을 읽고 핵심만 추출해 원문 대비 대폭 축약한다.
   - 재사용성 판단: 이 RAW의 내용 중 "다른 프로젝트에서도 쓸 수 있는 것"만
     Wiki 노트로 만든다. 전부 프로젝트 로컬 내용이면 Wiki 노트를 만들지 않고
     status를 raw → local 로 바꾼 뒤 그 사실을 보고한다.
   - question 분리: 원문에 제기됐으나 답이 나지 않은 사항이 있으면 별도 노트로
     만든다 — type: question, status: open, source_raw는 같은 RAW를 가리킨다.
     한 RAW에서 concept 1개 + question 0~N개가 나올 수 있다.
   - Wiki.md의 Wiki 카테고리 중 가장 맞는 폴더를 판단한다. 애매하면 general/에 넣고 이유를 보고한다.
   - Wiki frontmatter(title, type, up, aliases, tags, status, created, updated, source_raw)를 채운다. source_raw에는 원본 RAW 노트를 `[[위키링크]]`로 남긴다. up 필드 위키링크는 반드시 큰따옴표로 감싼다.
   - search_query로 관련 기존 Wiki 노트를 찾아 링크 규칙에 따라 [[크로스링크]]를 건다. 억지로 걸지 않는다.
   - vault_write로 새 노트를 BellFollow/Wiki/ 해당 경로에 저장한다(local로 판정된 경우 생략).
   - vault_patch(targetType: frontmatter)로 원본 RAW 파일의 status를 raw → linked(또는 local)로 바꾼다. RAW 원본은 이동·삭제·본문 수정하지 않는다.
3. 마지막에 승격한 RAW 파일 목록, 생성된 Wiki 노트 경로(concept/question 구분), local로 판정된 RAW, 애매해서 general/로 보낸 항목을 요약 보고한다.

---

> 가정: /ingest는 status: raw 파일을 한 번의 실행으로 일괄 처리할 수 있다.
> 이 가정 때문에 raw 상태에는 경과일수 임계값 규칙을 두지 않고 /lint 감지와
> 대시보드 가시성만 둔다. 실사용 중 한 번에 처리 가능한 양에 한계가 드러나면
> (예: 컨텍스트 제한으로 10~15개), raw에도 임계값 규칙이 필요한지 재검토할 것.
