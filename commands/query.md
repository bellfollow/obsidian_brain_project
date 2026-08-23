먼저 vault_read로 볼트 루트의 "BellFollow/Wiki.md"를 읽고 카테고리 구조를 파악한다.

사용자의 질문에 대해 BellFollow/Wiki/ 폴더 전체를 검색해 답하라.

1. search_query로 JsonLogic 쿼리를 실행해 질문과 관련된 노트를 BellFollow/Wiki/ 전역에서 찾는다 (제목/태그/frontmatter는 해당 필드로, 본문은 `{"in": ["<키워드>", {"var": "content"}]}` 형태로 검색).
2. 찾은 노트들을 vault_read로 읽어 내용을 종합해 답변을 구성한다.
3. 답변에 참고한 노트의 경로를 함께 표기한다 (예: 참고: BellFollow/Wiki/maple-autochess/기능/전투-로직/개념정리.md).
4. 관련 노트가 없으면 없다고 명확히 말하고, BellFollow/Raw/에 관련 원본이 있는지도 확인해 안내한다. 안내할 때 status를 함께 표기한다 — 검증된 내용처럼 제시하지 않는다:
   - `inbox` → "아직 읽지 않은 수집 자료"
   - `raw` → "승격 대기 중인 원본"
   - `local` → "이 프로젝트 전용으로 판정돼 Wiki에 없음"
