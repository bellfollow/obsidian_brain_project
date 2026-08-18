먼저 obsidian_get_note로 볼트 루트의 "BellFollow/Wiki.md"를 읽고, 그 안의 규칙(Wiki frontmatter 스키마, RAW→Wiki 승격 규칙, 링크 규칙, MCP 도구 사용 표준)을 따른다. 읽기 실패 시 진행을 멈추고 사용자에게 보고한다.

이후 BellFollow/RAW/ 안의 승격 대상 파일을 처리하라.

1. obsidian_search_notes(dataview 모드 권장, 예: `TABLE FROM "BellFollow/RAW" WHERE status = "raw"`)로 status가 raw인 파일만 골라낸다. status가 이미 linked인 파일은 건드리지 않는다.
2. 각 파일에 대해:
   - obsidian_get_note로 내용을 읽고 핵심만 추출해 원문 대비 대폭 축약한다.
   - Wiki.md의 Wiki 카테고리 중 가장 맞는 폴더를 판단한다. 애매하면 general/에 넣고 이유를 보고한다.
   - Wiki frontmatter(title, type, up, aliases, tags, status, created, updated, source_raw)를 채운다. source_raw에는 원본 RAW 노트를 `[[위키링크]]`로 남긴다. up 필드 위키링크는 반드시 큰따옴표로 감싼다.
   - obsidian_search_notes로 관련 기존 Wiki 노트를 찾아 링크 규칙에 따라 [[크로스링크]]를 건다. 억지로 걸지 않는다.
   - obsidian_write_note로 새 노트를 BellFollow/Wiki/ 해당 경로에 저장한다.
   - obsidian_manage_frontmatter로 원본 RAW 파일의 status만 raw → linked로 바꾼다. RAW 원본은 이동·삭제·본문 수정하지 않는다.
3. 마지막에 승격한 RAW 파일 목록, 생성된 Wiki 노트 경로, 애매해서 general/로 보낸 항목을 요약 보고한다.
