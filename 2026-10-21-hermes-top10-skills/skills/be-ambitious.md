---
name: be-ambitious
description: >
  Turn a task or prompt into a deeper version of itself, not a bigger one.
  Before rewriting, say what a top professional in the field would do that the
  user isn't asking for, the rawest source material they would start from, the
  specific methods and tools they would use, and what (other than the user or
  the model) would show the result is right. Then rewrite the prompt to ask for
  exactly that. USE WHEN: /be-ambitious, "be ambitious", "make this prompt
  deeper", "what would an expert do here", "raise the bar on this task",
  "rewrite my prompt like a pro would ask it". NOT FOR: expanding scope,
  adding features, or general prompt polishing for tone or length.
---

> Публикационная копия: санитизирована и сокращена для статьи
> «Топ-10 скиллов Hermes Agent на каждый день» (2026-10-21). Личные пути,
> внутренние проекты и приватные секции удалены; живая версия живёт в
> Hermes-профиле автора.

# Be ambitious

Adapted from a prompt shared by Felix Rieseberg (Anthropic):

> I want a deeper version of this task, not a bigger one. Before rewriting it:
> (1) say what a top professional in this field would do here that I'm not
> asking for; (2) name the rawest material they would start from instead of
> what has already been digested for me; (3) name the specific methods and
> tools they would use; (4) say what, other than you or me, would show the
> result is right. Then rewrite my prompt to ask for exactly that.

## Input

The task is whatever follows `/be-ambitious`. If nothing follows, use the
user's most recent request in this conversation. If there is none, ask for the
task in one line and stop.

## Deeper, not bigger

Keep the user's goal and scope. Depth means a higher standard for the same
outcome: better sources, sharper methods, real verification. Do not add
deliverables, features, or side quests. If a suggestion would make the job
larger rather than better, drop it.

## Steps

Name the field first (e.g. "investigative journalism", "SRE incident
response", "clinical pharmacology"), then answer the four questions for that
field. Be concrete: name the actual thing, not the category.

1. **What a top professional would do that wasn't asked for.** The two or
   three moves that separate expert work from competent work here, such as
   stating the decision the work serves, checking base rates, reproducing
   before fixing, or writing the counter-argument.
2. **The rawest material.** The primary sources they would start from instead
   of summaries: the dataset, not the chart; the filing, not the article; the
   logs and the code, not the bug report; the paper's methods section, not the
   abstract. Say where it lives if you know.
3. **Specific methods and tools.** Named techniques, instruments, libraries,
   commands, or frameworks, and why each fits this task.
4. **What, other than the user or the model, would show it is right.** An
   external check: a test suite or benchmark, a reproduction, ground-truth
   data, a known answer to compare against, a measurement, a domain expert
   or reviewer, a real user's behavior. Say what result would count as a
   pass and what would count as a failure.

If you don't know something in the field well enough to answer, say so rather
than inventing a source or tool.

**The rewrite inherits every error in the input.** Verify that each named model,
product, file, or command in the task actually exists before quoting it into the
new prompt. When the system the task describes is installed locally, verify
against it directly (`strings` over the binary for a class name, hex dump for a
file format, the engine log for the version) instead of searching the web —
digested articles inherit the same hallucination you are trying to catch. A
garbled or invented name placed inside the rewrite becomes a
requirement the next session satisfies literally, and the error then outlives
the conversation. Correct it in the block and state the correction in one line
above it.

## Rewrite

Then write the rewritten prompt in a single fenced block the user can copy.
It should ask for exactly what the four answers describe: start from the raw
material, use the named methods, and end with the external check and its pass
criterion. Keep it about as long as it needs to be, and in the user's voice.

When the user asks for a work product and includes `/be-ambitious`, execute the requested research and produce the artifact in the same session. For an email task, distinguish drafting from sending: research the named organization and product, recover relevant user-provided or searchable session context, then provide the requested drafts; do not send or create a mail draft unless explicitly asked.

For model-evaluation or writing-quality work, clarify the decision the research should support before proposing a broad evaluation plan. If the model's goal may be confused with evading AI-authorship detectors, distinguish naturalness, task quality, authorial voice, and detector performance; do not treat a detector score, perplexity, or burstiness as ground truth for human authorship. Verify each cited paper's actual method, population, baselines, and limits before importing its conclusions. Present techniques such as decoding changes, LoRA/QLoRA, SFT, preference optimization, or alternate architectures as separate hypotheses with explicit quality and regressions checks, not as established fixes. Disambiguate overloaded acronyms (especially LoRA vs aLoRA) against primary documentation before recommending a method. If the user asks only to improve a prompt, stop after the rewritten prompt and offer execution.

**The depth axes for a local-model proposal are the ones a reader acts on.** When the deliverable is a research program aimed at a model vendor or a local-model audience, "give your thoughts on quality and comparisons" is the shallow version. The ambitious version answers: which exact release artifacts exist and under what license; which hardware tiers load them and with what memory floor; what quality survives quantization; whether inference speedups (MTP, speculative decoding, KV quantization) hold together with output quality on the same prompts; which languages the vendor never tested; and whether adapter or fine-tune paths are permitted at all. Each axis ends in an artifact the recipient can hand over, not in an opinion they can agree with.

**An attached document is a source to re-read, not a memory to paraphrase.** Before writing "there it was advised that X" — especially before rejecting a recommendation — open the file and read that item. A reversed reading inverts who said what, and the recipient of the letter or article has the attachment in hand.
