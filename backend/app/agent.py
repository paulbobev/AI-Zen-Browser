"""
Zenith — browser-use agent configuration for Zen Browser.

Connects to the local Zen Browser installation via Playwright's Firefox
channel support and exposes an async helper used by the LangGraph nodes.
"""

from __future__ import annotations

import logging
import os
import platform
from pathlib import Path

from browser_use import Agent, Browser, BrowserProfile
from langchain_ollama import ChatOllama

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Zen Browser binary discovery
# ---------------------------------------------------------------------------

def _find_zen_binary() -> str:
    """Return the path to the Zen Browser executable.

    Checks (in order):
      1. ZEN_BROWSER_PATH environment variable.
      2. Platform-specific default install locations.
    """
    env_path = os.getenv("ZEN_BROWSER_PATH")
    if env_path and Path(env_path).exists():
        return env_path

    system = platform.system()
    candidates: list[Path] = []

    if system == "Windows":
        candidates = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Zen Browser" / "zen.exe",
            Path(os.environ.get("PROGRAMFILES", "")) / "Zen Browser" / "zen.exe",
        ]
    elif system == "Darwin":
        candidates = [
            Path("/Applications/Zen Browser.app/Contents/MacOS/zen"),
            Path.home() / "Applications" / "Zen Browser.app" / "Contents" / "MacOS" / "zen",
        ]
    else:  # Linux
        candidates = [
            Path("/usr/bin/zen"),
            Path("/usr/local/bin/zen"),
            Path.home() / ".local" / "bin" / "zen",
            Path("/opt/zen-browser/zen"),
        ]

    for p in candidates:
        if p.exists():
            return str(p)

    # Fallback — let Playwright try to resolve "firefox" and hope Zen is the default
    logger.warning(
        "Zen Browser binary not found. Set ZEN_BROWSER_PATH or install Zen. "
        "Falling back to system Firefox."
    )
    return "firefox"


# ---------------------------------------------------------------------------
# Ollama LLM for browser-use
# ---------------------------------------------------------------------------

def _get_browser_llm() -> ChatOllama:
    """LLM instance used by browser-use for page interaction decisions.

    Optimised for RTX 5070 (12 GB VRAM):
      - gemma3 (default) or llama3.2:11b via OLLAMA_MODEL env var.
      - All layers offloaded to GPU.
    """
    model = os.getenv("OLLAMA_MODEL", "gemma3")
    return ChatOllama(
        model=model,
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0.1,
        num_gpu=99,
    )


# ---------------------------------------------------------------------------
# Browser + Agent factory
# ---------------------------------------------------------------------------

_browser_instance: Browser | None = None


async def get_browser() -> Browser:
    """Lazy-initialise and return the shared Browser instance."""
    global _browser_instance
    if _browser_instance is None:
        zen_path = _find_zen_binary()
        logger.info("Launching Zen Browser from: %s", zen_path)

        profile = BrowserProfile(
            headless=False,
            executable_path=zen_path if zen_path != "firefox" else None,
            args=[
                "--new-instance",
                "--no-remote",
            ],
        )
        _browser_instance = Browser(browser_profile=profile)
    return _browser_instance


async def execute_browser_task(task_description: str) -> str:
    """Execute a single browsing sub-task and return a textual result.

    This is the main entry-point called from the LangGraph BrowserAction node.
    """
    browser = await get_browser()
    llm = _get_browser_llm()

    agent = Agent(
        task=task_description,
        llm=llm,
        browser=browser,
        max_actions_per_step=5,
    )

    result = await agent.run()

    # browser-use returns an AgentHistoryList; extract the final answer
    final = result.final_result()
    if final:
        return str(final)

    # Fallback: concatenate extracted content from the last few actions
    history_texts = [
        h.extracted_content
        for h in result.history
        if h.extracted_content
    ]
    return "\n".join(history_texts[-3:]) if history_texts else "[no content extracted]"


async def shutdown_browser() -> None:
    """Gracefully close the browser (called on app shutdown)."""
    global _browser_instance
    if _browser_instance is not None:
        await _browser_instance.close()
        _browser_instance = None
