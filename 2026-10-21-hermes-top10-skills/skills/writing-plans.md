---
name: writing-plans
description: "Write implementation plans: bite-sized tasks, paths, code."
version: 1.1.0
author: Hermes Agent (adapted from obra/superpowers)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [planning, design, implementation, workflow, documentation]
    related_skills: [subagent-driven-development, test-driven-development, requesting-code-review]
---

> Публикационная копия: санитизирована и сокращена для статьи
> «Топ-10 скиллов Hermes Agent на каждый день» (2026-10-21). Личные пути,
> внутренние проекты и приватные секции удалены; живая версия живёт в
> Hermes-профиле автора.

# Writing Implementation Plans

## Overview

Write comprehensive implementation plans assuming the implementer has zero context for the codebase and questionable taste. Document everything they need: which files to touch, complete code, testing commands, docs to check, how to verify. Give them bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume the implementer is a skilled developer but knows almost nothing about the toolset or problem domain. Assume they don't know good test design very well.

**Core principle:** A good plan makes implementation obvious. If someone has to guess, the plan is incomplete.

## When to Use

**Always use before:**
- Implementing multi-step features
- Breaking down complex requirements
- Delegating to subagents via subagent-driven-development

**Don't skip when:**
- Feature seems simple (assumptions cause bugs)
- You plan to implement it yourself (future you needs guidance)
- Working alone (documentation matters)

## Bite-Sized Task Granularity

**Each task = 2-5 minutes of focused work.**

Every step is one action:
- "Write the failing test" — step
- "Run it to make sure it fails" — step
- "Implement the minimal code to make the test pass" — step
- "Run the tests and make sure they pass" — step
- "Commit" — step

**Too big:**
```markdown
### Task 1: Build authentication system
[50 lines of code across 5 files]
```

**Right size:**
```markdown
### Task 1: Create User model with email field
[10 lines, 1 file]

### Task 2: Add password hash field to User
[8 lines, 1 file]

### Task 3: Create password hashing utility
[15 lines, 1 file]
```

## Plan Document Structure

### Header (Required)

Every plan MUST start with:

```markdown
# [Feature Name] Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

---
```

### Task Structure

Each task follows this format:

````markdown
### Task N: [Descriptive Name]

**Objective:** What this task accomplishes (one sentence)

**Files:**
- Create: `exact/path/to/new_file.py`
- Modify: `exact/path/to/existing.py:45-67` (line numbers if known)
- Test: `tests/path/to/test_file.py`

**Step 1: Write failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

**Step 2: Run test to verify failure**

Run: `pytest tests/path/test.py::test_specific_behavior -v`
Expected: FAIL — "function not defined"

**Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

**Step 4: Run test to verify pass**

Run: `pytest tests/path/test.py::test_specific_behavior -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## Writing Process

### Step 1: Understand Requirements

Read and understand:
- Feature requirements
- Design documents or user description
- Acceptance criteria
- Constraints

### Step 2: Explore the Codebase

Use Hermes tools to understand the project:

```python
# Understand project structure
search_files("*.py", target="files", path="src/")

# Look at similar features
search_files("similar_pattern", path="src/", file_glob="*.py")

# Check existing tests
search_files("*.py", target="files", path="tests/")

# Read key files
read_file("src/app.py")
```

### Step 3: Design Approach

Decide:
- Architecture pattern
- File organization
- Dependencies needed
- Testing strategy

### Step 4: Write Tasks

Create tasks in order:
1. Setup/infrastructure
2. Core functionality (TDD for each)
3. Edge cases
4. Integration
5. Cleanup/documentation

### Step 5: Add Complete Details

For each task, include:
- **Exact file paths** (not "the config file" but `src/config/settings.py`)
- **Complete code examples** (not "add validation" but the actual code)
- **Exact commands** with expected output
- **Verification steps** that prove the task works

### Step 6: Review the Plan

Check:
- [ ] Tasks are sequential and logical
- [ ] Each task is bite-sized (2-5 min)
- [ ] File paths are exact
- [ ] Code examples are complete (copy-pasteable)
- [ ] Commands are exact with expected output
- [ ] No missing context
- [ ] DRY, YAGNI, TDD principles applied

### Step 7: Save the Plan

```bash
mkdir -p docs/plans
# Save plan to docs/plans/YYYY-MM-DD-feature-name.md
git add docs/plans/
git commit -m "docs: add implementation plan for [feature]"
```

## Principles

### DRY (Don't Repeat Yourself)

**Bad:** Copy-paste validation in 3 places
**Good:** Extract validation function, use everywhere

### YAGNI (You Aren't Gonna Need It)

**Bad:** Add "flexibility" for future requirements
**Good:** Implement only what's needed now

```python
# Bad — YAGNI violation
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
        self.preferences = {}  # Not needed yet!
        self.metadata = {}     # Not needed yet!

