"""Loads prompt templates from the prompts/ directory at the project root."""

from functools import lru_cache
from pathlib import Path

# Project root is 3 levels up from this file: src/retrieval/chatbot/prompt_loader.py
_PROMPTS_ROOT = Path(__file__).parents[3] / "prompts"


@lru_cache(maxsize=None)
def load_prompt(relative_path: str) -> str:
    """
    Read and cache a prompt file.

    relative_path is relative to the project-root prompts/ directory,
    e.g. "chatbot/classifier/system.txt".

    Raises FileNotFoundError with a clear message if the file is missing.
    """
    full_path = _PROMPTS_ROOT / relative_path
    if not full_path.exists():
        raise FileNotFoundError(
            f"Prompt file not found: {full_path}\n"
            f"Expected under prompts/{relative_path}"
        )
    return full_path.read_text(encoding="utf-8").strip()
