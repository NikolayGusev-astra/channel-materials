---
name: corporate-tool-workarounds
description: Python SSL→curl fallback, codex exit-127, Windows SSH quoting patterns, CDP Chrome self-launch.
---

# Corporate Tool Workarounds (Windows + Astra Network)

## Python SSL failure → curl subprocess

**Symptom:** Python HTTP (httpx/urllib) fails `SSLEOFError` against
corporate hosts like `knowledge.internal.example.test` — even with
`verify=False`, `trust_env=False`. curl works with `--ssl-no-revoke`.

**Fix:** `subprocess` + `curl` bypass:

```python
import subprocess, json, tempfile, os

def curl_post_json(url, data, basic_auth=""):
    payload = json.dumps(data, ensure_ascii=False)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    ) as f:
        f.write(payload); tmp = f.name
    cmd = ["curl", "-sS", "--noproxy", "*", "--ssl-no-revoke",
           "-X", "POST", url, "-H", "Content-Type: application/json",
           "-d", f"@{tmp}"]
    if basic_auth:
        cmd.extend(["-H", f"Authorization: Basic {basic_auth}"])
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    os.unlink(tmp)
    return json.loads(r.stdout) if r.returncode == 0 else {"error": r.stderr}
```

Flags: `--noproxy '*'` (bypass 127.0.0.1:12334), `--ssl-no-revoke`,
`-d @<tmpfile>` (avoids 32KB Windows cmd-line limit).

## HuggingFace upload behind proxy

**Symptom:** `hf upload` / `huggingface-cli` fails with SSL/timeout behind corporate proxy.

**Fix:** Disable proxy for HF calls:
```bash
NO_PROXY='*' no_proxy='*' http_proxy='' https_proxy='' hf upload aule13/model ./model/ .
```

Python HF hub also needs `NO_PROXY='*'` set in env. HF calls go to huggingface.co — internal
KBO proxy (127.0.0.1:12334) must not intercept them.

## Corporate issue-tracker PAT dead -> knowledge MCP fallback

**Symptom:** every Jira ticket returns 401 with header `x-ausername: anonymous`,
including previously-working tickets; anonymous `/rest/api/2/project` returns 0.
Confluence REST returns 403 `Not permitted to use confluence` / 404 on known pages.
The PAT in the Hermes `.env` is dead or revoked.

**Diagnose before concluding:** test the token on a ticket you KNOW you could
read, not on the project list — a 404 on `/rest/api/2/project/{key}` or a 400
`value absent for field 'project'` in JQL means NO BROWSE permission, not that
the project does not exist. The project list shows more projects than you can
actually browse.

**Fix — pull content through the knowledge MCP** (`https://kb-mcp.internal.example.test/mcp/`,
Bearer `<pat>` from the MCP server config in Hermes config.yaml). Raw
JSON-RPC over urllib with `build_opener(ProxyHandler({}))` (plain urlopen → SSL EOF):
1. `initialize` (protocolVersion `2025-03-26`) → capture `mcp-session-id` response header
2. `notifications/initialized` with the same session id
3. `tools/call`: `kb_query` (search: titles/URLs/scores/snippets),
   `kb_document` (full text by `source_id` + `page_id`), `kb_sources`
4. Header `Accept: application/json, text/event-stream` is mandatory (406
   without it); responses come as SSE — parse the `data:` lines

Coverage: aa-confluence, life, wiki, docs and other corporate KB sources — most
Confluence content. Enough for "study the topic from regs/initiatives" tasks;
ticket comments are NOT covered. This is a fallback, not a replacement — say so
when reporting what was searched.

**Python 3.14 removed `urllib.request.SOCKSProxyHandler`, and PySocks 1.7+ stopped
shipping it.** `from urllib.request import SOCKSProxyHandler` raises ImportError;
`from socks import SOCKSProxyHandler` raises `AttributeError` too (module loads,
attribute gone). `socks.create_connection` is still there, so build the opener by
hand — this is the only working form on 3.14:

```python
def _socks_opener(proxy_url):
    from http.client import HTTPConnection, HTTPSConnection
    import ssl as ssl_mod
    from urllib.request import AbstractHTTPHandler
    import socks as socks_mod

    p = urllib.parse.urlparse(proxy_url)
    proxy_addr = (p.hostname or "127.0.0.1", p.port or 1080)

    class _Conn(HTTPConnection):
        def connect(self):
            self.sock = socks_mod.create_connection(
                (self.host, self.port), self.timeout,
                proxy_addr=proxy_addr, proxy_type=socks_mod.SOCKS5)

    class _ConnTLS(HTTPSConnection):
        def connect(self):
            raw = socks_mod.create_connection(
                (self.host, self.port), self.timeout,
                proxy_addr=proxy_addr, proxy_type=socks_mod.SOCKS5)
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)

    class Handler(AbstractHTTPHandler):
        def http_open(self, req):
            return self.do_open(_Conn, req)
        def https_open(self, req):
            return self.do_open(_ConnTLS, req, context=ssl_mod.create_default_context())

    return urllib.request.build_opener(Handler())
```

Verify the module actually exposes what you need before assuming an ImportError is
fatal: `python -c "import socks; print([n for n in dir(socks) if 'Proxy' in n])"`.

**An opaque 404 from a bot API means the token is empty, not invalid.** A request
built as `https://api.telegram.org/bot/getMe` (empty token) returns 404, which
reads exactly like "wrong token" and sends you hunting for a revoked credential.
Check what the config layer actually produced — `config.load()` reading only
`os.environ` silently yields empty tokens whenever the app is started outside
compose/systemd while its `.env` sits on disk. Print `bool(cfg.token)` before
believing the server.

## Codex CLI exit 127 on Windows

**Symptom:** `codex exec` exits 127. Output: `bash: <word>: command not found`.
Word is trailing prompt text (e.g. `Expected:`, `NOTE:`, `If:`).

**Root cause:** Bash parses prompt tail as commands. Exit 127 is bash, not codex.

**Fix:** Codex usually FINISHED despite 127. Verify:
```bash
git log --oneline -5
python -m pytest tests/ -v
```
Re-run only if files are missing.

**Prevention:** End prompts with the task itself. Move notes/expectations
BEFORE the task instruction, not after.

## Extract a live session cookie from CDP Chrome → scripted curl scraping

**Symptom:** You logged into an authenticated portal (e.g. `medkarta.online`) in
a CDP-driven Chrome and need to pull MANY pages (all documents) by script, not
by clicking each view. `curl` without the session cookie gets a redirect; the
Cookie SQLite is Chrome-encrypted and unreadable directly.

**Fix — get the cookie over CDP, then curl with it.**
1. Find the page target websocket (`curl -s 127.0.0.1:9222/json` → each tab's
   `webSocketDebuggerUrl`). Use the tab that has the portal open.
2. Connect with `websockets`, send `{"id":1,"method":"Storage.getCookies"}`.
   **Use `Storage.getCookies` on the PAGE target — NOT browser-level
   `Network.getAllCookies`** (that returns a `KeyError: 'result'` without a
   page context).
3. Build a `Cookie: name=value; ...` header from the cookies where
   `"medkarta" in domain` (grabs `PHPSESSID`, `BITRIX_SM_LOGIN`, etc.).
4. `curl -k -H "Cookie: ..."` each view page, regex the asset URLs
   (`upload/iblock/.+\.pdf`), download them all. Direct asset URLs under
   `/upload/` are often open **without** auth — only the listing pages need
   the cookie.

Useful: the portal's year filter is a plain `?open=documents&documents=<year>`
param plus `&PAGEN_2=<n>` pagination — enumerate all years/pages with curl,
dedupe document IDs, then fetch each view. A portal may only store 2 years
(2025+2026) even when the user expects "3+ years" — verify with the filter
before promising older data.

## MSYS `--user-data-dir=$HOME/...` becomes `C:\c\Users\...` in Chrome

**Symptom:** Launching `chrome.exe --remote-debugging-port=9222 --user-data-dir=$HOME/chrome-cdp-medkarta`
from git-bash, the profile lands in an unexpected path and `Default/Cookies` is
not where you looked.