# Good — YAGNI
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email
```

### TDD (Test-Driven Development)

Every task that produces code should include the full TDD cycle:
1. Write failing test
2. Run to verify failure
3. Write minimal code
4. Run to verify pass

See `test-driven-development` skill for details.

### Frequent Commits

Commit after every task:
```bash
git add [files]
git commit -m "type: description"
```

## Common Mistakes

### Vague Tasks

**Bad:** "Add authentication"
**Good:** "Create User model with email and password_hash fields"

### Incomplete Code

**Bad:** "Step 1: Add validation function"
**Good:** "Step 1: Add validation function" followed by the complete function code

### Missing Verification

**Bad:** "Step 3: Test it works"
**Good:** "Step 3: Run `pytest tests/test_auth.py -v`, expected: 3 passed"

### Missing File Paths

**Bad:** "Create the model file"
**Good:** "Create: `src/models/user.py`"

## Multi-Phase Plans & Cross-Task Consistency

When a plan spans multiple phases (migration, epics, ADR rollout), each phase is its own
document but they share types, protocols, and a dependency order. Defects here are subtle
and only surface when an executor (Codex / subagent) hits them mid-run. **Self-review the
plan BEFORE saving it** using the checklist below — every item is a real defect caught in a
production migration plan this session.

### Plan self-review checklist (run before saving)

- [ ] **Test/impl interface match.** If a task's test stubs a collaborator (e.g.
      `FakeClient.embed(...)`), the implementation in the SAME task must call that exact
      method. Mismatch (`embed` in test vs `.post()` in impl) makes GREEN unreachable.
      Prefer testing the real boundary (HTTP `post`) over inventing a secondary method.
- [ ] **No implicit cross-phase dependency.** If Task N says "reuse X from Phase M",
      Phase M must already define X, OR split the task: keep prep in the early phase,
      move the dependent step to a task in Phase M. Do NOT create a second implementation
      of X in the early phase "because Phase M isn't built yet" — that becomes dead/duplicate
      code to rewire later. (Variant A: early phase builds + integrity-checks; publication
      delegated to a later-phase unified publisher.)
- [ ] **Test data matches impl contracts.** A test asserting `check_compatible(a, b)` is
      `True` must construct `a` and `b` with identical fields (e.g. `model_revision`,
      `preprocessing_revision`). A helper with a default `revision=None` will fail the
      equality check — pass the explicit value in the test.
- [ ] **Dependency order stated per task.** Each task notes `Depends on: Phase X Task Y`
      so an executor can run phases in the right sequence (e.g. `1 → 2.5 → 2 → 3 → 4 → 5`).
- [ ] **One mechanism per concern.** If Phase 3 already has atomic publish, Phase 2.5 must
      NOT add its own; it prepares staged data and defers to the Phase 3 publisher.

### Phase document structure

For multi-phase work, also create `docs/plans/<topic>-index.md` listing each phase file,
its dependency, and a recommended execution order. Keep an acceptance gate at the end of
each phase; do not advance until that phase's gate is green.

## Markdown plan legibility

Long single-line markdown (tables, prose) hurts `git diff`, line review, and conflict
resolution. Reformat for line-based review — BUT preserve code blocks verbatim and keep
table rows atomic. Technique + script: see
[`references/markdown-plan-formatting.md`](references/markdown-plan-formatting.md).

## Execution Handoff

After saving the plan, offer the execution approach:

**"Plan complete and saved. Ready to execute using subagent-driven-development — I'll dispatch a fresh subagent per task with two-stage review (spec compliance then code quality). Shall I proceed?"**

When executing, use the `subagent-driven-development` skill:
- Fresh `delegate_task` per task with full context
- Spec compliance review after each task
- Code quality review after spec passes
- Proceed only when both reviews approve

### Executing multi-phase plans through Codex (one phase per call)

If the executor is the **Codex CLI** (not subagents), run phases **sequentially** —
one `codex exec -m gpt-5.6-terra --sandbox danger-full-access -C <repo> "<narrow prompt>"` per phase,
`background=true, notify_on_complete=true`. Never parallelize (shared source tree).
Do NOT push until all phases complete and the user audits. Independently re-run the
test suite and read back created files after each phase — do not trust the agent's
self-report. Exact invocation, prompt template, and verification gate:
[`references/phased-codex-execution.md`](references/phased-codex-execution.md).

## Acceptance-criteria verification (anti-scaffolding trap)

### Isolate data-loss / critical P0 fixes from the rest of the commit series

When an audit finds a **destructive** defect (e.g. sync that drops previously-indexed
documents, a publish that corrupts the active revision), close it ALONE first — do not mix
it into the same codex/subagent batch as unrelated phases (MCP transport, manifest
unification, indexing, adaptive-loop wiring). Reason (user decision, Auto-RAG migration):
a non-destructive-fixed commit series that *also* touches many modules risks shipping a
second latent bug into the same snapshot the P0 was supposed to protect. Sequence:

```
6.1 critical P0 (isolated, codex, local commits) → push → USER re-audit sync semantics
→ only then 6.2 … 6.N (remaining phases)
```

- Run the critical fix as its own `codex exec -m gpt-5.6-terra` call with a narrow prompt limited to that
  one concern; the prompt must say "ONLY the P0-X section, do NOT touch other phases".
- Write **state-transition tests**, not just method-unit tests (see Destructive-safety
  below): `initial A,B,C → add D → A,B,C,D`; `change` as upsert; `delete` last-wins;
  combined change+add+delete; failed publish preserves prior active revision; idempotent
  redelivery; conflicting ids; corrupt previous revision; source isolation.
- Push, then STOP and wait for the user's separate re-audit before continuing. Treat the
  re-audit as a gate, not a formality.

**RED→GREEN on isolated unit tests does NOT prove the plan meets its stated goal.**
A TDD plan executed by Codex/subagent will reliably produce green unit tests AND still
fail architecture acceptance criteria — because each task tests its own module in
isolation, and the cross-component contracts that the ADR actually requires are never
asserted. This session shipped 42 commits, 71 gateway tests green, then an audit found
**2 P0 + 6 P1** the unit tests never caught (destructive incremental sync, fake MCP
transport, plan-computed-but-ignored, faked availability, corrupted evidence origin,
three divergent manifest schemas, no persistence, no real index build).

**Add an explicit acceptance-verification step to EVERY plan that claims to implement
an ADR / architecture / multi-component spec.** This is separate from per-task RED→GREEN.

### Acceptance verification gate (add at end of each phase / plan)

Before claiming "done", write and run tests that assert the ADR's stated criteria, not
just module internals:

- **Cross-component wiring:** if component A is supposed to drive component B, assert
  B actually receives A's output (e.g. `QueryPlan` fields are read by the coordinator;
  a `web` connector is NOT called when `include_web=False`). Unit tests inside A will
  pass even when B is never invoked — that gap is the bug.
- **Contract unity:** if "one mechanism" is required, assert the same store/path is used
  by all writers (e.g. SyncEngine, RevisionPublisher, IndexManifest all read/write the
  SAME manifest schema + file). Divergent schemas = silent second implementation.
- **Persistence across restart:** if state must survive, kill and reload the process /
  store and assert state survived (in-memory lists are not persistence).
- **Real transport, not toy:** if "MCP-compatible" is claimed, assert `initialize` /
  `tools/list` / `tools/call` exist with JSON Schema; a custom JSON-RPC that only the
  project's own test client speaks is NOT the claimed protocol.
- **Destructive-safety:** for any sync/index/revision system, assert incremental update
  does NOT drop previously-synced documents (carry-forward + tombstones), and a failed
  publish leaves the prior revision active.

### How to write these tests

They belong in `tests/` as integration tests (not inside the per-task TDD cycle). They
often require constructing two collaborators and asserting the interaction, or reloading
state. Mark them clearly (e.g. `test_audit_p0_incremental_sync_non_destructive`). They
should FAIL on the scaffolded implementation and PASS only when the ADR contract holds.

Full pattern + the real P0/P1 list this session produced:
[`references/adr-acceptance-verification.md`](references/adr-acceptance-verification.md).

**Rule of thumb:** if your plan's tests only ever call one module at a time, the plan
is verifying implementation, not acceptance. Add the cross-component tests or the audit
will find them for you.

## Remember

```
Bite-sized tasks (2-5 min each)
Exact file paths
Complete code (copy-pasteable)
Exact commands with expected output
Verification steps
DRY, YAGNI, TDD
Frequent commits
Acceptance-criteria verification (not just RED→GREEN)
```

**A good plan makes implementation obvious — and proves the ADR contract holds.**
