#!/usr/bin/env python3
"""
doc_writer.py — v2 (완성본)

2-stage detach 구조:
  PARENT (hook이 직접 호출): stdin(hook JSON) 읽고 debounce만 판단 →
                            통과 시 job 파일 쓰고 detached child spawn → 즉시 exit (<1s)
  CHILD  (--job 로 재실행):  Gemini 콜 + HANDOFF.md write. 세션과 분리되어 백그라운드 실행.

stage 구분: argv에 --job 있으면 child, 없으면 parent.

수정 사항 (v1 대비):
  #1 detach: 'async' settings 필드는 존재하지 않음 → 스크립트가 직접 detach.
             stdin은 child가 못 받으므로 hook_input을 job 파일(JSON)로 넘긴다.
  #2 state:  Gemini 실패/빈응답이어도 child finally에서 last_lines 갱신
             → 같은 delta로 매 turn 무한 재호출되는 것 차단 (miss는 plan대로 수용).
  #3 ts:     HANDOFF 헤더 timestamp를 LLM 출력에 의존하지 않고 코드가 박는다.
             CAS 비교가 코드-주입 값끼리라 신뢰 가능.
  #4 lock:   atomic O_CREAT|O_EXCL + stale TTL/PID 체크.
"""

import sys
import os
import json
import time
import datetime
import tempfile
import subprocess
import logging
import argparse
import re
import urllib.request
import urllib.error
from pathlib import Path

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

# ── 경로 상수 ─────────────────────────────────────────────────────────────────
HOOKS_DIR  = Path.home() / ".claude" / "hooks"
CONFIG_ENV = HOOKS_DIR / "config.env"
LOG_FILE   = HOOKS_DIR / "doc_writer.log"
JOBS_DIR   = HOOKS_DIR / "jobs"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("doc_writer")


# ══════════════════════════════════════════════════════════════════════════════
# 헬퍼
# ══════════════════════════════════════════════════════════════════════════════

def load_config() -> dict:
    cfg = {
        "GEMINI_API_KEY": "",
        "GEMINI_MODEL":   "gemini-3.1-flash-lite",
        "GEMINI_TIMEOUT": "60",
        "LINE_THRESHOLD": "50",
        "LOCK_TTL":       "90",
    }
    if CONFIG_ENV.exists():
        for line in CONFIG_ENV.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                cfg[k.strip()] = v.strip()
    return cfg


def count_lines(path: str) -> int:
    try:
        with open(path, "rb") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def read_last_lines(project_dir: Path) -> tuple:
    """Returns (session_id, line_count)"""
    state_file = project_dir / ".handoff_last_lines"
    try:
        text = state_file.read_text(encoding="utf-8").strip()
        sid, _, lines = text.partition(":")
        return sid, int(lines)
    except Exception:
        return "", 0


def write_last_lines(project_dir: Path, session_id: str, lines: int):
    state_file = project_dir / ".handoff_last_lines"
    try:
        state_file.write_text(f"{session_id}:{lines}", encoding="utf-8")
    except Exception as e:
        log.error(f"write_last_lines failed: {e}")