**Root cause:** MSYS prepends `C:\c\` to `/c/...`-style args passed to a native
Windows binary (Chrome), so `--user-data-dir=$HOME/...` becomes
`C:\c\Users\<user>\...`. The CDP browser still works, but the profile dir is
doubled.

**Fix:** pass the Windows path explicitly when you care where the profile lives:
`--user-data-dir="C:\Users\<user>\chrome-cdp-medkarta"`. If it already launched
with the mangled path, find the profile at `/c/c/Users/<user>/...` (Cookies
under `Default/Network/Cookies`).

### Patching the source does not regenerate the output — wipe render output first

**Symptom:** layout was fixed in the scene source, a geometry audit of the
source reported clean, the concatenated file was handed over, and the shipped
video still had the defect. Timestamps tell the story: scene mp4s written at
22:26-22:27, source patched at 22:43, concat produced at 22:27 — the concat
predates the fix.

**Root cause:** the fix was verified against the source while the artifact on
disk was never rebuilt. Renderers that skip unchanged-looking output keep the
old scene file, so a re-render without clearing the output directory silently
reuses stale scenes and the final file mixes fixed and unfixed scenes.

**Fix:** delete the render output directory before re-rendering after any source
edit, then rebuild the final file and inspect frames taken FROM the final file:

```bash
rm -rf media/videos/<module_name>      # not optional after a source change
# re-render every scene, re-concat, then extract frames from final.mp4
```

**Rule: an audit of the source is not a check of the artifact.** Before shipping
any rendered file, run three independent checks — geometry audit on the source,
frame extraction from the FINAL file, and a non-empty-pixel count per frame.
Two of the three can pass while the user is still looking at the old bytes.

### Chained `scale_to_fit_width().scale_to_fit_height()` grows content past the frame

**Symptom:** letters at the edges of a frame are cut off, exit 0, no warning.

**Root cause:** those helpers scale to the given value, they do not clamp to it.
`scale_to_fit_width(13.0).scale_to_fit_height(7.2)` on a group that was
11.712 x 5.560 grows it to 13 wide, then the height call grows it further to 7.2
— final width 15.168 against a 14.222 frame, so content physically sits outside
the visible area.

**Fix:** one scaling call over both axes with headroom, so the governing axis is
chosen by comparison rather than by call order:

```python
FRAME_W, FRAME_H = 14.222, 8.0
g.scale(min(FRAME_W * 0.90 / g.width, FRAME_H * 0.90 / g.height)).move_to(ORIGIN)
```

**Text and figures must occupy different bands of the frame.** A heading placed
at the frame centre plus cards placed at the frame centre is an overlap: the
heading occupied y −0.27…0.27 while the cards occupied y −0.95…0.95. Push the
heading out with `head.to_edge(UP, buff=0.55)` and shift the figures the other
way. A mechanical bbox audit over the source catches this without an eyeball.

### A bbox audit that flattens the tree reports false overlaps

**Symptom:** an overlap audit reports 100% overlap for every text object.

**Root cause:** walking `family_members_with_points()` compares a `Text` against
its own glyph outlines — a glyph is always fully inside its own text box. Zero
text objects found means the detection branch never matched, not that the frame
is clean.

**Fix:** classify at the top level of `scene.mobjects`, keep `Text`/`Tex`/`MathTex`
as the text set, and flatten only non-text containers for the shape set. Report
overlap as a fraction of the smaller box area and flag above ~4%.

## Programmatic-video QA loop (manim/ffmpeg renders): verify frames before shipping

For rendered video artifacts (manim, ffmpeg-built explainers), do a
**frame-extraction QA loop** before declaring done — layout bugs like
overflow/overlap are invisible until you look at actual frames:

```bash
# Windows ffmpeg: output path MUST be Windows-syntax (see MSYS section above)
ffmpeg -y -loglevel error -ss 5 -i Scene2_Pipeline.mp4 -frames:v 1 "C:\\Users\\<u>\\proj\\frame.png"
```
Then `vision_analyze` the PNG asking the user's exact complaint
("did X overflow width? overlap at 13s? card text inside borders?"). Fix, re-render,
re-extract, re-inspect. Common manim 1080p failure modes caught this way:
- Cards in one row exceed frame width (frame default 14.222 units) → use
  `arrange_in_grid(rows=2, cols=3)` + `scale_to_fit_width(13.2)` instead of a single row.
- Whole-pipeline `VGroup.arrange(DOWN, buff=N)` + `scale_to_fit_height()` —
  values over ~7.2 push content off a 8.0-height frame.
- `FadeOut(list)` fails ("Animation only works on Mobjects") — wrap in `VGroup(*highlights)`.
- Sequential `next_to` on live mobjects collides at 1080p; build one `pipeline`
  VGroup, position once, then reference children for animations.
- Two Manim API traps that cost render cycles, both with confusing errors:
  a Scene class must NOT be named like a mobject it uses (`class ComplexPlane(Scene)`
  shadows the import, so `ComplexPlane(x_range=...)` inside it fails with
  `Scene.__init__() got an unexpected keyword argument`); and `Angle` takes
  `Line` objects, not coordinate points — passing points gives
  `AttributeError: 'numpy.ndarray' object has no attribute 'get_start'`.
- `-ss` past the clip duration yields `Output file is empty` with **exit 0**.
  Read `ffprobe format=duration` first and seek to ~50-80% of it, then `ls` the
  PNG — zero bytes means the seek missed, not that the frame was blank.

Report frame-verified results as such ("checked frames at 5/11/14s"), not
"video renders" — a render exit 0 proves nothing about framing.

**When `vision_analyze` is unavailable, verify the frame mechanically.** The local
VL model can fail to load (`llama-server ... exited before becoming healthy`), and
"looked fine by eye" is not acceptable anyway. Assert colours from the raw pixels:
convert the extracted PNG to `rgb24` with ffmpeg and read it as bytes with stdlib
(no PIL needed), then check that a sampled band contains the colours the script
asked for.

```bash
ffmpeg -y -i frame.png -f rawvideo -pix_fmt rgb24 frame.raw   # W*H*3 bytes
```
```python
# 1920x1080 rgb24: byte offset = (y*W + x)*3 ; sample every 4th row/col
band = data[(y0*W)*3:((y1)*W)*3]        # top N rows
```

This turned a vague "the formula rendered" into "these three bands contain
#58C4DD, #FC6255, #83C167", which is checkable and reproducible. Pair the pixel
assert with `vision_analyze` when the model is up; when it is not, the pixel
check is the gate, not an optional extra.

### `Tex`/`MathTex` need BOTH `latex` AND `dvisvgm` — checkhealth is the gate

`python -m manim checkhealth` probes two binaries, not one: `latex` (the
typesetter) and `dvisvgm` (the DVI→SVG converter `Tex` shells out to). Satisfying
only `latex` leaves `MathTex` failing at render time, so read both lines before
declaring the install good.

Pick the distribution the account can actually install, not the nominally newest
one — check the package manager's manifest for elevation requirements first:

```bash
scoop search miktex && scoop info miktex   # main bucket: portable, --unattended --private
scoop install miktex                       # adds bin to PATH, no admin needed
```

An installer that prompts for elevation cannot complete on a non-admin account,
and the fuller TeX Live often has no package-manager entry at all.

**`mpm --admin` fails in a portable install** with "Option --admin only makes
sense for a shared MiKTeX setup" - portable means private, so the flag is
meaningless. Drop it; `mpm --install=<pkg>` is enough to add one package.

**Set unattended package installation before the first render.** MiKTeX's default
on a missing package is a GUI dialog; under a headless or scripted run the render
waits on that dialog forever instead of failing. Set the config key directly with
`initexmf` rather than the documented `miktex` wrapper:

```bash
initexmf --set-config-value=[MPM]AutoInstall=1
```

The `miktex --set-default-package-install=1` form is the one printed in MiKTeX's
own help, but it opens the console and never returns under a non-interactive
call - it hangs until the caller is killed. `initexmf` writes the same
`[MPM]AutoInstall=1` key and returns immediately. Confirm it landed rather than
trusting exit status:

```bash
grep AutoInstall ~/scoop/persist/miktex/texmfs/config/miktex/config/miktex.ini
# AutoInstall=1
```

The config lives under the persist directory (scoop), not under the versioned
app dir, so an upgrade does not silently revert the setting.

Gate the work on `checkhealth` reporting PASSED for both binaries, then render one
throwaway scene containing `MathTex` and extract a frame from it. A distribution
that installs cleanly still leaves `Tex` broken when `dvisvgm` is absent, and a
scene that never mentions `Tex` will not notice.

## Windows-authored `.env` pushed to Linux: CRLF + unquoted spaces break both parsers

**Symptom:** A `.env` crafted on Windows (e.g. `lead_server.env` with `TG_TOKEN`,
`SMTP_PASS`) is scp-ed to a Linux host. `bash source file.env` dies at line N
with `command not found` (value leaked), or systemd `EnvironmentFile` loads
values with a trailing `\r` → tokens/URLs contain control chars
(`URL can't contain control characters`), Gmail app-passwords fail.

