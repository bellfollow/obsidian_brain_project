#!/usr/bin/env python3
"""
raw_writer.py — 세션 종료 시 볼트 Raw/에 세션 노트를 누적 생성/업데이트한다.
doc_writer.py가 HANDOFF.md를 쓴 뒤 호출한다. MCP 미사용, 파일 직접 쓰기.

build_raw_note()는 아무것도 쓰지 않는 순수 함수 — (path, frontmatter, body)만
계산해서 반환한다. 실제 파일 쓰기는 write_raw_note()가 담당하며, Google Drive
동기화 지연에 대비한 재시도/보류(pending) 저장을 포함한다.

doc_writer.py와 순환 import를 피하기 위해 load_config/call_gemini는 의도적으로
중복 구현한다(각각 15~25줄 정도라 공유의 이득보다 단방향 의존성을 깨는
리스크가 더 크다고 판단).
"""

import os
import re
import json
import time
import hashlib
import subprocess
import logging
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

log = logging.getLogger("doc_writer.raw_writer")

HOOKS_DIR    = Path.home() / ".claude" / "hooks"
CONFIG_ENV   = HOOKS_DIR / "config.env"
PENDING_DIR  = Path.home() / ".claude" / "raw_pending"


def load_config() -> dict:
    cfg = {
        "GEMINI_API_KEY": "",
        "GEMINI_MODEL":   "gemini-3.1-flash-lite",
        "GEMINI_TIMEOUT": "60",
    }
    if CONFIG_ENV.exists():
        for line in CONFIG_ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                cfg[k.strip()] = v.strip()
    return cfg


