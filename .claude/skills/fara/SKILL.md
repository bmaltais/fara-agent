---
name: fara
description: Run the fara browser-automation agent against any natural-language task. Handles pre-flight checks, flag construction, output monitoring, auth-wall relay, and streaming-state awareness. Trigger: "use fara to …", "ask fara to …", "have fara …", "run fara", "fara: …"
---

# Fara Skill

## Trigger
Invoke when the user says anything like:
- "use fara to …", "ask fara to …", "have fara …", "run fara", "fara: …"

---

## Step 1 — Pre-flight Port Checks

Run both checks in parallel (PowerShell):

```powershell
# llama-server on 8080
$llama = try { (Invoke-WebRequest http://localhost:8080/health -TimeoutSec 2).StatusCode -eq 200 } catch { $false }
# Edge CDP on 9222
$edge  = try { (Invoke-WebRequest http://localhost:9222/json/version -TimeoutSec 2).StatusCode -eq 200 } catch { $false }
Write-Output "llama=$llama edge=$edge"
```

---

## Step 2 — Flag Selection

```
flags = --task "<task>"
if not llama_running: flags += --start-server
if not edge_running:  flags += --start-edge
```

Always set `--cdp-url http://localhost:9222` when edge is already running.

---

## Step 3 — Task Prompt Engineering

**This is the most important step.** A poorly worded task causes fara to loop uselessly.

### Rules for every task prompt:

1. **Name the exact UI element** — use the label visible on screen (e.g., `"Ask anything"` for Grok's input, `"Search"` for a search bar). Fara-7B reads screenshots; it responds to exact text labels.

2. **Forbid coordinate clicks when auto-focus exists** — If the target input is focused on page load (Grok, Google), say explicitly: *"do NOT click. Use the `type` action with NO coordinate."* Without this, the model will click at wrong coordinates.

3. **Teach streaming-state recognition** — For any page that shows incremental output (Grok, ChatGPT, Perplexity, streaming search results), add this sentence verbatim to the task:
   > "After pressing Enter, you may see '...', 'Thinking about your request', or partial text appearing — this means the response is loading. Do NOT retype the question. Use the `wait` action (5 s) repeatedly until the full response appears."

4. **Specify termination condition explicitly** — Fara will terminate when told; without this it may stop early or loop. End every task with: *"Once the full response is visible, terminate with success."*

### Grok (x.com/i/grok) task template:
```
Navigate to https://x.com/i/grok. The 'Ask anything' input is auto-focused on page load — do NOT click anything. Use the `type` action with NO coordinate to type: '<question>' with press_enter set to true. After pressing Enter you may see '...', 'Thinking about your request', or partial text streaming — this means Grok is generating a response. Do NOT retype the question. Use the `wait` action (5 s intervals) until the full response is visible. Once complete, terminate with success.
```

---

## Step 4 — Command Construction & Execution

```powershell
Set-Location F:/github/fara-agent
uv run run_agent.py <flags>
```

Run via Bash with `run_in_background: true`; timeout **300 000 ms** (5 min — model load can take ~90 s on first start).

---

## Step 5 — Output Monitoring

After the run completes, surface the result:

| Output contains | Action |
|----------------|--------|
| `[INFO] Task terminated: success` | Report success; show last 10 log lines |
| `[INFO] Task completed after 15 rounds` without `terminated` | Likely looped — check `./screenshots/screenshot14.png` and report what was visible |
| `[AUTH REQUIRED]` | Tell the user: *"Fara is blocked by a login wall at [URL]. Switch to the Edge window, complete the login, then press Enter in the terminal running fara."* Wait for user to say "done" or "continue", then monitor for resumed output |
| `[ERROR]` lines | Surface verbatim |

---

## Step 6 — Known Limitations

- **Visual grounding offset (~100 px vertical)** — Fara-7B's coordinate predictions are offset ~100 px below the actual element. Mitigate with `type` (no coordinate) + auto-focus whenever possible. If a click is unavoidable, add: *"The element is higher on screen than it appears — click slightly above where you expect it."*
- **Streaming states cause retries** — Without explicit streaming-state guidance in the task, fara will retype the question when it sees a partial/loading response. Always include the streaming instruction (Step 3, rule 3).
- **Conversation URL confusion** — If the browser is already on `x.com/i/grok?conversation=...`, navigate to `https://x.com/i/grok` (clean URL) first so the input is auto-focused.
