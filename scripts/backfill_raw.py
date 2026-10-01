#!/usr/bin/env python3
"""
backfill_raw.py — 나라장터(korean_market_ai) 과거 세션을 볼트 Raw/에 백필한다.

hooks/raw_writer.py의 build_raw_note/write_raw_note를 그대로 import해서 쓴다
(새로 구현하지 않음). 기본은 --dry(쓰기 없이 미리보기), --apply를 줘야
실제로 raw_writer.write_raw_note를 호출해 쓴다.

대상은 ~/.claude/_backup/transcripts/narajangteo/*.jsonl (백업 사본) —
라이브 세션을 건드리지 않는다. source/trailer에는 원본 live 경로를 적는다.

스킵 여부는 raw_writer.build_raw_note를 부르기 전에 이 스크립트가 직접
_read_transcript_for_raw로 먼저 판단한다(사용자 메시지 3개 미만 AND 필터된
텍스트 20KB 미만). 그래서 그 조건을 통과했는데도 build_raw_note/write_raw_note가
None을 반환하면 그건 "스킵"이 아니라 "실패"(Gemini 실패 또는 빈 본문)로 분류한다.
"""

import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "hooks"))
import raw_writer

BACKUP_DIR = Path.home() / ".claude" / "_backup" / "transcripts" / "narajangteo"
LIVE_DIR = Path.home() / ".claude" / "projects" / "c--dev-narajangteo"
PROJECT = "korean_market_ai"
EXTRA_TAGS = ["backfill"]
SLEEP_BETWEEN_SESSIONS = 2  # Gemini 503 대비
SKIP_USER_COUNT = 3
SKIP_FILTERED_BYTES = 20 * 1024


def first_timestamp_date(jsonl_path: Path) -> str:
    """세션 jsonl 첫 메시지의 timestamp 날짜(YYYY-MM-DD)."""
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = obj.get("timestamp")
            if ts:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                return dt.strftime("%Y-%m-%d")
    raise RuntimeError(f"timestamp를 가진 줄을 못 찾음: {jsonl_path}")


def already_in_raw(vault_root: Path, session_id: str):
    raw_dir = vault_root / "Raw"
    if not raw_dir.is_dir():
        return None
    matches = list(raw_dir.glob(f"*_{session_id[:8]}.md"))
    return matches[0] if matches else None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", help="실제로 쓴다. 기본은 dry(미리보기만).")
    args = p.parse_args()
    dry = not args.apply

    jsonl_files = sorted(BACKUP_DIR.glob("*.jsonl"))
    print(f"대상: {len(jsonl_files)}개 ({BACKUP_DIR}), 모드: {'dry' if dry else 'apply'}")

    vault_root = raw_writer.resolve_vault_root()
    print(f"vault_root: {vault_root}")

    created, skipped, failed = [], [], []
    manual_candidates = []  # 실패 세션 재처리용(session_id, jsonl_path, live_source, captured)

    for i, jsonl_path in enumerate(jsonl_files):
        session_id = jsonl_path.stem
        live_source = LIVE_DIR / f"{session_id}.jsonl"

        existing = already_in_raw(vault_root, session_id)
        if existing:
            print(f"SKIP (이미 존재): {session_id} -> {existing}")
            skipped.append((session_id, "already_in_raw", str(existing)))
            continue

        try:
            captured = first_timestamp_date(jsonl_path)
        except Exception as e:
            print(f"FAIL (timestamp 파싱 실패): {session_id}: {e}")
            failed.append((session_id, f"timestamp parse failed: {e}"))
            manual_candidates.append((session_id, jsonl_path, live_source, None))
            continue

        # 스킵 여부를 build_raw_note 호출 전에 직접 판단 — 통과한 뒤 None이
        # 나오면 그건 스킵이 아니라 Gemini/빈 본문 실패다.
        filtered, user_count = raw_writer._read_transcript_for_raw(jsonl_path)
        if user_count < SKIP_USER_COUNT and len(filtered.encode("utf-8")) < SKIP_FILTERED_BYTES:
            print(f"SKIP (user_count={user_count}, filtered<20KB): {session_id}")
            skipped.append((session_id, "too_few_messages_and_short", None))
            continue

        kwargs = dict(
            project_override=PROJECT, extra_tags=EXTRA_TAGS, source_path=live_source,
        )

        if dry:
            path, frontmatter, body = raw_writer.build_raw_note(
                jsonl_path, jsonl_path.parent, session_id, captured, **kwargs
            )
            if path is None:
                print(f"FAIL (Gemini 실패/빈 본문): {session_id}")
                failed.append((session_id, "gemini_failed_or_empty_body"))
                manual_candidates.append((session_id, jsonl_path, live_source, captured))
            else:
                size = len((frontmatter + body).encode("utf-8"))
                print(f"[dry] {session_id} (captured={captured}) -> {path} ({size} bytes)")
                created.append((session_id, str(path), size))
        else:
            path = raw_writer.write_raw_note(
                jsonl_path, jsonl_path.parent, session_id, captured, **kwargs
            )
            if path is None:
                print(f"FAIL (Gemini 실패/빈 본문): {session_id}")
                failed.append((session_id, "gemini_failed_or_empty_body"))
                manual_candidates.append((session_id, jsonl_path, live_source, captured))
            elif path.exists():
                size = path.stat().st_size
                print(f"OK: {session_id} (captured={captured}) -> {path} ({size} bytes)")
                created.append((session_id, str(path), size))
            else:
                print(f"PENDING (쓰기 실패, raw_pending/에 보류): {session_id} -> {path}")
                failed.append((session_id, "write failed, saved to raw_pending"))
                manual_candidates.append((session_id, jsonl_path, live_source, captured))

        if i < len(jsonl_files) - 1:
            time.sleep(SLEEP_BETWEEN_SESSIONS)

    print()
    print(f"=== 요약 === 생성/예정 {len(created)} / 스킵 {len(skipped)} / 실패 {len(failed)}")
    if failed:
        print("실패 목록:")
        for item in failed:
            print(" ", item)
        print()
        print("수동 처리 후보(session_id, jsonl_path, live_source, captured):")
        for item in manual_candidates:
            print(" ", item)


if __name__ == "__main__":
    main()
