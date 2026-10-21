---
name: research-before-build
description: Find prior art before coding any new tool or algorithm.
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [research, architecture, prior-art]
    category: software-development
---

> Публикационная копия: санитизирована и сокращена для статьи
> «Топ-10 скиллов Hermes Agent на каждый день» (2026-10-21). Личные пути,
> внутренние проекты и приватные секции удалены; живая версия живёт в
> Hermes-профиле автора.

# Research Before Build

## Trigger

About to write a new utility, tool, plugin, converter, algorithm - anything
non-trivial. STOP. First answer: who solved this already?

User lesson (typewriter-t9, 28.08.2026): hand-rolled a spellchecker+layout
converter while Punto Switcher solved it in <1MB in 2001 with a better
algorithm. The user's response: "человек бы открыл гугл и спросил как работает
punto switcher". Do not repeat.

## Procedure

0. **Recover evidence and widen the survey before proposing work.** Read the project's prior plans, result reports and validity caveats first; classify each experiment as completed, exploratory, invalid or pending. Then search current releases and competing mechanisms beyond the names in the handoff. Internal evidence and fresh external research are both required: a handoff is neither the full experiment history nor a current technology survey. Check the incumbent application's actual defaults before describing an available feature as a new optimization. Do not turn compatibility checks or routine flag tuning into research contributions when the user asks for nontrivial acceleration.

1. **Principle search** (before any design):
   - RU: `<tool> принцип работы`, `<tool> как устроен архитектура`
   - EN: `how <tool> works internals`, `<tool> algorithm`
   - Read Wikipedia article if exists - history sections name algorithms.
2. **Prior art search**:
   - `github <tool> open source`, `github <task> implementation`
   - Alternatives lists on the Wikipedia page = free architecture survey.
   - Old small tools often beat modern frameworks: check 2000s utilities.
   - For papers and code, query the canonical APIs directly (arXiv
     `export.arxiv.org/api/query`, GitHub `search/repositories` and `/repos/<owner>/<repo>`):
     they hand back ids, dates, licences and activity you can cite in a document, and they
     resolve a name to a URL without a detour through prose. A general web index is for
     orientation only — it drifts into localised SEO and aggregator pages and cannot tell you
     whether the artifact exists.
3. **Extract the real algorithm**, not the feature list. Example (Punto
   Switcher): NOT "dictionary of words" but keyboard hook + statistical
   bigram/trigram typicality check + Backspace-emulation re-typing.
4. **Steal structure, not code** (license check first: GPL vs MIT vs closed).
5. **Only then** write code - and cite which prior art each tricky part
   follows.

## Verify the artifact, not the announcement

A paper that promises to open-source its tool, a README that links somebody else's repo in
its comparison table, and a repo with no commits in eighteen months are three different
answers to «the prior art exists». Before an external tool enters a plan, open its URL and
confirm three things: the code is actually there, the license file is present and named, and
the last commit is recent enough to trust. The phrases that mean there is nothing to adopt
yet are «we will open-source», «coming soon», and a name that appears only in a related-work
table — take the design idea from those and pick a working tool instead. A stale repo is
still readable as an idea, but it is not a dependency.

Verify by API, not by prose: a repository search, the repo object (`license.spdx_id`,
`pushed_at`, `language`) and the raw README answer all three questions in one pass, and they
answer them with what the host reports rather than with what the paper claims.

**Model weights get the same treatment.** «Open weights» on a card is marketing, not a
licence: open the `LICENSE` file and read the commercial and derivative terms before a plan
depends on fine-tuning, LoRA adapters, or paid serving. The card can say «free for
non-commercial use» while the licence adds «commercial use by agreement» and a different
upstream licence for the base model — three separate constraints that decide whether an
adapter or a hosted product is permissible at all, so quote the licence, never the tagline.
The repository tree answers what the card omits and what a local-run plan needs: shard count
and byte sizes, a separate MTP or speculative-decoding head, the tokenizer and chat template,
and the `language:` list that shows which language the vendor never tested. Fetch both before
promising anyone a local setup.

## Prior art is also the team's own in-house automation