**Root causes (two independent bugs):**
1. **CRLF:** Windows files carry `\r\n`; `bash source` and systemd read the
   `\r` into the value. Classic on any `echo ... > env` / `printf` from git-bash.
2. **Unquoted spaces:** Gmail app-passwords are `jcor fncq rwjq narn` (4×4,
   space-separated). `source` splits on whitespace → next line executes as a
   command. systemd tolerates it, bash does not.

**Fix:**
```bash
sed -i 's/\r$//' file.env          # kill CRLF first
# then quote every value with spaces (works for BOTH parsers):
SMTP_PASS="jcor fncq rwjq narn"
```
Also apply `sed -i 's/\r$//'` to any Windows-written `.py`/`.sh` before running
on Linux (scp preserves Windows line endings). Verify with the real consumer —
`systemctl start` + journalctl — not just `source`.

## Static-site lead form backend: queue-first + background dispatch

**Pattern (proven on build-host.example.test for example-project.example.test):** nginx static site
+ tiny Python `ThreadingHTTPServer` behind `proxy_pass` for `POST /api/lead`:
1. Handler returns `{"ok": true}` IMMEDIATELY (sub-second), appends lead to a
   JSONL queue file (durable record — replay on demand).
2. Dispatch (Telegram Bot API + SMTP email) runs in
   `threading.Thread(daemon=True)`, never inside `do_POST`.
3. `do_OPTIONS` + `Access-Control-Allow-Origin: *` for cross-origin JS fetch.

Why: a synchronous handler that calls TG/SMTP inside the request hangs the
client for seconds (SMTP handshake can take 2–15s) and the site "feels broken".
Queue-first keeps the form instant and survives mail/TG outages.

**Pitfall:** nginx `location /api/lead` + `proxy_pass http://127.0.0.1:PORT`
passes the ORIGINAL URI. Accept `endswith("/lead")` in the handler, not strict
`== "/lead"` match — else you get a 404 from the Python server through nginx.

## SearXNG search via SSH tunnel + Python urllib proxy pitfall

**Context:** Host `build-host.example.test` (153.80.251.34) runs a self-hosted
SearXNG in Docker (`0.0.0.0:8080`). Public search engines (DuckDuckGo HTML,
Bing) hit CAPTCHA/consent walls from automation — **the user's preferred path
is the server's own SearXNG** (`?format=json`).

**Step 1 — SSH tunnel (background) to the container port:**
```bash
ssh -o StrictHostKeyChecking=no -N -L 18080:127.0.0.1:8080 root@build-host.example.test
```
`-N` no shell, just the forward. Run with `background=true`.

**Step 2 — Query JSON:**
```bash
curl -s --noproxy '*' "http://127.0.0.1:18080/search?format=json&q=<query>" \
  -H "Accept: application/json"
```

**PITFALL — Python urllib gives 502 Bad Gateway on the tunnel:**
`HTTP_PROXY`/`HTTPS_PROXY` are set to the corporate proxy `127.0.0.1:12334`,
and urllib honors them even for `127.0.0.1:18080` → proxy tries to fetch the
localhost tunnel → 502. curl with `--noproxy '*'` is immune; Python is not.
**Fix:** build an opener with a disabled proxy handler:
```python
import json, urllib.request, urllib.parse
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # ← bypass proxy
url = "http://127.0.0.1:18080/search?format=json&q=" + urllib.parse.quote(q)
with opener.open(url, timeout=30) as r:
    d = json.load(r)  # d["results"][i]["title"|"url"|"content"]
```
Single-result curls may intermittently 502-return empty `results` (some engines
fail); **retry once with a short sleep** — a lone retry usually succeeds. Batch
queries in one `execute_code` with `time.sleep(1.5)` between and a retry wrapper.

## `pkill -f "<pattern>"` over SSH kills the SSH session itself

**Symptom:** Running `pkill -f "lead_server.py"` (or `kill $(pgrep -f "...")`)
inside an ssh command **kills the ssh session** → exit 255 / empty output, and
the intended service is never touched.

**Root cause:** The remote bash process running your command line contains the
pattern string in its own argv (because the whole command is passed through
ssh). `pkill -f` / `pgrep -f` match the full cmdline, so bash matches itself.

**Fixes:**
- **Bracket trick** so the pattern can't match your own command line:
  ```bash
  pkill -f "[l]ead_server.py 8715"   # [l] never equals literal l in own argv
  pgrep -f "[m]ini_probe"
  ```
- Or target by exact pid from `ss -tlnp` / `pgrep`, not by full pattern.
- Or avoid killing entirely: pick a fresh port / use `systemctl restart`.

## Native Windows binaries reject MSYS paths — use Windows-syntax for output

**Symptom:** `ffmpeg -i in.mp4 -frames:v 1 /c/Users/.../out.png` fails with
`Could not open file` / `[image2] Error opening output`. Works in git-bash for
MSYS-built tools (curl, python) but **not** for native Windows builds
(gyan.dev ffmpeg).

**Root cause:** MSYS path `/c/...` is only translated by MSYS-aware tools.
Native Windows binaries get the literal string `/c/Users/...`, which they can't
resolve (no `C:` drive letter).

**Fix:** Pass the Windows-form path to native binaries (input paths usually
resolve fine via `.`/relative, but output paths do NOT):
```bash
ffmpeg -y -ss 3 -i Scene2.mp4 -frames:v 1 "C:\\Users\\<user>\\proj\\frame.png"
```
Rule of thumb: relative/`.` input paths work; absolute output paths must use
`C:\...`. Same applies to any native Windows exe taking file args (gh, node,
codex writing files).

### `git clone <url> ~/.hermes/...` SILENTLY succeeds but lands in `/c/c/...`

**Symptom:** `git clone https://... ~/.hermes/desktop-plugins/x` prints
`Cloning into '/c/Users/...'...` and returns **exit 0**, yet `ls ~/.hermes/...`
shows nothing and `cd` into the target fails with `No such file or directory`.
The repo actually landed at `/c/Users/<user>/.hermes/desktop-plugins/x`
(on drive root `/c/c/...`), because git is a native Windows binary that does
NOT translate the MSYS destination path.

**Why this is worse than an error:** exit 0 + a plausible "Cloning into..."
message make the step look successful. You must verify the repo actually
appeared where you expected before moving on.

**Fix:** pass the Windows-form destination explicitly:
```bash
git clone https://github.com/NousResearch/Hermes-Bot-Mode "C:/Users/<user>/.hermes/desktop-plugins/hermes-bots"
```
Then confirm with `ls "C:/Users/<user>/.hermes/desktop-plugins/hermes-bots/"`.
If a previous mangled clone exists, clean it: `rm -rf /c/c` (it is drive-root
garbage, not your real home).

Note: curl with `--noproxy '*'`/MSYS paths is fine (curl is MSYS-aware), but
any *native* exe taking a destination argument (git clone, git init -b, node
writing files, gh release download) needs `C:/...` syntax. When in doubt,
verify the artifact's real location with `ls`/`find`, never trust exit code.

Also note git-bash `/tmp/` == `/c/Users/<user>/AppData/Local/Temp`, so files
written to `~/...` and `/tmp/...` land in different places — check both when a
freshly-written temp file "isn't there".

## ansible-core on Windows control node: needs stub layer, POSIX-only collections still fail

Running ansible-core as a control node on Windows requires shimming POSIX-only
modules before the CLI starts. Working setup: dedicated venv
(`uv venv ansible-venv --python 3.11` + `uv pip install ansible-core==2.17.*`;
2.19+ does not start on Windows at all), plus a `sitecustomize.py` in site-packages
that stubs `os.get_blocking`, `locale.getlocale` (force UTF-8), and dummy modules
`fcntl`/`termios`/`grp`/`pwd`. Two source patches also required:
`ansible/parsing/dataloader.py` (RE_TASKS regex built from `os.path.sep` breaks on
`\\` — hardcode `/`) and `ansible/utils/display.py` (libc `wcwidth` — stub on win32)
and `ansible/utils/multiprocessing.py` (`fork` context — use `spawn` on win32).

Collections install fails on symlinks (WinError 1314): download the tarball with
curl, extract skipping `m.issym()/m.islnk()`, then strip symlink entries from
`FILES.json`. Set `ANSIBLE_COLLECTIONS_PATH` to the dir that CONTAINS
`ansible_collections/` (not its parent).

Even with all shims, collections that import POSIX plugin machinery at load time
(e.g. `ansible.posix.mount`) do not resolve on a Windows controller — that is a
controller limitation, not a playbook error. For validation stop at
`--syntax-check` for builtin+platform-agnostic modules; run the full
`--check --diff` from a Linux controller.

