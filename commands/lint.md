0. vault_read로 "BellFollow/Wiki.md"를 읽고, 그 안의 "임계값 정본" 절에
   적힌 값을 아래 형식으로 그대로 출력한 뒤 점검을 시작한다.

     임계값 (Wiki.md에서 읽음): inbox <N>일 / raw <N>일 / open <N>일

   이 줄을 출력하지 않고 점검에 들어가지 마라. 기억으로 값을 채우지 마라.

읽은 규칙(frontmatter 스키마, 링크 규칙, up 필드 형식, RAW 승격 규칙)을 따른다.

BellFollow/Wiki/ 및 BellFollow/Raw/ 폴더의 상태를 진단하고 리포트만 작성하라. 자동으로 파일을 수정하지 않는다.

점검 항목:
1. 중복 노트 후보 (제목이나 내용이 유사한 노트 쌍)
2. 깨진 링크 — [[ ]]가 실제 존재하지 않는 노트를 가리키는 경우
3. #관련후보 태그가 달린 채 방치된 노트 (링크로 승격할지 검토 대상)
4. type: atomic 노트인데 up: 필드가 비어있어 위계에서 고아가 된 노트
5. up 필드에 큰따옴표 없이 위키링크가 들어가 YAML 파싱이 깨질 위험이 있는 노트
6. BellFollow/Wiki/general/ 폴더 노트 중 updated 기준으로 0단계 임계값(open)을 초과한 것 (더 적절한 카테고리로 옮길 수 있는지)
7. BellFollow/Raw/에서 status가 raw인 채 0단계에서 읽은 임계값 기준으로 방치된 파일 (승격 후보인데 /ingest가 아직 안 돌았을 가능성)
8. status가 linked인데 그 원본을 가리키는 source_raw 링크를 가진 Wiki 노트가 실제로 존재하지 않는 경우 (승격 중 끊긴 링크). status: local인 RAW는 Wiki 노트가 없는 것이 정상이므로 이 점검에서 제외한다.
9. BellFollow/Raw/에서 project 필드가 비어있거나 없는 파일 — 각 파일 내용을 보고 git 레포명을 유추할 수 있으면 후보로 제시하고, 확신 안 서면 "확인 필요"로만 표시한다 (자동으로 채우지 않는다, 수정은 사용자 확인 후 별도 진행)
10. BellFollow/Raw/에서 status: inbox인 파일 중 captured 기준 0단계 임계값(inbox)을 초과한 것 — Trash 이동 후보로 제시한다(자동으로 옮기지 않는다)
11. BellFollow/Wiki/에서 status: open인 노트 중 updated 기준 0단계 임계값(open)을 초과한 것 — 장기 미해결 목록으로 제시하고, 각 항목에 선택지 3개를 함께 보여준다:
    ⓐ 아직 유효 → updated 갱신
    ⓑ 더 이상 안 중요 → Archive/ 이동(삭제 아님)
    ⓒ 사실 답 났음 → concept로 승격
12. BellFollow/Trash/의 파일 개수와 가장 오래된 항목을 리포트 맨 끝에 한 줄로 표시한다.

각 항목별로 search_query / vault_list로 확인한 노트 경로 목록과 함께 리포트를 작성해 보여준다. 수정은 사용자 확인 후 별도로 진행한다.