The search is not only external (`github X` / vintage tools). When the class of
task is agent/workflow automation and a *team you work with already built the same
thing* — an ML/code-review program, a pipeline, a gateway — that stack is prior art
too, and usually more relevant than anything open-source: it shipped, carries the
field's real defect catalog, its eval corpus is already labeled and adversarially
checked, and its static layer (ladder-of-tiers, approval norms, mechanics) ports
directly to your domain. Enumerate what they built and clone the components that
fit (MCP bridge, review loop, eval seed, approval norm, tier ladder) instead of
writing your own prod loop.

Boundary that keeps this honest: **own code is for eval and spec, prod path reuses
the shipped component.** Writing your own runner to *measure* models on your corpus
is justified (their eval harness may be closed). Taking that runner into *production*
review when their reviewed tool exists is the wheel — the user's standing check is
`а не велосипед ли мы изобретаем?` and the honest answer names the shipped
component you are porting, not the code you wrote. A bench script is a measurement,
not a mandate to reimplement the cycle. See `local-llm-evaluation` tiering reference
for the port table.

## Filter candidate tools by environment constraints first

When the survey compares ready-made tools against a hand-built pipeline, run the hard
environment filter BEFORE any feature matrix: self-hostable, runs on an arbitrary
OpenAI-compatible endpoint, integrates with the actual forge/infra (e.g. Bitbucket Data
Center, not GitHub). A candidate that fails a hard constraint is out regardless of its
benchmark numbers — vendor pages bury constraints under features, so verify the
integration in docs or source, not on the landing page.

And name which layer a candidate replaces. Hand-rolling the measurement layer (golden
corpus, honest scorer, protocol parity) is legitimate; the iteration layer (propose
edits, probe variants, compose the winning config) is a solved class — prompt
optimizers (DSPy/GEPA) and eval harnesses (promptfoo) — and a private rebuild there is
the same wheel as a private review loop.

## The verdict goes into an ADR with a benchmark checklist, not into chat prose

When prior art is confirmed for something already under construction, the deliverable
is an ADR in the project's `adr/` dir (next number, status proposal), not a chat answer.
Structure it so the decision becomes measurable: how the prior art works internally
(from its source, not its README), what its own equivalent of your deterministic layer
is and how it differs, what stays yours (gates, eval corpus, measured recall, model
union) and what gets ported from the ready component. End with a checklist whose cells
stay empty: run the prior art on the project's own held-out golden set and fill recall
in against your recorded baseline. An unmeasured "we keep ours" claim is taste; the
same claim with a recall number is an argument. Keep the local-LLM constraint in the
risks section: a tool built for strong cloud models is not validated on a local 8B.
Benchmark under protocol parity, or the numbers are not comparable: same held-out
corpus, same scorer and counters as the baseline runs, same chunking/limits, and NO
extra hints (must-fix lists, extra instructions) unless the baseline had them —
feeding the prior art secrets your baseline never saw buys speed, not a verdict.
Run the prior art out of the box first (its own rubric); a tuned second pass is a
separate arm, never the headline number.

For performance research, select a domain-appropriate success metric rather than copying review recall: completed correct work per wall-clock interval, latency and quality may be the relevant outcomes. Account for any proposed model-based coordinator in the same compute and memory budget; use deterministic replay when the question concerns scheduling rather than orchestration intelligence. Consult `references/performance-research.md` for artifact selection, comparison parity and plan cleanup.

Before GPU trials, identify the available artifacts and run a short operational compatibility check: model loading, completion, actual drafting counters, resource fit and transport stability. Define the gate from the research question, not from an incidental diagnostic. For serving-performance research, model quality is a controlled input, not a new model-ranking project: reuse the frozen task scorer uniformly, count failed tasks, and continue measuring admitted configurations. Record differences in full outputs (including reasoning/tool calls) as limits on lossless claims; do not make byte-identical reasoning or a pilot JSON-format failure a prerequisite for measuring serving throughput unless exact equivalence is explicitly the experiment's objective. A model card does not replace task scoring, but neither does the scorer justify diverting into a separate quality study.

When authorized to execute the complete experiment, continue through the agreed matrix, aggregation and audit without yielding after each pilot or treating status reports as completion. A diagnostic failure closes or qualifies the affected claim/arm, not the entire program; continue independent runnable arms. Stop only for a genuine safety/resource/access blocker or a required user decision. Announce a long-running job as started, never as finished; carry verification and result consumption through to the final deliverable. Before launching, audit the runner against the frozen protocol so urgency does not replace a missing mixed workload, dependency trace or declared metric with a convenient approximation.

