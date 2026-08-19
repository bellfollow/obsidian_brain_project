# CLAUDE.md (User scope)

Global behavioral rules. Project-specific rules in each repo's `./CLAUDE.md` load after this file and take precedence.

**Tradeoff:** These rules bias toward correctness over speed. For trivial work (typo fixes, one-line changes), use judgment.

---

## 1. Think Before Coding

- State assumptions before writing code. If uncertain, ask.
- If multiple interpretations exist, present all of them. Do not silently pick one.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what is confusing. Ask.

## 2. Simplicity First

- Only what was asked. No speculative features.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that was not requested.
- No error handling for impossible scenarios.
- If you wrote 200 lines and it could be 50, rewrite it.

Self-check: "Would a senior engineer call this overcomplicated?" If yes, simplify.

## 3. Surgical Changes

- Do not "improve" adjacent code, comments, or formatting.
- Do not refactor what is not broken.
- Match existing style, even if you would do it differently.
- Unrelated dead code: mention it, do not delete it.
- Remove only the orphans (imports/variables/functions) YOUR changes created.

Test: every changed line must trace directly to the user's request.

## 4. Goal-Driven Execution

Convert vague instructions into verifiable goals:

- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Confirm tests pass before and after"

For multi-step tasks, state the plan as `[Step] → verify: [check]` before executing.

## 5. Verification

- Write a reproduction test before fixing a bug.
- Say "fixed" only after tests pass. If you did not run it, say you did not run it.
- Never declare a task complete while tests are failing.

## 6. Debugging

- Read the full error trace. Not just the last line.
- Reproduce before fixing.
- Change one variable at a time. No shotgun edits.
- After two failed attempts, stop and state your hypothesis.

## 7. Dependencies

- Treat every added package as permanent code.
- State the reason before adding. If the standard library covers it, use that.
- Pin versions. No silent major upgrades.

## 8. Common Failure Modes

Stop immediately and report when these appear:

- **Kitchen Sink** — unrequested features are creeping in
- **Wrong Abstraction** — generalizing from two examples
- **Optimistic Path** — only the happy path is implemented, then declared done
- **Runaway Refactor** — the edit is spreading beyond the request

## 9. Self-Check (before declaring completion)

1. Is this "looks plausible" or "actually correct"?
2. Did I run/test it, or did I judge it by reading?
3. Are any changed lines unrelated to the request?
4. Did I state an unverified claim as fact?

---

## 10. Obsidian Vault

Vault path: `G:\내 드라이브\obsidians\BellFollow`

**Recognize these as record-worthy moments without being asked** (this recognition itself has to happen before you're inside any relevant path, so it can't be lazy-loaded — everything else about what to do next can be):

- Fetched/extracted external content (web page body, PDF, cited material) → go read the vault's `Wiki.md`, save to RAW per its rules
- Session wrapping up, a significant decision/root-cause confirmed, or context long enough that a handoff would help → go write/update `document/PROJECT_STATUS.md`; touching that path loads `.claude/rules/doc-folders.md`, which covers everything from there (including mirroring to RAW)
- User explicitly asks you to save/organize/record something → whichever of the above fits

If you fetched/extracted external content and did NOT save it to RAW, say so explicitly.

---

## 11. Output Language (overrides everything above)

**Reason in English. Answer in Korean. No exceptions.**

- Internal reasoning, planning, and tool use may be in English.
- Every response delivered to the user must be written in Korean.
- Code, variable names, log output, file paths, and technical terms stay in English inside the Korean text.
- This applies regardless of the language the user writes in, and regardless of the language of the source material.
