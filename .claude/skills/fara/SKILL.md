---
name: fara
description: Run the fara browser-automation agent against any natural-language task. Handles pre-flight checks, flag construction, output monitoring, auth-wall relay, and streaming-state awareness. Trigger: "use fara to …", "ask fara to …", "have fara …", "run fara", "fara: …"
---

<!-- Canonical skill: .agents/skills/fara/SKILL.md — follow all steps there. -->
<!-- This file adds Claude Code-specific tool guidance for Steps 4–5 only. -->

See `.agents/skills/fara/SKILL.md` for the full skill definition. Apply all steps from that file, with these Claude Code-specific overrides:

## Step 4 override — Execution

Use **Bash** with `run_in_background: true` and `timeout: 300000`. Immediately follow with a **Monitor** tool call on the same process to receive each stdout line as a notification.

```powershell
Set-Location F:/github/fara-agent
uv run run_agent.py <flags>
```

## Step 5 override — Output Monitoring

Use the **Monitor** tool (not polling). Each stdout line arrives as a notification — react to the same table of patterns defined in the canonical skill.

For the `[AUTH REQUIRED]` case: tell the user Claude cannot press Enter in the terminal — they must do it manually in the Edge window.
