"""
utility.py – LLM helper that streams plain JSON from Gemini,
cleans it, validates with Pydantic, and retries on failure.
"""
from __future__ import annotations

import json
import re
import os
import sys
from typing import Any, Dict

from google import genai
from google.genai import types
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError, ConfigDict

load_dotenv()

_CLIENT = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
_MODEL = "gemini-2.5-flash"

# ---------- Pydantic models ----------
class PlanStep(BaseModel):
    model_config = ConfigDict(extra="ignore")

    description: str
    status: str
    result: str | None = None
    mark: str | None = None
    sub_steps: list["PlanStep"] = Field(default_factory=list)


class LLMResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    current_thinking: str
    planning: list[PlanStep]
    next_thought_needed: bool


# ---------- helpers ----------
def _clean_json(raw: str) -> str:
    raw = raw.strip().removeprefix("```json").removesuffix("```").strip()
    raw = re.sub(r"\\n|\\t|\\r", " ", raw)
    raw = re.sub(r",(\s*[}\]])", r"\1", raw)
    raw = re.sub(r"[\x00-\x1f\ufeff]", "", raw)

    def _fix_escapes(m: re.Match[str]) -> str:
        s = m.group(0)
        if s in {"\\\"", "\\\\", "\\/", "\\b", "\\f", "\\n", "\\r", "\\t"}:
            return s
        if re.fullmatch(r"\\u[0-9a-fA-F]{4}", s):
            return s
        return "\\\\" + s[1:]

    raw = re.sub(r"\\.", _fix_escapes, raw)
    raw = raw.encode("utf-8", "ignore").decode("utf-8")

    # Brute-force balance braces/brackets if truncated
    open_braces  = raw.count("{")
    close_braces = raw.count("}")
    open_brackets = raw.count("[")
    close_brackets = raw.count("]")
    raw += "}"  * (open_braces  - close_braces)
    raw += "]" * (open_brackets - close_brackets)
    return raw


def call_llm(prompt: str) -> Dict[str, Any]:
    contents = [
        types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    ]
    cfg = types.GenerateContentConfig(
        thinking_config={"thinking_budget": -1},
        response_mime_type="application/json",
    )

    for attempt in range(1, 4):
        buffer = ""
        print("\n🤖", end="")
        try:
            for chunk in _CLIENT.models.generate_content_stream(
                model=_MODEL, contents=contents, config=cfg
            ):
                buffer += chunk.text or ""
                print(chunk.text or "", end="")
                sys.stdout.flush()

            print()
            cleaned = _clean_json(buffer)
            parsed = LLMResponse.model_validate_json(cleaned)
            return parsed.model_dump()
        except Exception as e:
            print(f"\n⚠️  Attempt #{attempt} failed: {e}")
            if attempt == 3:
                raise RuntimeError("Unable to obtain valid JSON after 3 tries") from e


def format_plan(plan: list[dict[str, Any]], indent: int = 0) -> str:
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