## Windows SSH quoting:</strong> NEVER use `shell` module with pipes/quotes

**Symptom:** ansible `shell` module through `cmd.exe /c ssh.exe` breaks on
any of: `'` (single quote), `|` (pipe), `"` (double quote), compound
commands. Error: `bash: -c: строка 0: неожиданный конец файла во время поиска «'»`

**Root cause:** cmd.exe mangling of nested quotes through SSH chain:
`cmd.exe → ssh.exe → bash → ansible → bash → target`. Single quotes and
pipes are stripped/interpreted at wrong layer.

**Fix:** ALWAYS use `script` module, NEVER `shell`/`command` for anything
beyond single-command parameterless calls:
```bash
# ❌ BROKEN:
ansible host -m shell -a "ipa dnsforwardzone-add ald2.pro --forwarder=100.64.19.17"
# ❌ BROKEN:
ansible host -m shell -a "grep use_fast /etc/krb5.conf"
# ❌ BROKEN:
ansible host -m shell -a "ipactl status | head -5"

# ✅ WORKS:
ansible host --become -m script -a /path/to/script.sh
```

**Script conventions:**
- Scripts on bastion: `/home/<user>/proj-stand/<name>.sh`
- Copy via: `scp local.sh user@bastion:/home/<user>/proj-stand/`
- Run via: `ansible host -m script -a /home/<user>/proj-stand/script.sh`
- All diagnostic output in script body (echo, grep, ipactl, etc.)

**`&&` chaining through cmd.exe:** NEVER chain ansible commands with `&&`
in cmd.exe — cmd.exe interprets the second command locally. Always run as
separate `terminal` calls.

## scp multiple files from different local subdirs → flat root on server

**Symptom:** `scp common/config/config.go model/ability.go middleware/distributor.go root@host:/root/fork/` puts ALL files in `/root/fork/` (flat), NOT at their respective subpaths. Server build then fails (`cannot find package`), or worse — the root accumulates stray `.go` files that shadow correct ones (e.g. a `config.go` from `common/` landing in repo root when the real one lives in `common/config/`).

**Root cause:** scp in file-list mode flattens everything into the destination directory; it does NOT preserve source directory structure.

**Fix:** one destination path per file:
```bash
scp common/config/config.go root@host:/root/fork/common/config/config.go
scp model/ability.go        root@host:/root/fork/model/ability.go
scp middleware/distributor.go root@host:/root/fork/middleware/distributor.go
```
Or tar the repo subset preserving relative paths (`tar czf - <dirs> | ssh root@host 'tar xzf - -C /root/fork'`).

**Verify:** after copy, `ssh root@host 'ls <dest>/*.go'` — root must contain only true root files (e.g. `main.go`). Any strays from a flattened scp must be `rm -v`'d before `go build`/docker build. This bit us deploying the one-api fork (2026-08-02): first scp dumped `ability.go/channel.go/distributor.go/model.go/option.go/config.go/...` into the repo root; after `rm -v` of those strays the build went green.

## UTF-8 BOM Python files show as "binary" to read_file but are editable

**Symptom:** `read_file`/`search_files` return `Binary file - cannot display as text` /
`IO error` for `.py` (and some `.js`/`.md`) files that actually contain only text.
The root cause is a **UTF-8 BOM** (`EF BB BF`) at byte 0 — Windows tools (some
editors, `notepad`-family saves) write it. Both `read_file`'s text detector and
ripgrep treat the BOM as binary/non-UTF-8, so you cannot view the file through
the tools the agent normally reaches for.

**Fix — read/edit with CLI tools instead (all tolerate the BOM):**
```bash
grep -n "def foo\|class Bar" file.py        # locate symbols — works
sed -n '23,35p' file.py                     # view a region — works
head -5 file.py                             # works
```
And **`patch` still works** on BOM files — it does a fuzzy byte match and
preserves the BOM when rewriting (verified on `engine.py`/`config.py` this
session). `search_files` (rg) fails on the path; fall back to `grep` in terminal.

**Verify JS/Python syntax** on BOM files with a Windows-native tool (which
handles BOM fine), NOT the MSYS-path form:
```bash
node --check "C:\\Users\\<u>\\proj\\plugin.js"     # BOM-ok, Windows path REQUIRED
python -c "import py_compile; py_compile.compile('mod/bridge.py', doraise=True)"
# MSYS path like C:/c/Users/... breaks node; use the C:\\... form
```

Related MSYS quirk: a file you `write_file` to `/tmp/x` may land in
`C:\tmp` while MSYS `/tmp` == `C:\Users\<u>\AppData\Local\Temp`. When SCP/pscp
of a freshly-written file "file not found", check both locations (see the
`/tmp/` divergence note above).

## Search and count on disk: `rg`, not `grep | awk | find | wc`

**Rule: когда нужен поиск, выборка или счёт по файлам на диске — `rg`, а не
shell-конвейер вида `grep ... | awk ... | wc -l`.** ripgrep 15.2.0 стоит на хосте
(путь `~/AppData/Local/hermes/tools/ripgrep-15.2.0-win32-x64/rg`, в PATH git-bash).

Предстартовый фильтр решения (шесть осей: Боцман, Художник, Маск, Ли, Фома,
Фейнман) и его применение к работе агента: манифест `THEOREM.md` в корне пака.

Причины, а не вкусовщина:
- `rg` считает сам (`-c`, `--count-matches`), поэтому `grep | wc -l` не нужен.
  Конвейер из трёх программ это ровно тот «монстр, который умеет всё понемногу»:
  линтер и rg лучше модели и обвязки на одноразовой механической работе.
- Регулярное выражение пишется один раз в языке rg (Rust regex), без разницы
  в диалектах между grep/awk/sed.
- Ссылка на источник остаётся одна: `rg -n 'паттерн' путь` даёт файл и строку,
  по которым утверждение можно перевосстановить.

Формы, которые заменяют типовые конвейеры:

```bash
rg -c 'pattern' path/                # сколько вхождений в каждом файле (вместо grep|wc -l)
rg --count-matches 'pattern' path/ | awk '{s+=$1} END {print s}'   # суммарно
rg -n 'pattern' path/                # файл:строка для цитирования
rg -o 'pattern' -r '$1' path/ | sort -u   # вытащить и дедуплицировать значения
rg --files -g '*.md' path/           # вместо find path -name '*.md'
```

**Исключение одно:** файл с UTF-8 BOM rg считает бинарным и молча пропускает
(см. раздел про BOM выше) — там `grep -n` в terminal остаётся рабочим путём.

### Считает не модель: сумма, дедуп, счёт файлов делаются rg, не «на глаз»

**Rule:** когда задан вопрос «сколько», «какие из них», «есть ли ещё» — ответ
даёт `rg -c` / `--count-matches` / `rg --files`, а не память模型 и не круглое
число. Скилл-разбор, аудит ссылок, инвентаризация: любая цифра, попавшая в
ответ, проходит через счётчик в том же ходе, до выдачи. Круглое «10000
скиллов» без `rg --files -g 'SKILL.md' | wc -l` это не факт, а украшение, и
читатель первый же спросит «откуда число». Считать в том же tool call, что и
окончательное утверждение — не в предыдущем.

### Не крути правку одного класса дефектов вручную, когда линтер чинит все разом

**Symptom:** три-четыре круга `patch` по одной ошибке линтера на строку
(длинное тире, мат-знак, артефакт цитирования), severity растёт медленнее, чем
растёт число правок.

**Root cause:** дефект класса, а не строки. Точечный патч на каждый экземпляр
это ровно шлюха из анекдота: своя техническая цель (убрать ERROR с этой строки)\несть, а результат (читаемый текст) недостижим таким темпом.

**Fix:** сначала снять глобальный класс одним проходом — скриптовая замена
(линтер humanizer прямо предписывает: тире в `-`, `→` в `->`, знаки сравнения
словами), либо `sed`/python по байтам с `assert count == N`, либо переписать
файл целиком `write_file` не по частям. Точечно добивать только остаток.
**Правило деления:** если второй круг правит тот же вид дефекта в новом месте,
способ правки выбран неверно — меняй инструмент, не меняй попытки.

**Отдельный случай — `search_files` от Hermes.** Этот инструмент сам построен на
rg, поэтому для обычного поиска он предпочтительнее запуска rg руками: тот же
результат без обвязки. Ручной rg остаётся для того, чего `search_files` не умеет:
счётчиков, `-o` с заменой, глобов по имени файла и обхода в обход ограничений
инструмента.

## Inline `cmd.exe /c ssh.exe` dies on Cyrillic, braces, and shell vars → write-script-scp-run

