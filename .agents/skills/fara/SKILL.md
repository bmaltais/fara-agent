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

Check both services before building flags:

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

Always set `--cdp-url http://localhost:9222` when Edge is already running.

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

### Bing (bing.com) task template:
```
Navigate to https://www.bing.com. Click the search box, then type: '<query>' and press Enter. Wait for the results page to load fully (use `wait` 3 s if needed). Once results are visible, terminate with success.
```

---

## Step 4 — Command Construction & Execution

Run the agent as a background process from the repo root, streaming stdout so you can react to live output:

```powershell
Set-Location F:/github/fara-agent
uv run run_agent.py <flags>
```

Run with a **5-minute timeout** — model load on cold start takes up to 90 s. Stream or poll stdout line-by-line while the process runs.

---

## Step 5 — Output Monitoring

React to each output line:

| Output contains | Action |
|----------------|--------|
| `[INFO] Task terminated: success` | Report success to the user; show last 10 lines of output |
| `[INFO] Task terminated: failure` | Report failure verbatim; check `./screenshots/screenshot{N-1}.png` for the last visible state |
| `[INFO] Task completed after 15 rounds` (no `terminated`) | Rounds exhausted — likely looped or hit an auth wall. Check `./screenshots/screenshot14.png` and tell the user what was visible |
| `[AUTH REQUIRED]` | Tell the user: *"Fara is paused at a login wall. Switch to the Edge window and log in. When done, press Enter in the terminal where fara is running."* Continue monitoring — fara resumes automatically after Enter |
| `[ERROR]` lines | Surface verbatim |

---

## Step 6 — Known Limitations

- **Visual grounding offset (~100 px vertical)** — Fara-7B's coordinate predictions are offset ~100 px below the actual element. Mitigate with `type` (no coordinate) + auto-focus whenever possible. If a click is unavoidable, add: *"The element is higher on screen than it appears — click slightly above where you expect it."*
- **Streaming states cause retries** — Without explicit streaming-state guidance in the task, fara will retype the question when it sees a partial/loading response. Always include the streaming instruction (Step 3, rule 3).
- **Conversation URL confusion** — If the browser is already on `x.com/i/grok?conversation=...`, navigate to `https://x.com/i/grok` (clean URL) first so the input is auto-focused.
