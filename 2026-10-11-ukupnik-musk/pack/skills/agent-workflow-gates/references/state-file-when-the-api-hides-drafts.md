# When the API hides its own drafts, keep the id on disk

## When to use

Any external system whose read endpoints filter by committed status: artifact stores, ticket
trackers with a "published" flag, CMS with draft/published, approval queues, any provider whose
`GET by path` or `search` only returns rows past a lifecycle threshold.

Also: any client you are about to write where one command creates and a later command acts on that
same object by identifier. If the create returns an id, this pattern applies whether or not you have
yet hit the blind spot.

## The failure shape

The write succeeds and returns an id. The next command re-derives the id from the path it just
wrote to, gets nothing, and reports "not found". Read as a human, this looks like the write
failed. It did not — and a session that believes otherwise will re-run the create, producing a
duplicate, and then "fix" the duplicate by hand.

Three separate lookup paths commonly have the same blind spot, so fixing one is not enough:
a by-path reader, a by-query search, and a draft-scoped reader that requires an identity the
workflow's principal has never been granted.

## The rule

**Persist every id a create call returns, to run state, at creation time.** Not lazily when the
next step needs it — at creation, because that is the moment the value exists and nobody is
waiting. Write it before invoking the follow-up command.

The state file is then the mechanism that makes the process resumable, so give it the properties
the process needs anyway:

- keyed by a slug of the logical path, not by raw path (a path is not always a filename)
- a JSON object, so it can grow to hold realm, run id, revision
- written atomically enough for the process's failure model; if the create can succeed and the
  write can fail, do the write first with a placeholder, or verify the write before continuing
- scoped per profile/workdir, so two runs against the same logical path do not collide

## Reading it back

Resolve the id in this order, and stop at the first hit:

1. explicit `--id` on the command line, for one-off recovery
2. the local state file
3. verify the candidate is real before using it — a stale file from a previous run points at an
   artifact that may have been revoked or superseded, and acting on a revoked id is worse than
   reporting not-found
4. only then fall back to a server lookup, and expect it to miss uncommitted rows

Step 3 is the one people skip. A state file that is never invalidated will happily hand a
superseded revision to a command that then mutates the wrong artifact. Compare the id you recalled
against what the server reports for that path, and refuse to proceed on a mismatch.

## What this costs

One small file per run. In exchange: restart-safety for free, no duplicate creates, and a
`not found` that means genuinely not found rather than "the reader cannot see it yet".

## Naming

Keep the state next to the run, not next to the code. A state file inside a skill directory
accumulates across unrelated runs and eventually answers for the wrong one. Prefer the agent's own
state directory; if the skill must own the path, namespace it per profile and include enough of the
path in the filename to keep runs apart.
