"""Run the Fara agent backed by llama.cpp llama-server"""
import asyncio
import argparse
import json
import logging
import os
import subprocess
import time
import urllib.request
import urllib.error
from pathlib import Path

from agent import FaraAgent


logging.basicConfig(
    level=logging.INFO,
    format='[%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def _download_if_missing(repo: str, filename: str, dest: Path) -> None:
    """Download a single file from HuggingFace if it doesn't exist locally."""
    if dest.exists():
        return
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        raise SystemExit("huggingface-hub is required for model download. Run: uv sync")
    logger.info(f"{dest.name} not found — downloading from {repo} ...")
    dest.parent.mkdir(parents=True, exist_ok=True)
    downloaded = hf_hub_download(repo_id=repo, filename=filename, local_dir=str(dest.parent))
    logger.info(f"Saved to {downloaded}")


def ensure_model(config: dict) -> None:
    """Download the model GGUF and mmproj file if they don't exist yet."""
    repo = config.get("model_repo", "")
    _download_if_missing(repo, config["model_filename"], Path(config["model_path"]))
    if config.get("mmproj_filename") and config.get("mmproj_path"):
        _download_if_missing(repo, config["mmproj_filename"], Path(config["mmproj_path"]))


def start_edge(config: dict) -> None:
    """Launch Edge with CDP by delegating to start_edge.ps1."""
    script = Path(__file__).parent / "start_edge.ps1"
    edge_cfg = config.get("edge", {})
    port = edge_cfg.get("port", 9222)
    profile = edge_cfg.get("profile", "Profile 2")
    user_data_dir = edge_cfg.get("user_data_dir", r"C:\Users\berna\AppData\Local\Microsoft\Edge\User Data")
    exe = edge_cfg.get("exe", r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")

    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script), "-Port", str(port)]
    if profile:
        cmd += ["-Profile", profile]
    if user_data_dir:
        cmd += ["-UserDataDir", user_data_dir]
    if exe:
        cmd += ["-EdgeExe", exe]
    logger.info(f"Starting Edge via {script.name} ...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"start_edge.ps1 failed:\n{result.stdout}\n{result.stderr}")
    logger.info(result.stdout.strip().splitlines()[-1])  # last line = "Edge ready: ..."


def start_llama_server(config: dict) -> subprocess.Popen:
    """Launch llama-server as a background process using config settings."""
    exe = config.get("llama_cpp_path", "F:/llama.cpp/llama-server.exe")
    model = config.get("model_path", "")
    args_cfg = config.get("llama_cpp_args", {})

    cmd = [
        exe,
        "-m", model,
        "-ngl", str(args_cfg.get("ngl", 99)),
        "-c", str(args_cfg.get("ctx_size", 16384)),
        "--host", str(args_cfg.get("host", "0.0.0.0")),
        "--port", str(args_cfg.get("port", 8080)),
    ]
    mmproj = config.get("mmproj_path", "")
    if mmproj:
        cmd += ["--mmproj", mmproj]
    logger.info(f"Starting llama-server: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    port = args_cfg.get("port", 8080)
    health_url = f"http://localhost:{port}/health"
    deadline = time.time() + 120  # wait up to 2 minutes for model to load
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=2) as r:
                if r.status == 200:
                    logger.info("llama-server is ready")
                    return proc
        except Exception:
            pass
        time.sleep(2)

    raise TimeoutError("llama-server did not become ready within 2 minutes")
    return proc


async def main():
    parser = argparse.ArgumentParser(description="Run Fara agent with llama.cpp")
    parser.add_argument("--task", type=str, required=True, help="Task for the agent to perform")
    parser.add_argument("--headful", action="store_true", help="Show browser GUI")
    parser.add_argument("--config", type=str, default="config.json", help="Path to config file")
    parser.add_argument(
        "--start-server",
        action="store_true",
        help="Launch llama-server before running (uses llama_cpp_path/model_path from config)",
    )
    parser.add_argument(
        "--cdp-url",
        type=str,
        default=None,
        help="Attach to a running Chrome/Edge (e.g. http://localhost:9222). Overrides cdp_url in config.json.",
    )
    parser.add_argument(
        "--start-edge",
        action="store_true",
        help="Launch Edge with CDP via start_edge.ps1 before running (sets --cdp-url automatically).",
    )

    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    if args.start_edge:
        start_edge(config)
        port = config.get("edge", {}).get("port", 9222)
        config["cdp_url"] = f"http://localhost:{port}"
    elif args.cdp_url:
        config["cdp_url"] = args.cdp_url

    ensure_model(config)

    server_proc = None
    if args.start_server:
        server_proc = start_llama_server(config)

    agent = FaraAgent(config=config, headless=not args.headful, logger=logger)

    try:
        await agent.start()
        await agent.run(args.task)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
    finally:
        await agent.close()
        if server_proc:
            logger.info("Stopping llama-server")
            server_proc.terminate()


if __name__ == "__main__":
    asyncio.run(main())
