---
paths: ["**/document/**", "**/docs/**"]
---

# Documentation Folder Conventions

이 프로젝트(또는 이 컨벤션을 쓰는 프로젝트들)는 문서 폴더를 용도별로 분리한다.

## `document/` 폴더 (한글)
- 목적: 진행상황, 세션별 상태, 트러블슈팅/포스트모템을 사람(개발자 본인)이 나중에 읽기 위한 기록
- 언어: 한글
- 주요 파일:
  - `document/PROJECT_STATUS.md`: 현재 진행 중인 세션 로그 및 프로젝트 상태
  - `document/FINDINGS_*.md`: 트러블슈팅 노트, 실험, 발견 사항

## `docs/` 폴더 (영어)
- 목적: 다른 AI 에이전트(Claude Code 등)가 읽을 정리된 문서 — 아키텍처 요약, 설계 스펙, API, 프로젝트 컨텍스트
- 언어: 영어

## 작업 규칙
- 작업 보고서, 진행상황 요약, 트러블슈팅 로그를 생성할 때 → 한글로 작성, `document/`에 저장
- 다른 AI 에이전트가 참조할 기술 스펙, 코드베이스 설명, API 매뉴얼을 생성할 때 → 영어로 작성, `docs/`에 저장

## RAW 미러링
`document/PROJECT_STATUS.md` 또는 `document/FINDINGS_*.md`가 새로 생성되거나 갱신될 때마다, 그 내용을 BellFollow 볼트의 RAW/에도 동일하게 저장한다 (CLAUDE.md 10번 규칙 및 Wiki.md의 RAW 저장 형식을 따른다). 로컬 기록은 그대로 유지하고, RAW 저장은 추가 미러링일 뿐 로컬 파일을 대체하지 않는다.
