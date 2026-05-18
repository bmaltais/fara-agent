# Agent Guide — fara-agent

Local browser automation agent powered by [Microsoft Fara-7B](https://www.microsoft.com/en-us/research/blog/fara-7b-an-efficient-agentic-model-for-computer-use/) running via llama.cpp. No cloud, no API keys — everything runs on a consumer GPU.

## Architecture

| File | Role |
|---|---|
| `run_agent.py` | CLI entrypoint — arg parsing, model download, server/Edge launch, agent lifecycle |
| `agent.py` | `FaraAgent` — vision loop: screenshot → model → parse tool_call → execute → repeat |
| `browser.py` | Playwright wrapper — headless/headful, CDP attach, action execution |
| `prompts.py` | System prompt and action format fed to the model |
| `message_types.py` | Typed structures for model messages |
| `utils.py` | Shared helpers |
| `config.json` | Runtime configuration (paths, model params, browser settings) |
| `start_edge.ps1` | Launches Edge with CDP enabled, auto-detects profile |
| `start_server.bat` | Launches llama-server manually |

## Setup

```powershell
uv sync
uv run playwright install chromium
```

Requires `llama.cpp` binaries at `F:/llama.cpp/` (or override `llama_cpp_path` in `config.json`).

## Running

```powershell
# Full auto: start inference server + launch Edge + run task
uv run python run_agent.py --task "..." --start-server --start-edge

# Attach to an already-running browser
uv run python run_agent.py --task "..." --cdp-url http://localhost:9222

# Headless with llama-server already running
uv run python run_agent.py --task "..."
```

## Key Configuration (`config.json`)

- `model_path` / `model_repo` / `model_filename` — GGUF model location; auto-downloaded from HuggingFace if missing
- `mmproj_path` / `mmproj_filename` — multimodal projector file (required for vision)
- `llama_cpp_path` — path to `llama-server.exe`
- `llama_cpp_args.ctx_size` — context window (16 384 default; model supports up to 32 K)
- `cdp_url` — set to `http://localhost:9222` to attach to a running Chrome/Edge
- `max_rounds` — agent action limit (default 20)
- `temperature` — keep at `0.0` for deterministic tool calls

## Development conventions

- **Python tooling**: always use `uv`, never `pip` directly
- **Formatting**: `black` before any commit
- **No tests yet** — if you add tests, use `pytest` via `uv run pytest`
- **No type checker configured** — state this explicitly rather than skipping silently
- **Secrets**: never hardcode paths or credentials; keep everything in `config.json` or env vars
- **Screenshots**: written to `./screenshots/` each round — gitignored, safe to delete
- **Downloads**: written to `./downloads/` — gitignored

## External dependencies (not in repo)

| Dependency | Default path | Notes |
|---|---|---|
| llama-server | `F:/llama.cpp/llama-server.exe` | Build from [ggerganov/llama.cpp](https://github.com/ggerganov/llama.cpp) |
| Fara-7B GGUF | `F:/models/microsoft_Fara-7B-Q8_0.gguf` | Auto-downloaded from HuggingFace on first run |
| mmproj file | `F:/models/` | Auto-downloaded alongside the model |
| Microsoft Edge | `C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe` | CDP mode only |

## Common failure modes

| Symptom | Fix |
|---|---|
| `llama-server did not become ready` | Model file missing or GPU OOM — check `model_path` and VRAM |
| `CDP connection refused` | Browser not started with `--remote-debugging-port=9222` |
| Agent loops / oscillates | Temperature not `0.0`; or reduce `max_rounds` |
| Auth wall detected | Agent pauses and prompts user to log in manually (headful mode only) |