**Symptom:** `cmd.exe /c ssh.exe root@host '...'` fails mysteriously when the
remote command / probe contains:
- **Cyrillic** anywhere (e.g. `docker inspect --format '{{range .Config.Env}}...'`
  piped to `grep -i WORKSPACE`, or any output with Russian letters) → garbled
  `���⥬�` / `"WORKSPACE" � �� �⮫������'` / exit 255.
- **Curly braces** `{{...}}` (docker `--format`) — cmd.exe parses braces and
  mangles the inner text.
- **Shell `$` variables** (`for p in ...$p`) — cmd.exe eats them → empty/dangling.

**Root cause:** cmd.exe is the middle layer in `cmd.exe → ssh.exe → bash → target`.
Quotes, braces, `$`, and non-ASCII get interpreted/stripped at the wrong layer —
same family as the ansible-shell problem above, but hits plain ad-hoc ssh.

**Fix — write the script locally, scp it, run it on the server (never inline):**
```bash
# 1) write /tmp/probe.sh locally (write_file — keeps UTF-8 + $vars intact)
# 2) scp + run:
scp -o StrictHostKeyChecking=no     /tmp/probe.sh root@host:/tmp/probe.sh
cmd.exe /c ssh.exe -o StrictHostKeyChecking=no root@host 'bash /tmp/probe.sh'
```
This is the reliable path for ANY remote diagnostic that touches docker
`--format`, Cyrillic output, or loops/vars — don't fight cmd.exe quoting.
- Prefer ASCII-only output in the scripts (echo English labels) so results
  come back cleanly.
- `docker inspect --format '...'` is the #1 offender — always wrap in a scp'd script.
- **Heredocs through `cmd.exe /c ssh.exe` die too** — not just pipes/braces/cyrillic. `cmd.exe /c ssh.exe root@host "python3 - << 'PY' ... PY"` fails with `bash: warning: here-document at line 1 delimited by end-of-file (wanted 'PY')` — cmd.exe mangles the multi-line body before remote bash sees it. Fix: write the python/bash body to a local file with `write_file`, `scp` it, run `ssh root@host 'python3 /tmp/probe.py'` (the proven `desanitize-test.py` pattern). Inline one-liners are fine; anything with a heredoc, `<<`, or multi-line body is not.
- This is distinct from one-liner read-only probes (simple `curl -o /dev/null -w %{http_code}`)
  which DO work inline; only multi-part / Cyrillic / brace / var / heredoc commands need the script path.
- **From execute_code, drop the bash layer: `subprocess.run(["cmd.exe", "/c", "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", "root@host", remote_cmd], capture_output=True, text=True)` with the remote command as ONE argv element.** The terminal tool routes bash → cmd.exe → ssh, and bash mangles nested quotes before cmd.exe ever sees them — even a plain `ssh root@host "sqlite3 db \"SELECT ...;\""` dies with `unexpected EOF while looking for matching quote`. List-argv subprocess has no bash in the middle, so nested double quotes in the remote command survive.
- **Feed remote scripts through SSH stdin instead of `-c` quoting, heredocs, or scp:** `ssh root@host python3 -` with `input=<script text>` (Popen stdin) runs a multi-line python program cleanly; `ssh root@host "cat > /opt/scripts/x.py && chmod 755 /opt/scripts/x.py"` with `input=<text>` writes a remote file. Same cmd.exe transport, but the body never passes through a quoting layer — replaces both the `python3 -c '...'` attempt (dies like above) and the scp round-trip for text payloads.

## plink: uncached host key / password prompt → cmd-ssh BatchMode fallback

**Symptom 1:** `plink -batch` refuses a host missing from PuTTY's cache
("host key is not cached... Cannot answer interactive prompts").

**Fix:** take the SHA256 fingerprint from the error, VERIFY it against the
trusted OpenSSH known_hosts (`ssh-keygen -lf ~/.ssh/known_hosts`, match
the IP/alias line) - never just accept the new key - then pass it
explicitly: `plink -batch -hostkey SHA256:... root@host cmd`.

**Symptom 2:** with the hostkey passed, plink still demands a password
("Cannot answer interactive prompts in batch mode") although the server
authorizes by key - plink has no stored session/password in the registry.

**Fix:** skip plink, use Windows OpenSSH directly (key auth from ~/.ssh
works; BatchMode fails fast instead of hanging):
```python
subprocess.run(["cmd.exe", "/c", "ssh", "-o", "BatchMode=yes",
                "-o", "ConnectTimeout=10", "root@host", cmd], ...)
```
Check BOTH transports before concluding credentials are missing: cmd-ssh
BatchMode first when a key exists, plink -hostkey for password sessions.
git-for-windows ssh stays forbidden (faillock).

## `mktemp -d` paths are unreadable by native Windows programs

**Symptom:** a bash script creates a work dir with `mktemp -d`, writes files into it, then
invokes native `python` on those files. Python raises
`FileNotFoundError` / `[WinError 3] The system cannot find the path specified` for a directory that
plainly exists and that `ls` lists.

**Root cause:** same MSYS boundary as the ffmpeg/git sections above, in the other direction. The
shell understands `/tmp/tmp.XXXX`, but the native binary receives that literal string and cannot
resolve it without a drive letter.

**Fix:** resolve before handing the path to the native program, never after.

```bash
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
WORK_NATIVE=$(cygpath -w "$WORK" 2>/dev/null || echo "$WORK")
python "$SCRIPT" "$WORK_NATIVE"     # native python gets C:\Users\...\Temp\tmp.XXXX
```

**Same class of bug in a different disguise:** writing a multi-line JSON response into a shell
variable and then parsing it with a line reader. Pretty-printed JSON spans many lines, so a
line-by-line parser silently discards every record and reports an empty result with no error.
Write one response per file and `json.load` each — that is what makes a multi-request probe
report real counts.

## `shutil.rmtree` refuses Windows dirs with junctions; it aborts half-done

**Symptom:** `shutil.rmtree(path)` raises
`OSError: Cannot call rmtree on a symbolic link` on a directory that is a real directory with real
files. Nothing appears to have been removed, and the loop that called it dies partway through.

**Root cause:** Windows reparse points (junctions, and some symlink-to-directory layouts) make
`rmtree` bail at the top instead of recursing. Because the exception propagates, every remaining
item in the loop is skipped — the "batch" is a silent partial no-op that looks like a clean run.

**Fix:** remove such directories from the shell, then verify live siblings afterwards.

```bash
for d in "$ROOT"/*/*.rollback-broken; do [ -e "$d" ] || continue; rm -rf "$d"; done
ls -d "$ROOT"/*/*.rollback* 2>/dev/null | wc -l    # expect 0
```

Always re-check the siblings you did not intend to touch — a partial delete that aborts on
directory 3 leaves directories 4..n in place, and the ones already processed are gone for good.
Confirm with `os.path.exists` on the live paths, not by assuming the loop finished.

## PVE API-token auth header: `=` before the secret, not `:`

Authorization: PVEAPIToken=<user>@<realm>!<token-id>=<secret>
returns `401 Authentication failed` on ALL endpoints, read and write alike, for EVERY
freshly-issued secret. Looks like "the token mechanism is broken on this build" and
tempted three token rotations that changed nothing.

**Root cause:** the separator between tokenid and secret is an EQUALS sign; a colon makes
the header an unrecognized credential shape, which pveproxy rejects at authentication —
before permissions are even considered. ACL, privsep and expiry are NOT the problem when
the separator is wrong.

**Fix:**
```
Authorization: PVEAPIToken=<user>@<realm>!<token-id>=<secret>
```

Debug ladder that separates auth failure from permission failure: `GET /version` with the
token — 401 means authentication (fix the header); 200 on GET but `401 No ticket` on POST
means permissions/CSRF, not the header. POST with a token works WITHOUT
`CSRFPreventionToken` (tokens are CSRF-exempt); `pvesh termproxy` also works with
`Sys.Console`. A full working token string saved to a scratch file should be stored in
`PVEAPIToken=user@realm!id=secret` form ready-to-use, chmod 600.

**A secret is displayed exactly once** at creation/rotation (or in the `value` field of the
POST JSON response when creating the token via API) — after the popup closes it cannot be
re-read. Rotation invalidates the old secret immediately, so save before rotating. If a
freshly-pasted secret 401s, suspect the header format FIRST and the credential SECOND:
verify by rebuilding the header in the `=`-form with the same secret before issuing
another rotation.

## Corporate Bitbucket push: pre-receive hook rejects silently-named branches

