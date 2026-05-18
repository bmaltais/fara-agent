"""
Integration test runner for auth-wall detection (issue #1).

Runs fara as a subprocess, watches for [AUTH REQUIRED], writes a flag file
so the observer (Claude) can see it, then waits for a resume flag before
sending Enter to fara's stdin.

Usage:
    uv run test_auth_wall.py

Flag files (in system temp):
    fara_auth_needed.flag  — written when [AUTH REQUIRED] is detected
    fara_auth_resume.flag  — create this to unblock fara and resume the loop
"""
import subprocess
import os
import time
import tempfile

TEMP = tempfile.gettempdir()
AUTH_FLAG   = os.path.join(TEMP, "fara_auth_needed.flag")
RESUME_FLAG = os.path.join(TEMP, "fara_auth_resume.flag")
OUTPUT_FILE = os.path.join(TEMP, "fara_test_output.log")

TASK = (
    "Go to x.com/grok and ask Grok for a detailed report on "
    "Microsoft FARA (Foreign Agents Registration Act) filings or activities."
)

for f in [AUTH_FLAG, RESUME_FLAG, OUTPUT_FILE]:
    try:
        os.remove(f)
    except FileNotFoundError:
        pass

print(f"[RUNNER] Starting fara...")
print(f"[RUNNER] Output log : {OUTPUT_FILE}")
print(f"[RUNNER] Auth flag  : {AUTH_FLAG}")
print(f"[RUNNER] Resume flag: {RESUME_FLAG}", flush=True)

proc = subprocess.Popen(
    ["uv", "run", "run_agent.py",
     "--task", TASK,
     "--start-server",
     "--start-edge"],
    cwd=os.path.dirname(os.path.abspath(__file__)),
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

auth_triggered = False

with open(OUTPUT_FILE, "w", encoding="utf-8") as log:
    for line in proc.stdout:
        print(line, end="", flush=True)
        log.write(line)
        log.flush()

        if "[AUTH REQUIRED]" in line and not auth_triggered:
            auth_triggered = True
            with open(AUTH_FLAG, "w") as f:
                f.write(line.strip())
            print("[RUNNER] Auth wall detected — waiting for resume signal...", flush=True)
            while not os.path.exists(RESUME_FLAG):
                time.sleep(0.5)
            os.remove(RESUME_FLAG)
            print("[RUNNER] Resume signal received — sending Enter to fara...", flush=True)
            proc.stdin.write("\n")
            proc.stdin.flush()

proc.wait()
print(f"[RUNNER] fara exited with code {proc.returncode}", flush=True)

# Print pass/fail verdict
with open(OUTPUT_FILE, encoding="utf-8") as f:
    output = f.read()

exhausted = "Task completed after 15 rounds" in output
terminated_ok = "Task terminated" in output or "Task completed after" in output

if auth_triggered:
    print("\n[PASS] Auth wall detected, fara paused and resumed correctly.")
elif not exhausted and terminated_ok:
    print("\n[PASS] No auth wall needed — task completed normally (user was already logged in).")
else:
    print("\n[FAIL] Auth wall was NOT detected and fara exhausted all rounds.")
