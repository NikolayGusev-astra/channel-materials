---
name: agent-workflow-gates
description: Build agent workflows with mechanical gates, not prose.
version: 0.1.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [workflow, gates, dod, verification, orchestration, design]
    related_skills: [ontonet-ops, kanban-orchestrator, hermes-bot-mode-roster]
---

# Agent Workflow Gates

Design a business process so an agent executes it repeatably across sessions, restarts and
model changes. The load-bearing idea: **a gate is a permission check, not a sentence.**
Prose is lossy under context compaction; a permission is not.

## The one rule everything else follows from

**Tell the agent only what is correct. Never what is incorrect.**

A negative instruction ("don't delete the schema", "never write to prod") is weaker than the
positive form and actively harmful: it puts the forbidden token into context, and after a few
compactions the surviving fragment reads "delete the schema — wrote it, must be true" — the
prohibition has inverted into a permission. Model the correct action instead and let the
incorrect path be unavailable.

Corollary: **you cannot prompt your way out of a missing capability.** If the wrong action must
be impossible, remove the permission — file ACL, read-only mount, token scope, server-side
authorization. Prose only carries context and rationale; enforcement lives in mechanics.

## Layered shape

| Layer | Holds | Where it lives |
|---|---|---|
| Outcome | terminal result + verifiable end state | the DoD |
| Steps | deterministic actions | scripts, not model decisions |
| Gates | transitions requiring external authority | permissions, API facts, human sign-off |
| State | where the process is | DB keyed by run, not by session |
| Verification | proof the step happened | deterministic check, not a claim |

## Procedure

0. **Prove the gate blocks, and enumerate what the system distinguishes.** Attempt the transition
   the gate claims to forbid, using the credentials the blocked party actually holds. A state
   diagram, a role name, or a vendor doc asserting "only a reviewer can do this" is a hypothesis.
   Then close the other side of the question by asking the system what it *distinguishes* — which
   roles, principals, or scopes exist. A successful call with your own key proves only that your key
   is permitted; it says nothing about whether a less-privileged one exists. Never report "there is
   no check here" as a finding: report which role you hold and what it permits. Both directions, or
   you have not tested the gate.

1. **Start from the done state, unroll backwards.** Write the final verifiable result first,
   then derive each preceding step and the gate that admits to it. Describing a process
   forwards from a task statement reliably produces steps with no completion criteria.
   Ask of every step: *what observable fact proves this ran?* No answer means it is not a step,
   it is a hope.

2. **Split determinism from judgement.** Anything a script can do (create accounts, call REST,
   mutate a record) is a script. The model routes, fills parameters, and talks to people.
   Never let the model be the thing that retries or re-derives a deterministic action.

3. **Make every step idempotent and fact-checked.** "I called the create endpoint" is not
   proof. Verify the object exists afterwards, and treat "already exists" as success, not
   error — otherwise a resumed run after a crash reports phantom red. Without this, a repeat
   run silently double-applies or falsely alarms.

4. **Gate on API facts, never on text.** A quiz passed, an approval granted, a webhook
   delivered — pull it from the system of record. If a gate can be satisfied by the agent's own
   statement, it is not a gate.

5. **Put human gates at transitions, not at the end.** Blocking mid-process keeps partial work
   intact and the state in the DB. Gate the irreversible or outward-facing step (publish,
   delete, spend, notify externally) before it happens.

6. **Persist state outside the session.** A process lasting days must survive session death.
   Store run state in a DB keyed by run id; keep the session as a view, never as the store.
   A process whose only record is the transcript has already ended.

7. **Verify with a deterministic metric chosen per result type.** Same-shaped outputs need
   different checks: pixel statistics for image properties, embedding cosine for identity,
   HTTP status and schema for API results. A vision-model judgement is appropriate for
   semantic content and wrong for numeric thresholds — pick per output, and say which.

8. **Audit the trail.** Who performed the transition, when, at which revision. Needed the
   first time someone asks why the process did that.

## Pitfalls

0. **A rule you can only honour by remembering it is a gate you forgot to build.** The cheapest
   test for any destructive action against a live external system: could the same outcome be
   produced by a loop instead of a single deliberate call? If yes, the action needs its argument
   parser to reject collections. A `edit` script that accepts `200-400` will eventually be
   handed `200-400` — by you, in the same session, while diagnosing something else, because the
   range was the obvious way to ask "which of these are mine?". Constrain the *shape* of the
   argument, not the intention behind it: one id, parsed as an int, nothing that resembles a
   range, plus a `--expect` sentinel checked against the target's current content so "wrong
   target" is unrepresentable. Write first by default; `--apply` is what mutates.
   Permission removal is the stronger sibling: when the owner can revoke the capability that
   made the mistake destructive (message deletion, resource delete), take that away rather than
   wrapping the same capability in a better script. Report which role the credential holds and
   what it permits, and say plainly that an operation the key cannot perform needs no guard.

