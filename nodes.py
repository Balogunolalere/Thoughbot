"""
nodes.py – Chain-of-Thought self-looping node.
Now tolerates YAML errors and retries internally.
"""
from __future__ import annotations

import yaml
from typing import Any

from pocketflow import Context, Node, Params
from utility import call_llm, format_plan


class ChainOfThoughtNode(Node):
    async def __call__(self, ctx: Context, p: Params) -> tuple[str, Any]:
        # --------------- PREP ---------------
        problem: str = ctx.setdefault("problem", p.data.get("problem", ""))
        thoughts: list[dict[str, Any]] = ctx.setdefault("thoughts", [])
        current_num: int = ctx.setdefault("current_thought_number", 0) + 1
        ctx["current_thought_number"] = current_num

        history_yaml = yaml_history(thoughts) if thoughts else "No previous thoughts."

        # --------------- EXEC (LLM call) ---------------
        prompt = build_prompt(problem, history_yaml, current_num)
        llm_output = call_llm(prompt)

        thought_entry = {
            "thought_number": current_num,
            "current_thinking": llm_output["current_thinking"],
            "planning": llm_output["planning"],
            "next_thought_needed": llm_output["next_thought_needed"],
        }

        # --------------- POST --------------
        thoughts.append(thought_entry)

        print(f"\n🔍 Thought #{current_num} complete")
        print("📋 Updated plan:")
        print(format_plan(llm_output["planning"]))

        if not llm_output["next_thought_needed"]:
            ctx["solution"] = llm_output["current_thinking"]
            print("\n🎯 PLAN COMPLETE – final reasoning above.")
            return ("end", llm_output["current_thinking"])

        return ("continue", None)


# ------------------------------------------------------------------
# Prompt helper
# ------------------------------------------------------------------
def build_prompt(problem: str, history_yaml: str, thought_num: int) -> str:
    return f"""
You are an advanced reasoning engine.  Solve the following problem step-by-step.

Problem:
{problem}

Previous thoughts and plans:
{history_yaml}

Current thought number: {thought_num}

Instructions:
1. Evaluate the last step's result and its impact on the overall plan.
2. Pick the next pending step (or sub-step) and execute it.
3. Update the plan: mark steps as Done, Pending, or Verification Needed; add sub-steps when useful.
4. If a step fails or produces an unexpected result, adjust the plan or insert corrective actions.
5. When the plan is entirely complete and verified, set `next_thought_needed: false`.
6. Provide concise results for steps marked Done.

Return ONLY valid YAML **using block-style literal scalars** (|) for `current_thinking`.
Required top-level keys:
current_thinking: |
  <detailed reasoning and evaluation>
planning:
  - description: <step text>
    status: Pending|Done|Verification Needed
    result: <concise outcome>  # only if Done
    mark: <optional note>      # only if Verification Needed
    sub_steps: []              # optional nested list
next_thought_needed: true|false
"""


# ------------------------------------------------------------------
# History formatter
# ------------------------------------------------------------------
def yaml_history(thoughts: list[dict[str, Any]]) -> str:
    return yaml.dump(
        [
            {
                "thought_number": t["thought_number"],
                "current_thinking": t["current_thinking"],
                "planning": t["planning"],
            }
            for t in thoughts
        ],
        default_flow_style=False,
    )