**Symptom:** `git push` to `git.example.test:7999/<PROJECT>/<repo>.git` fails with a
wall of `remote:` lines and no local diff. The hook lists numbered rules
(`2.1 BRANCH`, `3.1 COMMIT`, `4.1`) plus a `REJECTED!` banner. This is NOT an
access failure and NOT a wrong remote — a probe branch pushed fine moments
earlier.

**Finding the repo path (SSH works, "Repository not found" = wrong slug):** the
SSH key is registered on the Bitbucket DC even when you do not know the project
key. Enumerate candidate slugs with `git ls-remote ssh://git@git.example.test:7999/<PROJ>/<repo>.git`
— "Repository not found" means wrong path, refs output means found. Known:
ИИ-платформа repo lives at `INT/int-6536` (web UI path `users/.../repos/...` is
NOT the clone path). The Jira PAT (`JIRA_PAT` from `hermes config get
mcp_servers.jira.env.JIRA_PAT`, base64 `userId:secret`) authenticates
Jira/Confluence REST but NOT Bitbucket REST — git-over-SSH with id_ed25519 is
the working write path.

**What the hook enforces** (discovered by probing, all four were invisible from
the error text until read):

| Rule | Requirement |
|---|---|
| 2.1 | branch name matches `<master\|((feature\|bugfix)/\S+)>` |
| 3.1 | **exactly one** issue key INT/PRESALE in the **whole commit message**, not just the subject line |
| 4.1 | committer email matches `*@example.test` |
| — | **commits must be signed**; unsigned commits rejected |

**Rule 3.1 is the trap.** A subject line like `[PROJ-1001] feature` passes, but
mentioning a second ticket anywhere in the body makes the hook count two keys
and reject. Cross-references go in the task tracker, not the commit body.

**Signed commits enforced repo-wide.** A push of an unsigned commit fails with
`Signed commits and tags are enforced for this repository. <sha> was not signed`.
Amend with `-S` and the SSH signing config:
```bash
git commit --amend --no-edit -S \
  -c user.signingkey=~/.ssh/id_ed25519.pub -c gpg.format=ssh -c commit.gpgsign=true
```
Local `git log --show-signature` may print `No signature` — that is the local
verifier missing `gpg.ssh.allowedSignersFile`, not a missing signature. Check the
object itself: `git cat-file commit HEAD | grep gpgsig` proves the commit is
signed; push it.

**Configure once per clone** — the settings are repo-local, so a fresh clone
needs them again:

```bash
git config gpg.format ssh
git config user.signingkey ~/.ssh/id_ed25519.pub
git config commit.gpgsign true
git config user.name "Firstname Lastname"
git config user.email "user.name@example.test"
```

SSH signing works **without ssh-agent** here (no agent running, key referenced
by path). GPG signing also works but needs a generated keyring.

Verify signing worked before blaming the hook — `%G?` in the log needs
`gpg.ssh.allowedSignersFile` set locally or it errors out and prints `N`:

```bash
git log --format='%h sig=%G? mail=%ae' -1
```

`sig=N` with a push rejection about signatures means the commit really is
unsigned. `sig=N` with a push rejection about issue keys means it got past
signing.

**Probe branches leave state on the server.** The server accepts them; they stay
in `refs/heads` until explicitly deleted. Always clean up and verify:

```bash
git ls-remote --heads origin | grep my-probe      # before and after
git push origin --delete my-probe
git ls-remote --heads origin | grep my-probe || echo clean
```

`git push origin --delete <name>` deletes exactly one ref by full path
(`refs/heads/<name>`); it takes no glob, cannot touch `master`, cannot touch
other repos, and does not fire `pre-receive` (which filters pushes, not ref
deletion). If `receive.denyDeletes` is set the command **fails safely** rather
than deleting.

**A stale remote-tracking ref proves deletion happened.** After the delete,
`git branch -vv` shows `[origin/my-branch: gone]` — useful when a delete command
was interrupted and you need to know whether it landed.

## Per-host proxy transport differs — probe, don't assume

The corp proxy at `127.0.0.1:12334` is not uniformly required or uniformly fatal; which
path works is a per-host property. Probe before concluding a host is unreachable:

```bash
curl -s -o /dev/null -w '%{http_code}\n' --max-time 20 --noproxy '*' "$URL"   # direct
curl -s -o /dev/null -w '%{http_code}\n' --max-time 20 --socks5-hostname 127.0.0.1:12334 "$URL"  # socks
```

Known split on this host: `hermes-agent.ru` and `huggingface.co` go direct; `api.telegra.ph`
answers ONLY over SOCKS5 (direct = connect timeout that reads as "API down"); `api.telegram.org`
needs PySocks from Python but NOT socks-via-curl (curl gets a schannel handshake failure);
`platform.claude.com` works direct. A `000` from a direct curl to a telegra URL is a
transport verdict, not a dead link — re-probe with `--socks5-hostname` before concluding
anything about the page.

**Python side:** both a disabled env proxy AND an explicit SOCKS socket are needed for
telegra - `socket.socket = socks.socksocket` + `socks.set_default_proxy(socks.SOCKS5,
"127.0.0.1", 12334, rdns=True)` + `urllib.request.build_opener(ProxyHandler({}))`.
Dropping the opener lets the env proxy hijack CONNECT. Use the hermes venv interpreter;
the comfyui venv has no `socks`.

### `000` from curl can be an untrusted CA, not a dead host - check with `-k` before concluding

Direct curl to an RF-hosted endpoint (`api.giga.chat`, gosuslugi-adjacent hosts)
returns `000` with `SEC_E_UNTRUSTED_ROOT` (schannel) or Python
`CERTIFICATE_VERIFY_FAILED`: the certificate is signed by the Russian Trusted CA
(Минцифры), absent from clean Windows and Python trust stores. The host is alive
and answering - TLS handshake fails before any HTTP happens, so you get no status
code at all, which reads exactly like "host unreachable".

Diagnose in one command: `curl -k` the same URL. 401/400/403 = network and host
are fine, only the trust store is missing. Confirm whose CA:
```bash
openssl s_client -connect HOST:443 -servername HOST -showcerts </dev/null \
  | openssl x509 -noout -issuer     # CN=Russian Trusted Sub CA → Минцифры
```
Fix = install the Минцифры root+sub CA (gosuslugi.ru/tls page) into the trust
store; after that plain requests succeed. Also verify the per-host transport
conclusion (direct vs proxy vs socks) only AFTER the CA is handled - a `000`
from a missing CA and a `000` from a blocked route look identical, and probing
the same host through a proxy adds a second unknown.

### A dead jump host in `~/.ssh/config` presents as an unreachable target

**Symptom:** `ssh <alias>` fails with `Connection timed out during banner exchange`
on port 65535, while the same host answers instantly by IP and the public HTTPS
endpoint returns 200.

**Root cause:** the alias carries a `ProxyJump` to a bastion that no longer
resolves or answers. The failure looks like the target is down; the target is
reachable. Note the odd port 65535 - that is the resolved-bastion-port placeholder,
not a real service.

**Diagnose in this order, cheapest first:**

```bash
grep -A8 "^Host <alias>$" ~/.ssh/config | grep -i proxyjump
nslookup <bastion> 2>&1 | tail -3          # Non-existent domain / Query refused = dead
ssh -o ProxyJump=none <user>@<host> hostname # does the target answer directly?
```

**Fix the config, not the command line.** Overriding with `-o ProxyJump=none` on
every call hides the breakage until the next session. Comment out the dead
`ProxyJump` line in `~/.ssh/config` (back the file up first), and note inline why.
Deduplicate while there: repeated `Host <alias>` blocks all carry their own
`ProxyJump`, so patch every occurrence or the earlier block wins.

## Live API writes need a script gate, not agent judgment

**Symptom:** a loop over message ids against a bot API silently rewrote five live
channel posts. The bot was a full administrator (`can_delete_messages`), Telegram
asks no confirmation for an edit, and the damage surfaced only when the channel
was read back.

**Root cause:** the rule existed as prose in the publishing skill, and prose cannot
refuse. The agent needed one message id, got a rejection, and substituted a range
sweep to "find out which ids are editable" - a write used as a probe.

**Rule: never call a live API directly from an agent to probe or fix.** Writes go
through a checked script that (a) rejects ranges and non-integer ids at argument
parsing, before any request; (b) requires an explicit apply flag, dry-run by
default; (c) takes `--expect <marker>` and compares it against the CURRENT
resource state, refusing when it does not match; (d) classifies provider error
strings into "stop and ask a human" vs "retry". Range rejection and the expect
check are what make "shot past the target" impossible rather than discouraged.