## Your own earlier analysis is prior art too

The search is not only for systems other people wrote. When the user says the
session was lost, «you forgot the context», or asks about something you already
worked on, the first move is not to re-derive the answer from scratch — it is to
lift the artifact: project folder, plans, `session_search` on the topic. A written
conclusion is stored evidence about this codebase, and re-deriving it burns the
turn and often produces a *worse* answer, because the first pass had sources you
no longer have in context.

Two rules follow:

- **Restate nothing you have not re-verified.** A conclusion written earlier was
  true against the state of the world *then*. Before repeating it, re-check against
  the live source (current releases, changelog, upstream HEAD). Engine and library
  backends change per release; a negative capability claim has a shelf life of
  roughly one release.
- **When a live source refutes what you wrote before, fix that sentence in place**
  in the document rather than appending a correction underneath it. Replacing a
  refuted claim with the correct one plus the surviving caveats keeps the decision
  trail usable; an "UPDATE: actually…" strip or a silent deletion loses why the
  design was chosen.

## Prior art includes the binaries already on this host

The cheapest search precedes the web one: enumerate what is installed. A hand-rolled
secret scanner lived next to `gitleaks`, and `semgrep`, `ruff`, `shellcheck`,
`bandit`, `trivy` were all already on PATH. One call answers it:

```python
import shutil
for t in ("gitleaks", "trufflehog", "semgrep", "ruff", "shellcheck",
          "bandit", "trivy", "cloc", "pygount"):
    print(t, shutil.which(t))
```

Before writing any analyzer, scanner, linter or complexity metric, run that list. A
ready tool wins on the depth of its defect catalog, not on features; your version
re-discovers its bugs one incident at a time.

**PATH is not an inventory.** `shutil.which` (and `command -v`) sees only what is on
PATH, and a host can carry a full CUDA build of the same engine in five places without
a single symlink. Measured failure: «llama.cpp is not installed» concluded from
`command -v llama-server`, right before a sweep found a standalone llama.cpp with
`ggml-cuda.dll` and the CUDA 13 runtime under a project dir, plus five CUDA builds
shipped inside LM Studio's `~/.lmstudio/extensions/backends`. Two traps stack here:
ripgrep-backed file search **skips hidden directories** by default (`.lmstudio` never
appeared in results), and a file that exists may still be unusable — the LM Studio copy
of `llama-server.exe` exits 0 and prints no `--version` because it is a stub for that
app's own engine protocol. So: sweep the disk with a shell `find` (the ripgrep-backed file search skips dot-dirs,
so a whole class of bundled runtimes is invisible to it), then call
the binary's `--version`/`--help` before believing either the absence or the presence.
An application's bundled engine runtime counts as prior art too, once it is shown to run.

**Then name the residue before buying a model.** The deterministic layer (linters,
gates, size/tier rules, an embedding-plus-logistic screen) costs zero tokens. Say out
loud which classes survive it, and only then add an LLM stage. On the review corpus the
survivors were exactly the semantic ones — false green, regression introduced by the
patch itself, a test that pins nothing — which no linter can see. That sentence is the
justification for the model layer; without it the model stage is decoration, and the
honest answer to «может, я переусложняю?» is to point at which stage is the excess.

## Anti-patterns

- Building a naive version "to have something working" when a 20-year-old
  proven design exists.
- Hand-rolling lookup tables (QWERTY↔ЙЦУКЕН, translit maps) that ship inside
  every open source clone.
- Skipping the search because "the task sounds simple".
- Writing your own version of a tool that is one `shutil.which(...)` away — check the
  host's PATH before the web.

## Physical Cleanup

Distinguish superseding research plans from physically deleting downloads, caches, or duplicate environments; state exactly which cleanup occurred. Use package-manager cache commands, preserve shared models and working environments, and report the measured free-space delta rather than summed logical sizes: hardlinks can make these differ. Do not attribute an unexplained discrepancy to hardlinks as a verified cause without checking.

## Rule of thumb

If you cannot name two existing programs that do the thing and one line about
HOW each does it - you have not researched yet.