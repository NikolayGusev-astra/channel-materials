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

# Research Before Build

## Trigger

About to write a new utility, tool, plugin, converter, algorithm - anything
non-trivial. STOP. First answer: who solved this already?

User lesson (typewriter-t9, 28.08.2026): hand-rolled a spellchecker+layout
converter while Punto Switcher solved it in <1MB in 2001 with a better
algorithm. The user's response: "человек бы открыл гугл и спросил как работает
punto switcher". Do not repeat.

## Procedure

1. **Principle search** (before any design):
   - RU: `<tool> принцип работы`, `<tool> как устроен архитектура`
   - EN: `how <tool> works internals`, `<tool> algorithm`
   - Read Wikipedia article if exists - history sections name algorithms.
2. **Prior art search**:
   - `github <tool> open source`, `github <task> implementation`
   - Alternatives lists on the Wikipedia page = free architecture survey.
   - Old small tools often beat modern frameworks: check 2000s utilities.
3. **Extract the real algorithm**, not the feature list. Example (Punto
   Switcher): NOT "dictionary of words" but keyboard hook + statistical
   bigram/trigram typicality check + Backspace-emulation re-typing.
4. **Steal structure, not code** (license check first: GPL vs MIT vs closed).
5. **Only then** write code - and cite which prior art each tricky part
   follows.

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

## Anti-patterns

- Building a naive version "to have something working" when a 20-year-old
  proven design exists.
- Hand-rolling lookup tables (QWERTY↔ЙЦУКЕН, translit maps) that ship inside
  every open source clone.
- Skipping the search because "the task sounds simple".

## Rule of thumb

If you cannot name two existing programs that do the thing and one line about
HOW each does it - you have not researched yet.