def call_gemini(api_key: str, model: str, prompt: str, timeout: int) -> str:
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )
    body = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    retry_delays = [5, 15]  # 503/429 전용, 딱 2회만
    for attempt in range(len(retry_delays) + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and attempt < len(retry_delays):
                delay = retry_delays[attempt]
                log.warning(f"raw_writer: Gemini {e.code}, retrying in {delay}s... (attempt {attempt + 1}/{len(retry_delays)})")
                time.sleep(delay)
                continue
            log.error(f"raw_writer: Gemini HTTP error {e.code}: {e.read()[:200]}")
            raise
        except Exception as e:
            log.error(f"raw_writer: Gemini call error: {e}")
            raise
    return ""


def _real_vault_path() -> Path:
    claude_md = Path.home() / ".claude" / "CLAUDE.md"
    text = claude_md.read_text(encoding="utf-8")
    m = re.search(r"Vault path:\s*`([^`]+)`", text)
    if not m:
        raise RuntimeError(
            f"Vault path를 {claude_md}에서 찾을 수 없음 "
            f"(OBSIDIAN_VAULT 환경변수로 override 가능)"
        )
    return Path(m.group(1))


def resolve_vault_root() -> Path:
    """
    OBSIDIAN_VAULT 환경변수가 있으면 그걸 쓰고, 없으면 ~/.claude/CLAUDE.md의
    "Vault path: `...`" 줄을 파싱한다. 하드코딩하지 않는다.

    RAW_WRITER_TEST=1 (테스트 모드)일 때는 안전장치 둘을 건다 — 실수로
    프로덕션 볼트에 테스트 데이터를 쓰는 사고(과거 1회 발생)를 막기 위함:
    - OBSIDIAN_VAULT가 지정 안 되면 CLAUDE.md fallback 금지, 즉시 abort.
    - OBSIDIAN_VAULT가 지정됐어도 실제 볼트 경로와 같으면 abort.
    """
    test_mode = os.environ.get("RAW_WRITER_TEST") == "1"
    env_val = os.environ.get("OBSIDIAN_VAULT")

    if test_mode:
        if not env_val:
            raise RuntimeError(
                "RAW_WRITER_TEST=1인데 OBSIDIAN_VAULT가 지정되지 않음 — "
                "테스트 모드에서는 CLAUDE.md fallback을 금지한다. abort."
            )
        env_path = Path(env_val)
        real_path = _real_vault_path()
        if str(env_path.resolve()).lower() == str(real_path.resolve()).lower():
            raise RuntimeError(
                f"RAW_WRITER_TEST=1인데 OBSIDIAN_VAULT({env_path})가 "
                f"실제 볼트 경로({real_path})와 동일함. abort."
            )
        return env_path

    if env_val:
        return Path(env_val)
    return _real_vault_path()


def _git_project_name(cwd: Path) -> str:
    """git remote origin에서 레포명을 뽑는다. 실패하면 폴더명으로 떨어진다."""
    try:
        result = subprocess.run(
            ["git", "-C", str(cwd), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            url = result.stdout.strip().rstrip("/")
            name = url.split("/")[-1]
            if name.endswith(".git"):
                name = name[:-4]
            if name:
                return name
    except Exception:
        pass
    return cwd.name


_NON_USER_PREFIXES = (
    "<command-name>", "<command-message>", "<command-args>", "<local-command-",
    "<system-reminder>", "<user-prompt-submit-hook>",
)


def user_texts(obj):
    """진짜 사용자 입력 텍스트만 반환. str(신형)/text 블록 리스트(구형) 둘 다 지원.
    tool_result 블록, isMeta 레코드, 시스템 주입 태그, 슬래시 명령(한 줄 "/...")은 제외."""
    if obj.get("isMeta"):
        return []
    c = (obj.get("message") or {}).get("content")
    if isinstance(c, str):
        c = [c]
    out = []
    for b in c or []:
        t = b if isinstance(b, str) else (b.get("text", "") if isinstance(b, dict) and b.get("type") == "text" else "")
        s = t.strip()
        if not s or s.startswith(_NON_USER_PREFIXES):
            continue
        if s.startswith("/") and "\n" not in s:
            continue
        out.append(t)
    return out


def _read_transcript_for_raw(transcript_path: Path):
    """
    (filtered_text, user_message_count)를 반환한다.
    user_message_count는 텍스트가 있는 user 메시지 개수 — 스킵 판정 기준.
    """
    user_count = 0
    lines_out = []
    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            for raw in f:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if not isinstance(obj, dict):
                    continue
                msg_type = obj.get("type", "")
                if msg_type == "user":
                    for text in user_texts(obj):
                        user_count += 1
                        lines_out.append(f"[user] {text[:2000]}")
                elif msg_type == "assistant":
                    for block in obj.get("message", {}).get("content", []):
                        if isinstance(block, dict) and block.get("type") == "text":
                            lines_out.append(f"[assistant] {block.get('text', '')[:2000]}")
    except Exception as e:
        log.warning(f"raw_writer: transcript read failed: {e}")
    return "\n".join(lines_out), user_count


RAW_NOTE_PROMPT = """You are archiving a Claude Code coding session into a personal
knowledge vault. Read the transcript below and write ONLY the sections that
actually apply — if a section has nothing to say, omit its heading entirely
(do not write "None" or "해당 없음").

Sections (Korean headings, in this order, write in Korean):

## 요약
(2-4문장: 무엇을 하려고 했고 어떻게 됐는지)

## 결정사항
(불릿: 내린 결정과 이유. 사소한 결정은 생략)

## 트러블슈팅
(불릿: 문제, 원인, 해결. 문제가 없었으면 섹션 전체 생략)

## 재사용 가능한 지식
(불릿: 이 세션에서 나온 내용 중 다른 프로젝트에서도 쓸 수 있는 도메인 지식이나
RAG 소재가 있다면. 각 항목 끝에 "어느 프로젝트에 쓸지"를 한 줄로. 해당 없으면
섹션 전체 생략)

구체적으로 쓰고, transcript에 없는 내용을 지어내지 마라.

TRANSCRIPT:
{transcript}
"""


def build_raw_note(
    transcript_path, cwd, session_id: str, captured,
    project_override: str = None, extra_tags: list = None, source_path=None,
):
    """
    쓰기 없는 순수 함수. 반환: (path, frontmatter, body).
    None 반환은 두 가지 경우 — 호출자는 로그로 구분한다:
    - 사용자 메시지 3개 미만 AND 필터된 텍스트 20KB 미만: 스킵(내용 자체가 적음)
    - Gemini 실패 또는 응답에 "## " 섹션이 하나도 없음: 실패(재시도/수동 처리 대상)

    captured: ISO 문자열 또는 datetime/date — "이 세션이 실제로 있었던 날짜".
    실시간 훅에서는 호출 시점(오늘)을 넘기고, 백필에서는 세션 jsonl 첫
    메시지의 timestamp 날짜를 호출자가 넘긴다. 파일명과 frontmatter의
    captured 필드 모두 이 값 하나로 통일한다.

    project_override: git remote 조회 없이 project 필드를 강제 지정(백필용 —
    백업 사본 경로에서 git remote를 조회하면 틀린 값이 나오므로).
    extra_tags: "session" 기본 태그에 추가할 태그 목록(예: 백필이면 ["backfill"]).
    source_path: frontmatter source/본문 trailer에 적을 경로를 transcript_path와
    다르게 지정(백필에서 실제로 읽는 건 백업 사본이지만, source는 원본 live
    경로를 가리켜야 하므로).
    """
    transcript_path = Path(transcript_path)
    cwd = Path(cwd)
    display_source = Path(source_path) if source_path else transcript_path

    filtered, user_count = _read_transcript_for_raw(transcript_path)
    if user_count < 3 and len(filtered.encode("utf-8")) < 20 * 1024:
        log.info(f"raw_writer: skip (user_count={user_count}, filtered<20KB): {session_id}")
        return None, None, None

    captured_dt = (
        datetime.fromisoformat(captured) if isinstance(captured, str) else captured
    )
    date_str = captured_dt.strftime("%Y-%m-%d")
    project = project_override if project_override else _git_project_name(cwd)
    vault_root = resolve_vault_root()
    path = vault_root / "Raw" / f"{date_str}_{project}_{session_id[:8]}.md"

    cfg = load_config()
    try:
        body = call_gemini(
            cfg["GEMINI_API_KEY"], cfg["GEMINI_MODEL"],
            RAW_NOTE_PROMPT.format(transcript=filtered), int(cfg["GEMINI_TIMEOUT"]),
        )
    except Exception as e:
        log.error(f"raw_writer: Gemini call failed, 노트 생성 실패: {session_id}: {e}")
        return None, None, None

    body = body.strip()
    if "## " not in body:
        log.error(f"raw_writer: Gemini 응답에 섹션 없음(빈 본문), 노트 생성 실패: {session_id}")
        return None, None, None

    body += f"\n\n원본 transcript 경로: `{display_source}`"

    tags = ["session"] + list(extra_tags or [])
    tags_str = "[" + ", ".join(tags) + "]"
    frontmatter = (
        "---\n"
        f"source: {display_source}\n"
        f"captured: {date_str}\n"
        "status: inbox\n"
        f"project: {project}\n"
        f"session_id: {session_id}\n"
        f"tags: {tags_str}\n"
        "---\n\n"
    )
    return path, frontmatter, body


def _last_section_text(existing: str) -> str:
    """기존 노트에서 비교 대상 텍스트를 뽑는다 — 마지막 업데이트 섹션이
    있으면 그것, 없으면 frontmatter 이후의 최초 본문."""
    marker = "\n## 업데이트 "
    if marker in existing:
        last = existing.rsplit(marker, 1)[1]
        _, _, rest = last.partition("\n")
        return rest.strip()
    if "---\n\n" in existing:
        return existing.split("---\n\n", 1)[1].strip()
    return existing.strip()


def _atomic_write(path: Path, content: str) -> bool:
    """같은 폴더에 .tmp로 쓰고 os.replace. Google Drive 동기화로 인한
    PermissionError/OSError는 0.5초 간격 3회 재시도."""
    tmp = path.with_suffix(path.suffix + f".tmp{os.getpid()}")
    last_exc = None
    for attempt in range(3):
        try:
            tmp.write_text(content, encoding="utf-8")
            os.replace(tmp, path)
            return True
        except (PermissionError, OSError) as e:
            last_exc = e
            log.warning(f"raw_writer: write attempt {attempt + 1}/3 failed: {e}")
            time.sleep(0.5)
    log.error(f"raw_writer: write failed after 3 attempts: {last_exc}")
    try:
        tmp.unlink(missing_ok=True)
    except Exception:
        pass
    return False


def _save_pending(path: Path, content: str):
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(str(path).encode("utf-8")).hexdigest()
    pending_file = PENDING_DIR / f"{digest}.json"
    pending_file.write_text(
        json.dumps({"path": str(path), "content": content}, ensure_ascii=False),
        encoding="utf-8",
    )
    log.error(f"raw_writer: 최종 실패, pending 저장: {pending_file} (target={path})")


def flush_pending():
    """다음 훅 실행 시 가장 먼저 호출 — 쌓여있는 pending 재전송을 시도한다."""
    if not PENDING_DIR.is_dir():
        return
    for pending_file in list(PENDING_DIR.glob("*.json")):
        try:
            data = json.loads(pending_file.read_text(encoding="utf-8"))
            target = Path(data["path"])
            target.parent.mkdir(parents=True, exist_ok=True)
            if _atomic_write(target, data["content"]):
                pending_file.unlink(missing_ok=True)
                log.info(f"raw_writer: pending 재전송 성공: {target}")
        except Exception as e:
            log.error(f"raw_writer: pending 재전송 실패: {pending_file}: {e}")


def _warn_sync_conflicts(raw_dir: Path):
    """Raw/ 바로 밑에 Google Drive 충돌 사본으로 보이는 파일명이 있으면 경고."""
    try:
        for p in raw_dir.glob("*.md"):
            name = p.name
            if "(1)" in name or "conflict" in name.lower():
                log.warning(f"raw_writer: 동기화 충돌 의심 파일: {p}")
    except Exception:
        pass


def write_raw_note(
    transcript_path, cwd, session_id: str, captured,
    project_override: str = None, extra_tags: list = None, source_path=None,
):
    """반환: 실제로 대상으로 삼은 path(스킵이면 None) — 호출자가 결과를 알 수 있게."""
    flush_pending()

    path, frontmatter, body = build_raw_note(
        transcript_path, cwd, session_id, captured,
        project_override=project_override, extra_tags=extra_tags, source_path=source_path,
    )
    if path is None:
        log.info("raw_writer: skip (사용자 메시지 3개 미만)")
        return None

    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if body.strip() == _last_section_text(existing):
            log.info(f"raw_writer: 변경 없음, 스킵: {path}")
            return path
        # 업데이트 시각은 captured(세션이 있었던 날짜)가 아니라 실제 "지금"
        # — 백필처럼 captured가 과거일 때도 업데이트 마커는 현재 시각이어야 함.
        hhmm = datetime.now().strftime("%H:%M")
        full = existing.rstrip() + f"\n\n## 업데이트 {hhmm}\n\n{body}\n"
    else:
        full = frontmatter + body + "\n"

    if not _atomic_write(path, full):
        _save_pending(path, full)

    _warn_sync_conflicts(path.parent)
    return path
