# PowerShell 5.1 and local-endpoint verification on Windows

Two traps that both fail *silently into a false pass*, which is why they belong together: the
interpreter is not the one you assumed, and the endpoint is not serving what you asked for.

## PowerShell 5.1 is the default interpreter and lacks `??`

**Symptom:** a script written with modern PowerShell syntax runs on a machine with no `pwsh` and
dies with a parse error before any logic executes. The visible frame is `Invoke-Expression` or a
`-Command` string, so the error points at the wrapper, not the operator that broke.

**Root cause:** Windows ships PowerShell **5.1** as `powershell.exe`; `pwsh` (7+) is a separate
install that may not exist. 5.1 predates `??` and `?:` entirely, and has no ternary.

```powershell
# wrong on 5.1 — parse error, nothing runs
$url = $cfg.endpoint ?? "http://127.0.0.1:1234/v1"

# 5.1-safe
if (-not $url) { $url = "http://127.0.0.1:1234/v1" }
```

Banned on 5.1: `??`, `?:`, `&&`/`||` pipeline chains, `-Parallel`, `Get-Error`.

**Diagnose the interpreter before the script:** `$PSVersionTable.PSVersion`. If it reports 5.1,
write 5.1 grammar — do not "fix" the calling code. `Invoke-Expression` hides the real line number,
so a parse error there misleads you into debugging the wrapper.

## A local LLM endpoint may silently substitute the model it loaded

**Symptom:** a validation script requests one model, receives a well-formed chat response, and
reports PASS — while the `model` field in the JSON body names a completely different model. An
embedding-model check therefore "passes" against a loaded generative model, and every conclusion
drawn from that response is about a model you never asked for.

**Root cause:** OpenAI-compatible local servers (LM Studio and similar) treat the model name as a
hint, not a guarantee. A loaded-model mismatch is not an error condition upstream, so nothing
raises.

**Fix:** assert on the `model` field of the *response*, never on the name you sent.

```powershell
$resp = Invoke-RestMethod -Uri "$base/chat/completions" -Method Post -Body $body
if ($resp.model -ne $expected) {
    Write-Error "endpoint served '$($resp.model)', expected '$expected'"
    exit 7
}
```

`/v1/models` listing the expected model is necessary but not sufficient — it advertises what is
available, not what is loaded. Only the response body tells you what actually ran.

Give the mismatch its own non-zero exit code so no caller gating on status can read the
substitution as a green run, and echo both names into the error so the report names the real model.

## Related: the general shape

Both defects share a mechanism — a layer that can differ from the one you assumed, and reports
success anyway. When a verification script on this host returns "fine", the first question is
which interpreter ran and which model answered, not whether the check was thorough.