def acquire_lock(project_dir: Path, lock_ttl: int) -> bool:
    """
    Atomic lock via O_CREAT|O_EXCL.
    Stale lock(TTL 초과 or PID dead) 이면 탈취.
    Returns True if lock acquired.
    """
    lock_file = project_dir / ".handoff_writing.lock"

    def _try_create() -> bool:
        try:
            fd = os.open(
                str(lock_file),
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
            with os.fdopen(fd, "w") as f:
                f.write(f"{os.getpid()}:{time.time()}")
            return True
        except FileExistsError:
            return False
        except Exception as e:
            log.error(f"acquire_lock create error: {e}")
            return False

    if _try_create():
        return True

    # 이미 존재 → stale 여부 확인
    try:
        text = lock_file.read_text(encoding="utf-8").strip()
        pid_str, _, ts_str = text.partition(":")
        pid = int(pid_str)
        age = time.time() - float(ts_str)

        if age < lock_ttl:
            alive = False
            if HAS_PSUTIL:
                alive = psutil.pid_exists(pid)
            else:
                alive = True  # TTL만으로 판단 (psutil 없으면)

            if alive:
                log.info(f"Lock held by PID {pid} (age {age:.0f}s), skip.")
                return False

        # stale → 탈취
        log.info(f"Stale lock (PID {pid}, age {age:.0f}s), stealing.")
        lock_file.unlink(missing_ok=True)
        return _try_create()

    except Exception as e:
        log.warning(f"lock inspection failed: {e}, attempting steal.")
        try:
            lock_file.unlink(missing_ok=True)
        except Exception:
            pass
        return _try_create()


def release_lock(project_dir: Path):
    lock_file = project_dir / ".handoff_writing.lock"
    try:
        lock_file.unlink(missing_ok=True)
    except Exception:
        pass


def filter_transcript(transcript_path: str):
    """
    JSONL에서 text/thinking 블록 + tool name만 추출.
    tool_result 대용량 내용, base64, 긴 stdout 제거.

    Returns (filtered_text, path_list, tool_names).
    path_list: tool_use의 file_path/path/notebook_path 값만 (경로로 신뢰 가능한
               키만 — command= 같은 자유 텍스트 필드는 넣지 않는다).
    tool_names: 등장한 tool_use 이름 전부(중복 포함, 등장 순서).
    """
    MAX_TEXT_LEN      = 2000
    MAX_THINKING_LEN  = 1000
    MAX_TOOL_INPUT_LEN = 300
    lines_out = []
    path_list = []
    tool_names = []
    PATH_KEYS = ("file_path", "path", "notebook_path")

    try:
        for enc in ("utf-8", "cp949", "latin-1"):
            try:
                with open(transcript_path, "r", encoding=enc) as f:
                    raw_lines = f.readlines()
                break
            except (UnicodeDecodeError, LookupError):
                continue
        else:
            raw_lines = []

        for raw in raw_lines:
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

                if msg_type == "assistant":
                    for block in obj.get("message", {}).get("content", []):
                        if not isinstance(block, dict):
                            continue
                        btype = block.get("type", "")
                        if btype == "text":
                            lines_out.append(
                                f"[assistant] {block.get('text', '')[:MAX_TEXT_LEN]}"
                            )
                        elif btype == "thinking":
                            lines_out.append(
                                f"[thinking] {block.get('thinking', '')[:MAX_THINKING_LEN]}"
                            )
                        elif btype == "tool_use":
                            name = block.get("name", "")
                            inp  = block.get("input", {}) or {}
                            tool_names.append(name)
                            # 식별자 값은 살리고, 대용량 blob만 크기로 대체
                            KEEP = ("file_path", "path", "command", "pattern",
                                    "url", "query", "notebook_path")
                            DROP = ("content", "new_string", "old_string",
                                    "new_str", "old_str")
                            parts = []
                            for k, v in inp.items():
                                if k in DROP:
                                    parts.append(f"{k}=<{len(str(v))} chars>")
                                elif k in KEEP:
                                    parts.append(f"{k}={str(v)[:200]}")
                                if k in PATH_KEYS and v:
                                    path_list.append(str(v))
                            lines_out.append(f"[tool_use] {name} {' '.join(parts)}")

                elif msg_type == "user":
                    for block in obj.get("message", {}).get("content", []):
                        if not isinstance(block, dict):
                            continue
                        btype = block.get("type", "")
                        if btype == "text":
                            lines_out.append(
                                f"[user] {block.get('text', '')[:MAX_TEXT_LEN]}"
                            )
                        elif btype == "tool_result":
                            lines_out.append("[tool_result] (omitted)")

    except Exception as e:
        log.warning(f"filter_transcript error: {e}")

    return "\n".join(lines_out), path_list, tool_names


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

    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt == 0:
                log.warning("Rate limit, retrying in 10s...")
                time.sleep(10)
                continue
            log.error(f"Gemini HTTP error {e.code}: {e.read()[:200]}")
            raise
        except Exception as e:
            log.error(f"Gemini call error: {e}")
            raise
    return ""


def ensure_handoff_stub(project_dir: Path):
    handoff_path = project_dir / "HANDOFF.md"
    if not handoff_path.exists():
        stub = (
            "# HANDOFF\n"
            "<!-- last-updated: never | session: none -->\n\n"
            "_Not yet generated. Will be created after first session._\n"
        )
        try:
            handoff_path.write_text(stub, encoding="utf-8")
            log.info(f"Created HANDOFF stub: {handoff_path}")
        except Exception as e:
            log.error(f"stub write failed: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# #1  detach helper
# ══════════════════════════════════════════════════════════════════════════════
def spawn_detached_child(job_path: Path, force: bool):
    argv = [sys.executable, os.path.abspath(__file__), "--job", str(job_path)]
    if force:
        argv.append("--force")

    kwargs = dict(
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x00000008 | 0x00000200  # DETACHED | NEW_GROUP
    else:
        kwargs["start_new_session"] = True

    subprocess.Popen(argv, **kwargs)
    log.info(f"spawned detached child, job={job_path.name}")


# ══════════════════════════════════════════════════════════════════════════════
# #3  PROMPT + build_handoff: 헤더/timestamp는 코드가 100% 통제
# ══════════════════════════════════════════════════════════════════════════════
HANDOFF_PROMPT = """You are a technical documentation assistant.
Read the Claude Code session transcript below and produce the BODY of a HANDOFF.md.
Do NOT output any title line or HTML comment header — the system adds those.

Output exactly these markdown sections:

## Current Project State
(1-2 sentences on overall status)

## What Was Done This Session
(bullet list of concrete changes/decisions)

## Known Issues & Blockers
(bullets, or "None")

## Next Steps
(bullets of immediate next actions)

Keep under 400 words. Be specific, not generic.

Summarize only work relevant to the current project directory (cwd). If the
transcript includes work on a different repository or the Obsidian vault,
do not fold that into the summary — you may note that out-of-scope work
occurred, but keep the sections above focused on this project. (This
instruction is advisory only; a code-level check enforces the real guard.)

TRANSCRIPT:
{transcript}
"""


def compute_scope_banner(path_list: list, tool_names: list, project_dir: Path) -> str:
    """
    코드 레벨 결정적 판정 — LLM 출력과 무관하게 동작한다.
    OR 조건 둘: (1) project_dir 밖 경로 접근, (2) obsidian 계열 도구 사용.
    (2)가 주 신호다 — MCP 도구는 file_path/path 인자명을 안 쓸 수 있어
    경로 추출(1)만으로는 놓칠 수 있다.
    command= 값은 자유 텍스트라 여기서 판정에 쓰지 않는다(참고용도 아님).
    조건에 안 걸리면 빈 문자열을 반환한다.
    """
    reasons = []

    outside = set()
    for p in path_list:
        try:
            pp = Path(p)
            if not pp.is_absolute():
                continue
            if not str(pp).lower().startswith(str(project_dir).lower()):
                outside.add(str(pp))
        except Exception:
            continue
    if outside:
        sample = ", ".join(sorted(outside)[:5])
        reasons.append(f"cwd 밖 경로 접근: {sample}")

    obsidian_tools = sorted({t for t in tool_names if "obsidian" in t.lower()})
    if obsidian_tools:
        reasons.append(f"Obsidian/볼트 도구 사용: {', '.join(obsidian_tools)}")

    if not reasons:
        return ""

    return (
        f"> ⚠ **세션 범위 경고**: 이 세션은 cwd(`{project_dir}`) 밖 작업을 "
        f"포함할 수 있음 — {' / '.join(reasons)}. 아래 요약이 이 프로젝트와 "
        f"무관한 내용을 담고 있을 수 있으니 확인할 것.\n\n"
    )


def build_handoff(body: str, session_id: str, capture_iso: str, banner: str = "") -> str:
    header = (
        f"# HANDOFF\n"
        f"<!-- last-updated: {capture_iso} | session: {session_id} -->\n\n"
    )
    return header + banner + body.strip() + "\n"


# ══════════════════════════════════════════════════════════════════════════════
# #3  CAS write
# ══════════════════════════════════════════════════════════════════════════════
def write_handoff_cas(project_dir: Path, content: str, capture_iso: str):
    handoff_path = project_dir / "HANDOFF.md"
    my_ts = datetime.datetime.fromisoformat(capture_iso)

    if handoff_path.exists():
        try:
            head = handoff_path.read_text(encoding="utf-8")[:300]
            m = re.search(r"last-updated:\s*([0-9T:\-]+)", head)
            if m:
                existing = datetime.datetime.fromisoformat(m.group(1))
                if existing >= my_ts:
                    log.info("CAS: disk HANDOFF newer/equal, skip write.")
                    return
        except Exception:
            pass

    try:
        fd, tmp = tempfile.mkstemp(dir=str(project_dir), suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, str(handoff_path))
        log.info(f"HANDOFF.md written ({capture_iso})")
    except Exception as e:
        log.error(f"write_handoff_cas failed: {e}")
        try:
            os.unlink(tmp)
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
# CHILD
# ══════════════════════════════════════════════════════════════════════════════
def run_child(job_path: Path, force: bool):
    try:
        job = json.loads(job_path.read_text(encoding="utf-8"))
    except Exception as e:
        log.error(f"job read failed: {e}")
        try:
            job_path.unlink(missing_ok=True)
        except Exception:
            pass
        return
    try:
        job_path.unlink(missing_ok=True)
    except Exception:
        pass

    transcript_path = job["transcript_path"]
    session_id      = job["session_id"]
    project_dir     = Path(job["cwd"])
    current_lines   = job["current_lines"]
    capture_iso     = job["capture_iso"]
    cfg             = load_config()

    if not acquire_lock(project_dir, int(cfg["LOCK_TTL"])):
        return

    try:
        filtered, path_list, tool_names = filter_transcript(transcript_path)
        if not filtered.strip():
            log.warning("empty filtered transcript")
            return

        prompt = HANDOFF_PROMPT.format(transcript=filtered)
        log.info(f"calling Gemini ({cfg['GEMINI_MODEL']})...")
        body = call_gemini(
            cfg["GEMINI_API_KEY"], cfg["GEMINI_MODEL"],
            prompt, int(cfg["GEMINI_TIMEOUT"]),
        )
        if not body.strip():
            log.error("Gemini empty response")
            return

        try:
            banner = compute_scope_banner(path_list, tool_names, project_dir)
        except Exception as e:
            log.error(f"scope banner computation failed: {e}", exc_info=True)
            banner = "> ⚠ 세션 범위 점검 실패\n\n"

        content = build_handoff(body, session_id, capture_iso, banner)
        write_handoff_cas(project_dir, content, capture_iso)

    except Exception as e:
        log.error(f"child error: {e}", exc_info=True)
    finally:
        # #2: 성공/실패 무관하게 state 갱신 → 무한 재호출 차단
        write_last_lines(project_dir, session_id, current_lines)
        release_lock(project_dir)


# ══════════════════════════════════════════════════════════════════════════════
# PARENT
# ══════════════════════════════════════════════════════════════════════════════
def run_parent(force: bool):
    try:
        hook_input = json.load(sys.stdin)
    except Exception:
        hook_input = {}

    transcript_path = hook_input.get("transcript_path", "")
    session_id      = hook_input.get("session_id", "unknown")
    cwd             = hook_input.get("cwd", os.getcwd())
    project_dir     = Path(cwd)
    cfg             = load_config()

    if not cfg["GEMINI_API_KEY"] or cfg["GEMINI_API_KEY"] == "your_api_key_here":
        log.error("GEMINI_API_KEY not set in config.env")
        return

    if not transcript_path or not Path(transcript_path).exists():
        log.warning(f"transcript_path not found: {transcript_path}")
        ensure_handoff_stub(project_dir)
        return

    current_lines = count_lines(transcript_path)
    saved_sid, saved_lines = read_last_lines(project_dir)
    last_lines = saved_lines if saved_sid == session_id else 0

    if not force and (current_lines - last_lines) < int(cfg["LINE_THRESHOLD"]):
        log.info(
            f"debounce skip: +{current_lines - last_lines} lines, "
            f"session={session_id[:8]}"
        )
        return

    JOBS_DIR.mkdir(parents=True, exist_ok=True)
    fd, job_path = tempfile.mkstemp(dir=str(JOBS_DIR), suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({
            "transcript_path": transcript_path,
            "session_id":      session_id,
            "cwd":             str(cwd),
            "current_lines":   current_lines,
            "capture_iso":     datetime.datetime.now().isoformat(timespec="seconds"),
        }, f)

    spawn_detached_child(Path(job_path), force)
    # 즉시 리턴 → Stop hook <1s


# ══════════════════════════════════════════════════════════════════════════════
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="debounce 스킵 (PreCompact/SessionEnd)")
    p.add_argument("--job",   default=None,        help="(내부용) child stage job 파일 경로")
    args = p.parse_args()

    if args.job:
        run_child(Path(args.job), args.force)
    else:
        run_parent(args.force)


if __name__ == "__main__":
    main()