1. **Checklist in a persona file is not a procedure.** SOUL.md, AGENTS.md and system prompts
   load as context every session; the agent is not obliged to traverse them, and they die with
   the session. Use them for role and rationale, never for step order or completion criteria.

2. **A lifecycle is not a gate. Roles are.** `draft → submitted → accepted` on someone's
   server is a well-formed audit trail; whether the writer can walk it to the end depends entirely
   on which role its key carries. Enumerate the roles the system actually has, give the writer the
   lower one, and reserve the closing transition for the higher. If only one key exists, say so
   plainly in the design instead of implying a boundary that isn't there — and equally, do not
   claim the system lacks a boundary just because one key was allowed through. The two mistakes are
   the same mistake: inferring the permission model from your own experience of it.

3. **Interleaving state and logic in prose.** DoD entries must be machine-checkable to be worth
   storing; a free-text criterion drifts into unverifiable on the first compaction.

4. **One agent where isolation matters.** Split profiles when credentials, access method, or
   blast radius differ between steps — contamination risk lives in shared context and shared
   tokens, not in the model. Splitting is only meaningful if the tokens actually differ; two
   profiles sharing one key are one boundary on paper.

5. **Do not encode prohibitions to compensate for absent permissions.** That is the failure
   mode above seen from the other side: the sentence is doing the job the ACL should do.

6. **A publish step has no draft mode, and that is the real gate risk.** Some targets make the
   artifact public the instant the create call returns, with no private-then-publish sequence. For
   those, the reversible human gate is publishing under a visibly-marked draft title at a
   throwaway URL, and the DoD for the last step becomes "the draft is clean" (markers stripped,
   secrets absent, payload shape verified) rather than "published". Choose the DoD by what the
   target can actually guarantee, not by what the process wishes for.

7. **Concluding a capability is missing from one failed interface.** A vendor may ship two
   layers that disagree; one rejecting a payload says nothing about whether the other accepts it.
   Replay the identical payload on the alternative before reporting a limit — and never turn a
   single opaque error into a standing "this API does not allow X", which later agents cite as
   settled fact and refuse to re-test.

8. **Re-deriving an id you were just handed.** When a create call returns the id of what it
   created, carry that id into the next step. Re-reading it through a lookup that filters by
   status will miss a freshly created object and read as "the write failed" — and if the provider
   hides unaccepted objects from every search, the chain stops with "not found" rather than an
   error. Persist the id to run state at creation time; a lookup that only sees committed rows is
   not an identity service.

9. **Letting the DoD be a claim instead of a measurement.** "Published" and "done" are
   unverifiable on their own. Every step's DoD must be something a script reads — a status field, a
   file's bytes, a counter in the target system, a marker count in the returned HTML. The
   verification call is the step; the DoD is what it compares against.

