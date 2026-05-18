---
name: fara
description: Run the fara browser-automation agent against any natural-language task. Handles pre-flight checks, flag construction, output monitoring, auth-wall relay, and streaming-state awareness. Trigger: "use fara to …", "ask fara to …", "have fara …", "run fara", "fara: …"
---

<!-- Canonical skill: .agents/skills/fara/SKILL.md — follow all steps there. -->
<!-- This file adds Claude Code-specific tool guidance for Steps 4–5 only. -->

See `.agents/skills/fara/SKILL.md` for the full skill definition. Apply all steps from that file, with these Claude Code-specific overrides:

## Step 4 override — Execution

**Pre-flight runs on every attempt, including retries.** Fara stops llama-server on exit, so a previous run may have left it down. Always re-check ports before constructing flags.

Use **Bash** with `run_in_background: true` and `timeout: 300000`. The working directory must be set inside the command (not via `Set-Location`, which is PowerShell-only and fails silently in Bash):

```bash
cd F:/github/fara-agent && uv run run_agent.py <flags>
```

Immediately follow with a **Monitor** tool call on the same output file.

## Step 5 override — Output Monitoring

Use the **Monitor** tool (not polling). Monitor runs **bash** — use `tail -f | grep --line-buffered`, never PowerShell (`Get-Content -Wait`) syntax:

```bash
tail -f "<output-file>" | grep --line-buffered -E "terminated|completed|AUTH REQUIRED|\[ERROR\]|Memorized|\[INFO\] Round"
```

Each matching stdout line arrives as a notification — react to the same table of patterns defined in the canonical skill.

For the `[AUTH REQUIRED]` case: tell the user Claude cannot press Enter in the terminal — they must do it manually in the Edge window.
