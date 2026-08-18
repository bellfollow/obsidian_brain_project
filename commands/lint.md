먼저 obsidian_get_note로 볼트 루트의 "BellFollow/Wiki.md"를 읽고 규칙(frontmatter 스키마, 링크 규칙, up 필드 형식, RAW 승격 규칙)을 파악한다.

BellFollow/Wiki/ 및 BellFollow/RAW/ 폴더의 상태를 진단하고 리포트만 작성하라. 자동으로 파일을 수정하지 않는다.

점검 항목:
1. 중복 노트 후보 (제목이나 내용이 유사한 노트 쌍)
2. 깨진 링크 — [[ ]]가 실제 존재하지 않는 노트를 가리키는 경우
3. #관련후보 태그가 달린 채 방치된 노트 (링크로 승격할지 검토 대상)
4. type: atomic 노트인데 up: 필드가 비어있어 위계에서 고아가 된 노트
5. up 필드에 큰따옴표 없이 위키링크가 들어가 YAML 파싱이 깨질 위험이 있는 노트
6. 오래 방치된 BellFollow/Wiki/general/ 폴더 노트 (더 적절한 카테고리로 옮길 수 있는지)
7. BellFollow/RAW/에서 status가 raw인 채 오래 방치된 파일 (승격 후보인데 /ingest가 아직 안 돌았을 가능성)
8. status가 linked인데 그 원본을 가리키는 source_raw 링크를 가진 Wiki 노트가 실제로 존재하지 않는 경우 (승격 중 끊긴 링크)
9. BellFollow/RAW/에서 project 필드가 비어있거나 없는 파일 — 각 파일 내용을 보고 git 레포명을 유추할 수 있으면 후보로 제시하고, 확신 안 서면 "확인 필요"로만 표시한다 (자동으로 채우지 않는다, 수정은 사용자 확인 후 별도 진행)

각 항목별로 obsidian_search_notes / obsidian_list_notes로 확인한 노트 경로 목록과 함께 리포트를 작성해 보여준다. 수정은 사용자 확인 후 별도로 진행한다.
