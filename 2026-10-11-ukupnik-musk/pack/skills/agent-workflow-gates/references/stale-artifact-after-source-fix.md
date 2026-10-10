# The artifact, not the source, is what ships

## The shape

You fix a generator, its output is stale, and you verify the generator. The user receives the old output.

```text
22:26  scenes rendered from v1 source          -> media/videos/...
22:27  mp4 assembled from those scenes
22:43  you patch the source file               <- generator now correct
22:45  audit of the patched source: 0 defects  <- "done"
       you ship the 22:27 mp4
```

Every check passed and the artifact was wrong. The audit measured the thing you edited; the user
consumed the thing you built, and nothing ever re-derived the second from the first.

## Why it survives review

The source is the thing under edit, so it is what attention lands on. And the audit *did* run and
*did* come back clean, which reads as coverage. Coverage of the wrong subject is indistinguishable
from coverage when the result is green.

## The rule

**After any fix to a generator, rebuild the artifact before verifying anything, then verify the
artifact.** Order matters more than diligence here.

```bash
rm -rf <output_dir>          # stale output is not skipped by the next run, it is reused
<generator> <input>          # full rebuild
ffprobe <output>             # it exists, right duration, right dimensions
ffmpeg -ss <t> -i <output> -frames:v 1 <frame.png>   # frame from the SHIPPED file
```

The `rm -rf` matters: most generators key their cache on the output path and will happily reuse
chunks from the previous run, so a "rebuild" after a source fix can emit a Frankenstein of old and
new. Check timestamps on output versus source — if the output is older, you are looking at the
previous build.

## Verify the frame, and distrust a viewer that cannot be wrong

A frame pulled from the delivered file is evidence. A frame pulled from the source is a preview of
what you hope for. When the check is spatial (did text overlap a figure, did content leave the
frame, did the crop clip), measure rather than squint:

- count non-background pixels along each edge — an empty border is the proof content fits
- compare the text object's bounding box against the other shapes' boxes; overlap area over the
  smaller shape is a number, not an opinion
- a vision model reporting "content is fine" is one opinion; a pixel count is a fact. When the two
  disagree the number wins, and a vision model reading Cyrillic as Latin is a known failure mode,
  not evidence of a rendering bug

## The same rule for composed outputs

Multi-step pipelines fail the same way at the seams. A merge, a concat, a deploy: the pieces are
each verified, the assembly is not. Verify the composed file, and in the pipeline's own gate, not
only in the step that produced each part.