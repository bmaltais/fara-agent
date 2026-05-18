# Fara Browser Automation Agent

A local browser automation agent based on [Microsoft Fara-7B](https://www.microsoft.com/en-us/research/blog/fara-7b-an-efficient-agentic-model-for-computer-use/), powered by [llama.cpp](https://github.com/ggerganov/llama.cpp) for inference.

Run browser automation locally on a consumer-grade GPU with quantized models — no cloud, no API keys.

## Features

- 100% local AI browser agent
- Quantized GGUF model support via llama.cpp
- Auto-downloads the model on first run
- Completely self-contained (no external dependencies)
- Browser automation via Playwright
- Attach to a running Chrome/Edge instead of launching a new browser

## Requirements

- [llama.cpp](https://github.com/ggerganov/llama.cpp) binaries installed at `F:/llama.cpp/`
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.11+
- A Chromium-based browser (Chrome or Edge) if using CDP attach mode

## Setup

### 1. Install dependencies

```powershell
uv sync
uv run playwright install chromium  # installs the managed Chromium browser
```

### 2. Configure

Edit `config.json` to set paths and options:

```json
{
  "llama_cpp_path": "F:/llama.cpp/llama-server.exe",
  "model_path": "F:/models/microsoft_Fara-7B-Q8_0.gguf",
  "model_repo": "bartowski/microsoft_Fara-7B-GGUF",
  "model_filename": "microsoft_Fara-7B-Q8_0.gguf"
}
```

The model is downloaded automatically from HuggingFace on first run if `model_path` does not exist.

To use a different quantization, change both `model_filename` and `model_path` to match
(e.g. `microsoft_Fara-7B-Q5_K_M.gguf` for a smaller/faster variant).

### 3. Run the agent

**Auto-start llama-server + launch Firefox:**
```powershell
uv run python run_agent.py --task "Go to wikipedia.org and search for cats" --start-server --headful
```

**If llama-server is already running:**
```powershell
uv run python run_agent.py --task "Go to wikipedia.org and search for cats" --headful
```

**Attach to a running Chrome/Edge browser:**
```powershell
uv run python run_agent.py --task "Go to wikipedia.org and search for cats" --cdp-url http://localhost:9222
```

## Starting llama-server manually

```powershell
start_server.bat
```

Or directly:
```powershell
F:\llama.cpp\llama-server.exe -m F:\models\microsoft_Fara-7B-Q8_0.gguf -ngl 99 -c 8192 --port 8080
```

The server exposes an OpenAI-compatible API at `http://localhost:8080/v1`.

## CDP browser attach mode

Attach the agent to a running Chrome or Edge browser instead of launching a managed one.

### Automatic (recommended)

Use the `--start-edge` flag — it handles everything: closes existing Edge instances, launches Edge with your active profile and CDP enabled, waits until ready, then runs the task.

```powershell
uv run python run_agent.py --task "..." --start-server --start-edge
```

The `start_edge.ps1` script auto-detects:
- Edge executable location
- User data directory (`%LOCALAPPDATA%\Microsoft\Edge\User Data`)
- Most recently used profile

Override any of these in `config.json` under the `"edge"` key:

```json
"edge": {
  "port": 9222,
  "exe": "",
  "user_data_dir": "",
  "profile": ""
}
```

Leave values as `""` to use auto-detection.

### Manual

Run `start_edge.ps1` yourself, then pass `--cdp-url`:

```powershell
.\start_edge.ps1
uv run python run_agent.py --task "..." --cdp-url http://localhost:9222
```

Or point to an already-running Chrome/Edge that was started with `--remote-debugging-port=9222`.

> **Notes:**
> - CDP mode requires a Chromium-based browser (Chrome or Edge)
> - All existing Edge windows must be closed before `--start-edge` (the script handles this automatically)
> - Downloads are not captured in CDP mode
> - If another process (e.g. D5 Render) is using port 9222, the script kills it automatically

## Configuration reference

| Key | Default | Description |
|---|---|---|
| `base_url` | `http://localhost:8080/v1` | llama-server API endpoint |
| `api_key` | `no-key` | Unused by llama-server; kept for API compatibility |
| `model` | `fara` | Model name sent in API requests (ignored by llama-server) |
| `llama_cpp_path` | `F:/llama.cpp/llama-server.exe` | Path to llama-server binary |
| `model_path` | `F:/models/microsoft_Fara-7B-Q8_0.gguf` | Path to GGUF model file |
| `model_repo` | `bartowski/microsoft_Fara-7B-GGUF` | HuggingFace repo for auto-download |
| `model_filename` | `microsoft_Fara-7B-Q8_0.gguf` | Filename within the HuggingFace repo |
| `llama_cpp_args.ngl` | `99` | GPU layers (-ngl) |
| `llama_cpp_args.ctx_size` | `16384` | Context length (16K recommended; model supports up to 32K) |
| `llama_cpp_args.port` | `8080` | llama-server port |
| `cdp_url` | `null` | CDP endpoint to attach to a running browser |
| `max_rounds` | `20` | Maximum agent action rounds |
| `temperature` | `0.0` | Sampling temperature |
| `max_n_images` | `1` | Screenshots kept in model context |
| `save_screenshots` | `true` | Save screenshots each round |
| `screenshots_folder` | `./screenshots` | Screenshot output directory |
| `downloads_folder` | `./downloads` | Download save directory |
| `show_overlay` | `true` | Debug HUD in headful mode |
| `show_click_markers` | `true` | Visual click/hover markers in headful mode |

## CLI flags

| Flag | Description |
|---|---|
| `--task TEXT` | Task for the agent to perform (required) |
| `--headful` | Show the browser window |
| `--start-server` | Launch llama-server before running |
| `--start-edge` | Launch Edge with CDP via `start_edge.ps1` (auto-detects profile) |
| `--cdp-url URL` | Attach to an already-running browser via CDP (overrides config) |
| `--config PATH` | Path to config file (default: `config.json`) |

## How it works

1. **Model inference**: llama-server runs the Fara-7B GGUF model locally, serving an OpenAI-compatible API
2. **Browser control**: Playwright controls Chromium (or attaches to Chrome/Edge via CDP)
3. **Vision loop**: Each round — take screenshot → send to model → parse `<tool_call>` response → execute action → repeat
4. **Actions**: click, type, scroll, navigate, hover, keypress, wait, memorize facts, terminate
5. **Single-image mode**: Only the latest screenshot is sent to the model to minimize context size
6. **Loop guard**: Scroll position is tracked; the model is warned when it oscillates up/down

## Troubleshooting

**Model not downloading?**
- Check your internet connection and that `model_repo`/`model_filename` in `config.json` are correct
- You can download manually from [bartowski/microsoft_Fara-7B-GGUF](https://huggingface.co/bartowski/microsoft_Fara-7B-GGUF)

**Model not responding?**
- Verify llama-server is running: `curl http://localhost:8080/v1/models`
- Use `--start-server` to launch it automatically

**CDP connection refused?**
- Make sure the browser was started with `--remote-debugging-port=9222`
- Only Chromium-based browsers (Chrome, Edge) support CDP

**Agent looping?**
- Reduce `max_rounds` in `config.json`
- Ensure `temperature` is `0.0`

**Browser not visible?**
- Add the `--headful` flag

## License

MIT License — Based on [Microsoft Fara-7B](https://www.microsoft.com/en-us/research/blog/fara-7b-an-efficient-agentic-model-for-computer-use/)