10. **A gate that re-reads the same thing the step wrote, through a different path, is not a
    gate — it is a second opinion that can disagree.** A step whose output the gate confirms by
    re-deriving it is fine; a gate that confirms by looking somewhere else (a cache, a status file,
    a `changed` flag, a task's own rc) inherits every gap of that other path, and the step and the
    gate will eventually disagree with the world. **The gate must read the artifact the step
    actually mutated** — the CIB, not the exit code; the table, not the API's "ok".

11. **The most dangerous gate failure is a gate that cannot fail.** Three shapes produce a step
    that reports success while doing nothing, and all three are silent:
    - **A gate that counts emptiness and reads it as conformance.** Grepping a state store for
      resource-like strings and finding none is indistinguishable from "the store is clean" — the
      grep is equally happy when the store was never written. Assert on the positive count you
      expect, never on the absence of an error string.
    - **A tool invocation whose failure is swallowed.** `failed_when: false` on a step whose tool
      is missing from PATH turns a hard error into a green task. A step that must succeed gets a
      real `failed_when`; a genuinely best-effort step is marked as such in its name, because
      nothing else distinguishes the two later.
    - **A gate placed before the step it checks.** A gate that runs before the action verifies a
      state that has not been produced yet — it either passes vacuously or fails on the very thing
      it is meant to confirm. Gates come after the action they gate.
    A step's own success flag is evidence about the *process*, never about the *world*; only
    re-reading the world proves the world changed.

12. **Assert the precondition's applicability, not just its value.** A correct assertion run on
    the wrong subject is a false pass. A gate inspecting local state must first ask whether *this*
    node is the node that owns the thing — replicas, promoted/secondary pairs, and role-bound
    resources are distributed, and the "correct" value on a non-owner is a different value or no
    value at all. Cluster roles (`Master`/`Primary` vs `Slave`/`Secondary`) are the usual trap: the
    assertion is right and the node is wrong, so it fails on a perfectly healthy system.

13. **A verification command that takes a lock is not a verification command.** Some tools
    serialize on a lock and block indefinitely when the resource is live (device-metadata and
    cluster-configuration tools both do this). Wrapping them in `timeout` is the minimum; choosing
    a read-only alternative (a status query that needs no lock) is the fix. A gate that can wedge the
    system it is gating has no timeout budget, no exception, and hangs the run instead of
    reporting.

14. **A gate added next to the prose it replaces is a suggestion.** The usual fix for a
    destructive-action rule is to write a script *and* keep the sentence, so the script documents
    a rule the model already read and may reasonably follow the cheaper one. Delete the prose in
    the same edit: a future session cannot tell which of two instructions the author's intent was,
    and picks the one that costs no subprocess. When a rule gets a gate, the skill entry becomes
    the invocation - `python scripts/x.py <id> --expect <marker> --apply` - plus the reason the
    prose existed, never the prose plus the invocation.

15. **The step that performs an action writes its own id to the mapping.** A separate bookkeeping
    call ("now record what we just created") is a step the agent can skip or defer, and after an
    incident the missing rows are exactly the ones needed to recover. Fold the write into the same
    script that performed the action, after its own verification, so the mapping is a by-product of
    success rather than a task. Make it lookupable by the recovery path that needs it, and have the
    lookup for an unknown id say plainly that recovery is impossible - never return a near match,
    because a confident wrong mapping during an incident rewrites the wrong object.

16. **A publish pipeline's step count is the risk.** When every artifact needs hand-typed commands
    (sync, commit, push, run-server-script, curl-verify), each is an unverified boundary and a
    warning printed into a stdout stream sails straight through to the next command. Collapse the
    sequence into one script that stops at the first failed check, and promote each intermediate
    warning to an explicit assertion: "the sync printed `ВНИМАНИЕ:`" must be a refusal, not
    something the next command tolerates. A step that cannot fail the run is not a step.

17. **A mapping keyed by the wrong half is not a mapping.** If the recovery path needs "which object
    corresponds to this published id", a registry keyed by publication date or directory name cannot
    answer it - only the id the target system itself returned can. Key on that, and let the lookup
    say "impossible" otherwise.

18. **In a rule engine, a default tier is a fallback, not a baseline — a matched specific rule
    beats it even when the rule's number is lower.** Starting `best = default` and updating only
    when a rule's rank exceeds the default's means a T0 match for a README never displaces a
    default T2: the classifier silently returns T2 for the one artifact the default was never meant
    to govern. Default applies only when NOTHING matches; once any rule matches, the result is the
    max of the matched set. And a triviality check ("only docs / an extension") must run AFTER
    the classifier and must NOT downgrade a hit on an explicitly critical rule — a `docs/SKILL.md`
    that matches a critical pattern is critical, not auto-approvable; the cheap heuristic never
    overrides the specific rule. Test both directions on a live artifact before shipping the engine.

19. **Audit a suspicious render through geometry, not through a second unreliable reader.** When a
    rendered output looks wrong to a cheap judge (a vision model reports garbled glyphs or clipped
    text), the judge's verdict is not evidence — the same model that produced the report is
    hallucinating from downscaling, and it gives no coordinates you can act on. Verify layout with
    deterministic geometry on the real artifact: compute block widths, text lengths at the actual
    font size, edge-pixel darkness at the documented canvas scale. If the numbers say the text fits
    and the glyphs are clean code points with no replacement characters, the layout is fine no
    matter what the blurry thumbnail suggested. Trust the measurement; distrust the unanchorable
    claim.

## Verification

- Every step has an observable fact that proves it, and a check that reads that fact.
- Re-running the whole process from a clean state produces the same result and no duplicates.
- Killing the process mid-run and resuming does not repeat a completed step.
- No gate can be passed by the agent's own say-so.
- Every claimed gate was attempted with the blocked party's credentials and observed to fail.
- No gate shares its read path with the step it checks; each reads the artifact the step mutated.
- Every gate can fail: prove it by breaking the precondition and watching the gate go red.
- Every gate that inspects local state has established it is running on the owning node.
- Every gate is ordered after the action it gates, and every state-reading call is bounded by a
  timeout or chosen lock-free.

## References

- `references/stale-artifact-after-source-fix.md` — why a clean audit of a patched generator is not
  evidence about the artifact built from the old one, and the rebuild-then-verify order that
  closes it.
- `references/onto-as-gate-provider.md` — OntoNet's MemoryArtifact lifecycle as a state-and-audit
  backend: the artifact contract, verified transport quirks, and a worked correction of the claim
  that the lifecycle is an authorization boundary (it is not, with a single key).
- `scripts/onto_gate.py` — working client (draft / submit / status / audit / list / supersede)
  against that provider; persists the artifact id and deliberately omits `accept`.
- `references/state-file-when-the-api-hides-drafts.md` — why an id returned by a create call must
  be written to local run state, and the working recipe when every server-side lookup filters to
  committed rows only.
- `scripts/telegraph-verify.py` — verification half of a publish gate: audits an
  already-published Telegra.ph page by path (typography, markdown leftovers, leak
  patterns, draft marker) and exits non-zero unless every check passes. Creates
  nothing, so it is safe to re-run; re-running a *publisher* to verify spawns a
  duplicate page.
