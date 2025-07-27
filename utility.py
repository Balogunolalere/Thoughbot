"""
utility.py – LLM helper that streams responses,
tolerates YAML errors, and retries on parse failure.
"""
from __future__ import annotations

import os
import sys
import re
import yaml
from typing import Any, Dict

from google import genai
from google.genai import types

_CLIENT = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
_MODEL = "gemini-2.5-flash"


def _repair_yaml(text: str) -> str:
    """
    Quick-and-dirty repair:
    - strip code fences
    - coerce to block-style literal scalar for current_thinking
    """
    text = text.strip().removeprefix("```yaml").removesuffix("```").strip()
    # If current_thinking is double-quoted and contains backslashes, re-wrap it
    pattern = r'^current_thinking:\s*"(.*)"'
    if re.search(pattern, text, flags=re.MULTILINE | re.DOTALL):
        text = re.sub(
            pattern,
            lambda m: 'current_thinking: |\n' + _indent(m.group(1)),
            text,
            flags=re.MULTILINE | re.DOTALL,
        )
    return text


def _indent(s: str) -> str:
    """Indent every line four spaces."""
    return "\n".join("    " + line for line in s.splitlines())


def call_llm(prompt: str) -> Dict[str, Any]:
    """Stream Gemini and return a valid YAML dict, retrying if necessary."""
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    ]
    cfg = types.GenerateContentConfig(
        thinking_config={"thinking_budget": -1},
        response_mime_type="text/plain",
    )

    for attempt in range(1, 4):  # up to 3 attempts
        buffer = ""
        print("\n🤖", end="")
        for chunk in _CLIENT.models.generate_content_stream(
            model=_MODEL, contents=contents, config=cfg
        ):
            text = chunk.text or ""
            buffer += text
            print(text, end="")
            sys.stdout.flush()

        print()  # newline after streaming

        try:
            buffer = _repair_yaml(buffer)
            parsed = yaml.safe_load(buffer)
            # Basic schema check
            for key in ("current_thinking", "planning", "next_thought_needed"):
                if key not in parsed:
                    raise KeyError(key)
            return parsed
        except Exception as e:
            print(f"\n⚠️  YAML parse attempt #{attempt} failed: {e}")
            if attempt == 3:
                raise RuntimeError("Unable to obtain valid YAML after 3 tries") from e


# ------------------------------------------------------------------
# Pretty-printers
# ------------------------------------------------------------------
def format_plan(plan: list[dict[str, Any]], indent: int = 0) -> str:
    """Recursively pretty-prints the plan (list of step dicts)."""
    lines = []
    prefix = "  " * indent
    for step in plan:
        lines.append(
            f"{prefix}- [{step['status']}] {step['description']}"
            + (f" → {step['result']}" if step.get("result") else "")
            + (f" ⚠ {step['mark']}" if step.get("mark") else "")
        )
        if step.get("sub_steps"):
            lines.append(format_plan(step["sub_steps"], indent + 1))
    return "\n".join(lines)