**Do not answer a destructive over-permission finding with "remove the
permission".** Asking for a read-only token to replace an admin token breaks the
posting path itself - the same account must read and write. Narrow what a write
can reach (script guards, dry-run, expect check), not the privilege the workflow
needs.

**Telegram specifics worth remembering:** caption limit is 1024 and a photo post is
edited with `editMessageCaption`, a text post with `editMessageText`; the provider
returns `400` with a JSON body that names the reason (`message to edit not found`,
`message can't be edited`, `MESSAGE_ID_INVALID`) - read it before retrying, all of
those mean stop. A send call's returned id proves nothing about visibility; read it
back before treating the operation as done.

**One canonical artifact per published thing.** Three near-identical caption files
accumulate in the same directory, they drift apart on the next edit, and the stale
one wins the next send - that is how a post ships pointing at a URL that was
superseded an hour earlier. The publishing step takes exactly one path and the
publisher deletes its siblings. Make the gate check the path, not the content: a
caption whose `img` or link target was already replaced elsewhere cannot be caught
by a length limit.

**A Telegra draft marker is permanent in the URL.** The slug is derived from the
title at `createPage` time and cannot be edited afterwards, so a title containing a
draft marker bakes that marker into the address for the page's life, and the API
has no delete. Finalising a draft means `editPage` on the SAME path with the clean
title. Creating a second page for a clean address leaves the marked one live
forever - do that only when the owner explicitly wants the clean URL, and then
remove the marked page by hand.

## Secret-masking in tool output fakes broken text — byte-check the FILE, not the log

**Symptom:** a `grep`/`sed` dump of your own file shows a mangled token — a variable like
`$OPENR..._KEY`, or `Authorization: ***` where `Bearer <token>` was written. You then burn
calls byte-hunting the "broken" string with python `bytes.replace` that keeps asserting
`count == 1` and failing.

**Root cause:** the Hermes tool-output layer masks secret-like patterns (substrings of
variables ending in `_KEY`, `Bearer ...`, token shapes) before display. The FILE on disk is
fine; the log line is a redaction. Two different renders of the same line (`sed` vs `python`)
show different masks, which makes it look like the file keeps changing.

**Rule:** before diagnosing text corruption, re-read the exact region as raw bytes
(`python -c "print(repr(open(p,'rb').read()[i:i+120]))"`) — bytes are never masked, logs are.
If the bytes contain the correct string, the defect exists only in the log and there is
nothing to fix.

## Verify-before-apply: repo config is desired state, not current state

**Symptom:** the repo's config file for a live service is missing entries the
service actually runs with. Copying the repo version onto the node silently
breaks a working service. Found this reading a reverse-proxy config from git
that had no TLS section while the live proxy was terminating TLS for a
published service that appeared nowhere in the repo (not in the service
inventory either).

**Rule:** before writing a live config from the repo, `cat` the live file and
diff. The epic rule that already exists in most of these projects ("change
desired state in git, apply to node") means the repo is authoritative for
**intent**, and the node is authoritative for **what is actually running**.
They diverge until someone reconciles.

**Harden the apply script against it.** A script that installs a config onto a
live node should refuse to run if a marker of the currently-working setup is
absent from the candidate file, and exit non-zero before touching anything.
Cheap to add, and it converts a silent outage into a failed gate.

```bash
for marker in known-working-service.example other-live-service.example; do
    grep -qF "$marker" "${NEW_CONFIG}" || { echo "REFUSING: marker missing: $marker" >&2; exit 2; }
done
```

**Corollary — inventory drift makes read-only checks lie green.** If the
service inventory omits running containers, a reconciliation script that
compares inventory against the hypervisor reports no discrepancies while whole
services are unaccounted for. Probe the address space (TCP connect sweep) when
you suspect the inventory is stale, and treat a suspicious reconciliation
result as "inventory incomplete" before "state is correct".

## Cyrillic and quotes in YAML rules break the parser

**Symptom:** a config file parses fine except for one scalar:
`yaml.scanner.ScannerError: found unknown escape character`.

**Root cause:** a backslash inside a double-quoted YAML scalar is an escape
sequence, so regex like `\.` in a routing rule becomes an invalid escape and
the file fails to load. Single-quoted scalars are literal and pass through.

**Fix:** wrap regex-bearing rules in single quotes, or avoid escapes by using a
character class (`[.]` instead of `\.`).

This fails only on the specific scalar, which is why the rest of the file looks
fine. Validate the whole file with the project's own parser, not by eyeballing
the lines that changed.

## A trailing `[[ … ]] && cmd` makes the script exit 1

**Symptom:** a shell script runs correctly, prints the expected report, and still returns
non-zero, so any caller gating on the exit code treats success as failure.

**Root cause:** `[[ -n "$OUT" ]] && save_report` as the final statement evaluates false when the
variable is empty, and the conditional's status becomes the script's status.

**Fix:** explicit `if` block plus explicit `exit 0`. Also prefer this when the script's real
failure modes must carry distinct exit codes — a probe that returns "no usable completions" should
exit with its own code rather than colliding with a generic error.

## Windows-утилиты отдают русский текст в cp1251 → скрипп молча врёт

**Symptom:** скрипт парсит вывод `ping`/`nslookup`/`ipconfig`/`netstat`/`sc qc`
и получает пустые значения, после чего решает, что хост недоступен — хотя хост
отвечает (`TTL=104` в том же самом «мусорном» выводе). Код возврата 0, исключения нет.

**Root cause:** эти утилиты печатают русский текст в однобайтовой кодировке
консоли (cp1251/cp866). UTF-8-декодер превращает его в мусор, регулярка не
находит ни поля, ни числа. Это худший вид поломки: не падает, а говорит неправду.

**Fix — приводить кодировку на входе, до парсинга:**
```bash
ping -n 1 -w 800 8.8.8.8 2>&1 | iconv -f cp1251 -t utf-8
```
В subprocess: `subprocess.run(..., encoding="utf-8", errors="replace")` поверх
явно перекодированного вывода, либо `out.decode("cp1251", "replace")`.

**Правило для скриптов:** любой вывод Windows-утилиты, который может содержать
русский текст, гонить через `iconv`. У `curl` и `git` проблемы нет — они отдают
ASCII плюс UTF-8, их перекодировать не нужно.

**Соседний случай, не кодировка, а локаль:** инструмент может требовать UTF-8-локаль
по КОДОВОЙ СТРАНИЦЕ консоли, а не по переменной окружения. `LANG=C.UTF-8 LC_ALL=C.UTF-8`
в git-bash такой проверке не удовлетворяет. Рабочие пути: запускать через cmd с
кодовой страницей 65001, либо ставить инструмент в отдельный venv.

## paramiko для доступа к стендам (Windows-агент)

Снять cmd.exe-квотинг для администрирования: `direct-tcpip` через бастион вместо
`ProxyCommand`, `allow_agent=False`/`look_for_keys=False`, нативные пути к ключу,
удалённый `py3compat` в paramiko 5.x. Рецепт и шаблоны:
`references/paramiko-bastion-admin.md`.

## `git commit -F <MSYS-path>` fails: native git can't read the path

**Symptom:** `git commit -F /tmp/msg.txt` (file written and listed by `ls`)
dies with `fatal: could not read log file '/tmp/msg.txt': No such file or directory`,
even though `git commit -m "..."` works in the same shell.

**Root cause:** native Windows git.exe resolves the message-file path itself, without
MSYS translation — `/tmp/...` is meaningless to it. Same family as clone/ffmpeg above,
but hits an *input* file, not just destinations.

**Fix:** pass a Windows-form path (`C:/Users/<u>/AppData/Local/Temp/msg.txt`) or,
simpler, write the file inside the repo and use a relative path:
`cp /tmp/msg.txt ./msg.txt && git commit -F msg.txt && rm msg.txt`.
Same applies to `git tag -F`, `git notes -F`.

## Git not on PATH / git-bash dead → GitHub Desktop bundled git.exe

**Symptom:** every `terminal` call fails with `Top-level not found:
C:\Program Files\Git\bin` (the MSYS git-bash install dir is gone), and
`shutil.which('git')` from Python returns None — there is no git on PATH.

**Fix — run GitHub Desktop's bundled git by absolute path from
execute_code/subprocess:**
```python
import glob, subprocess
GIT = (glob.glob(r'C:\Users\<u>\AppData\Local\GitHubDesktop\app-*'
                 r'\resources\app\git\cmd\git.exe') or [None])[0]
def g(*args, cwd=REPO, timeout=180):
    r = subprocess.run([GIT, *args], cwd=cwd, capture_output=True, timeout=timeout)
    return (r.stdout + r.stderr).decode('cp1251', errors='replace')
g('add', 'file.md'); g('commit', '-m', '...'); g('push', 'origin', 'master')
```
- The version segment (`app-3.6.2`) changes on GitHub Desktop updates —
  always glob, never hardcode.
- Decode git output as cp1251: localized git messages are cp1251, and a
  utf-8 decode inside subprocess reader threads throws UnicodeDecodeError
  and swallows the output.
- Run git subcommands as separate list-arg calls (add / commit / push), not
  one `shell=True` chain — commit-message Cyrillic plus shell quoting
  through cmd is the same mangling family as the SSH section above.
- Push verification without bash: `g('fetch','origin')` then compare
  `g('rev-parse','origin/master')` against the local head instead of
  `tail`-ing push output.

## terminal/git-bash dead → do the whole task from execute_code

When the terminal shim is broken (`Top-level not found: C:\Program
Files\Git\bin` on EVERY terminal call) and no git.exe is on PATH, the
execute_code kernel still has full stdlib + network. Convert the task:

- Download a GitHub repo WITHOUT git:
  `urllib.request.urlretrieve("https://codeload.github.com/<org>/<repo>/zip/refs/heads/main", tmp)`
  then `zipfile` — filter `zf.namelist()` to extract ONLY the needed subtree
  (e.g. `skills/<name>/` into the Hermes profile skills dir) instead of cloning.
- requests/urllib to EXTERNAL hosts (github, crt.sh) work fine from the
  kernel — verify with a 1-line GET before assuming SSL/proxy problems.
- Parallel external probes: `concurrent.futures.ThreadPoolExecutor(8-10)` +
  `ex.map` — a 10-host DNS/TLS/header matrix finishes in ~3s. Batch the whole
  probe set into ONE execute_code call instead of per-host tool calls.
- Verify kernel results the same way you would terminal results (print paths,
  status codes, file counts) — with no terminal there is no second line of
  verification.
- Skill installed this way: confirm Hermes sees it with
  `skill_view(name)` (readiness_status available) before running it.

## Gmail IMAP via himalaya config (app-password with spaces)

Gmail app-passwords are stored space-grouped (`xxxx xxxx xxxx xxxx`); IMAP
LOGIN requires the password WITHOUT spaces. Read it from the himalaya config
(`C:\Users\<u>\.config\himalaya\config.toml`, line `passwd.cmd = "echo '...'"`),
strip spaces in code, and never print it. The himalaya account name is the
config key (e.g. `gmail`), NOT the email address — `himalaya envelope list -a
<email>` fails with "cannot find configuration for account".

On Windows skip the himalaya CLI for scripted checks (a `-c tmpconfig` run
hangs on the echo-quoting) — connect with `imaplib.IMAP4_SSL('imap.gmail.com',
993)` from execute_code instead: login, `select('INBOX', readonly=True)`,
`search`, `fetch(...BODY.PEEK...)`. Works in ~2s and stays read-only.

## computer_use (cua) + CDP on the same Chrome: coordinate spaces do not mix

- `capture` requires BOTH `pid` and `window_id` — pid alone is refused with 0
  elements. In capture output, element `bounds` are NATIVE desktop px, while
  the `coordinate=` accepted by click/key actions is the LAST CAPTURE's
  screenshot-pixel space (window-relative; cua scales it itself). CDP
  `Input.dispatchMouseEvent` takes CSS viewport px. Mixing these lands clicks
  ~17% off plus the window offset on a scaled display — no error, just missed
  targets. Always derive click coordinates from a FRESH capture, never from a
  previous turn's bounds.
- Bare `element` index is refused by cua 0.17 (needs element_token/
  snapshot_id) — click by coordinate from the fresh capture instead.
- Background keystrokes to Chrome are dropped (background_unavailable) —
  follow the verdict and re-issue with `delivery_mode: "foreground"` (brief
  focus steal; fine when the user said they are away).
- Verify every input via a read-only DOM read (e.g. `aria-checked` through
  CDP `js()`), never trust the action's `ok:true` — it confirms delivery, not
  effect.
- Anti-automation SPAs (Typeform-class widgets) may ignore synthetic DOM
  events, CDP mouse events AND OS letter-keys alike. Do not grind: pivot to
  (1) a cua native click from a fresh capture (click the row's left part where
  the checkbox square sits), (2) Enter via cua key foreground to submit the
  active question, (3) after a few failures hand the form URL to the user —
  the outcome (waitlist position) matters more than the optional questionnaire.
- Localhost HTTP from Python hits the system proxy: checking the CDP port
  returns HTTPError. Use `urllib.request.build_opener(urllib.request.ProxyHandler({}))`
  for any 127.0.0.1 check.
- `tasklist`/`netstat` output on RU Windows is cp866: decode
  `r.stdout.decode('cp866', 'replace')` or the subprocess reader thread dies
  on Cyrillic output.

## CDP Chrome not running: launch it yourself from execute_code

`browser_exec` fails with `BU_CDP_URL http://127.0.0.1:9222 unreachable`
when no automation Chrome is listening. Start one from the kernel:

```python
import subprocess
flags = 0x01000000  # CREATE_BREAKAWAY_FROM_JOB: Chrome survives kernel reset
subprocess.Popen([
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "--remote-debugging-port=9222",
    r"--user-data-dir=C:\Users\<u>\chrome-cdp-profile",
    "--no-first-run", "--no-default-browser-check", "--headless=new",
    "about:blank"], creationflags=flags)
```

Verify readiness with the proxy-free opener (see the SearXNG note): a plain
`urlopen('http://127.0.0.1:9222/json/version')` returns **HTTP 502 Bad Gateway**
while the browser is perfectly alive — the env proxy (127.0.0.1:12334)
intercepts localhost. `build_opener(ProxyHandler({}))` shows the real status.
`--headless=new` is enough for browser_exec/CDP scraping; drop it only when a
visible window is required. Chrome must take `C:\...` paths for
`--user-data-dir` (see the MSYS path section above).

## Self-contained mailbox-watch cron

Cron jobs run in a fresh session with no chat context: the prompt must carry
the whole IMAP recipe itself — config path, the space-strip rule, "never print
the password", read-only BODY.PEEK, an exact one-line string to answer when
there is no news (so repeats stay quiet), and `continuity: true` so the job
diffs against its own previous output instead of re-announcing old mail.

## `git pull --rebase` aborts on untracked dirs that origin already deleted

**Symptom:** `git pull --rebase origin master` (or plain `git merge`) fails with
"Please move or remove them before you switch branches / could not detach HEAD", naming
directories that look like the user's own recent work. `git push` first reports
"tip of your current branch is behind its remote counterpart".

**Root cause:** the working tree carries untracked article/project directories that exist
locally but were already committed and removed in origin (typically because the same work
was pushed from another machine or a parallel session). Rebase refuses to touch untracked
files that a checkout would need to replace.

**Fix:** compare before removing anything - do NOT blanket-delete, the local copy may be
newer:
```bash
git fetch origin master
git ls-tree -r origin/master --name-only > /tmp/origin-files
# for each untracked path: compare local sha1 against `git cat-file -p origin/master:<path>`
git cat-file -p origin/master:<path> | sha1sum
```
Move aside only the entries that differ from origin or are absent from it; leave identical
ones in place. Then `git merge origin/master --no-edit` and push. Treat a directory as
someone's work until the diff proves otherwise.

## Client-supplied documents land in the profile cache — canonicalize into the project dir first

**Symptom:** the client sends multi-file material (audits, specs, questionnaires)
through chat; the platform saves it to the profile document cache under hashed names
(`...profiles/<profile>/cache/documents/doc_<hash>_<name>.md`). Building the project
around hashed cache paths loses it later — the cache is disposable cleanup fodder.

**Rule:** first action on receiving such material — create the client project dir
`C:\Work\<client>\`, copy documents there under real names in a topical
subfolder (e.g. `it-audit/`), keep a `CARD.md` per the local project-card convention
(in-repo example: `C:\Work\PROJ-2000\CARD.md`). Then VERIFY the copies:
`os.path.getsize` + short `sha256` per file, and after any text write read it back
and compare (`back == content`). Never cite cache paths in the card.

**Run the file ops in execute_code** (os/shutil/hashlib) — it sees the whole
filesystem even when the terminal shim is dead (see the terminal-dead section
above). If the `write_file` tool itself errors with the same shim error, fall back
to `open(path,'w',encoding='utf-8')` in execute_code and verify by reading back.
Filesystem discovery may also transiently fail right after session start (`could
not stat ... sandbox may still be starting`) — sleep/retry inside execute_code
instead of concluding the path does not exist.
