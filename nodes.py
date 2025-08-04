"""
nodes.py – Chain-of-Thought + advanced reasoning nodes.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

from pocketflow import Context, Node, Params, Flow
from utility import call_llm, format_plan


# ------------------------------------------------------------------
# Base CoT node
# ------------------------------------------------------------------
class ChainOfThoughtNode(Node):
    async def __call__(self, ctx: Context, p: Params) -> tuple[str, Any]:
        problem: str = ctx.setdefault("problem", p.data.get("problem", ""))
        thoughts: list[dict[str, Any]] = ctx.setdefault("thoughts", [])
        current_num: int = ctx.setdefault("current_thought_number", 0) + 1
        ctx["current_thought_number"] = current_num
        thoughts[:] = thoughts[-10:]  # keep last 10

        history_json = json_history(thoughts) if thoughts else "No previous thoughts."

        prompt = build_prompt(problem, history_json, current_num)
        llm_output = call_llm(prompt)

        thought_entry = {
            "thought_number": current_num,
            "current_thinking": llm_output["current_thinking"],
            "planning": llm_output["planning"],
            "next_thought_needed": llm_output["next_thought_needed"],
        }
        thoughts.append(thought_entry)

        print(f"\n🔍 Thought #{current_num} complete")
        print("📋 Updated plan:")
        print(format_plan(llm_output["planning"]))

        if not llm_output["next_thought_needed"]:
            ctx["solution"] = llm_output["current_thinking"]
            print("\n🎯 PLAN COMPLETE – final reasoning above.")
            return ("end", llm_output["current_thinking"])

        # LLM decides the next action
        return (llm_output.get("next_action", "continue"), None)


# ------------------------------------------------------------------
# 1. Parallel exploration
# ------------------------------------------------------------------
class ParallelExploreNode(Node):
    async def __call__(self, ctx: Context, p: Params) -> tuple[str, Any]:
        sub_problems: list[str] = p.data["sub_problems"]
        if not sub_problems:
            return ("continue", None)

        async def _worker(sub: str) -> Any:
            sub_ctx = ctx.copy()
            sub_params = Params({"problem": sub})
            node = ChainOfThoughtNode()
            while True:
                act, val = await node(sub_ctx, sub_params)
                if act == "end":
                    return val

        results = await asyncio.gather(*(_worker(s) for s in sub_problems))
        ctx.setdefault("candidates", []).extend(results)
        return ("continue", None)


# ------------------------------------------------------------------
# 2. Self-critique / revision loop
# ------------------------------------------------------------------
class CritiqueNode(Node):
    async def __call__(self, ctx: Context, p: Params) -> tuple[str, Any]:
        last_plan = ctx["thoughts"][-1]["planning"]
        prompt = f"""
You are a strict reviewer.  
Score the following plan 1-5 and give concise feedback.  
Return ONLY JSON: {{"score": int, "feedback": str}}

{format_plan(last_plan)}
"""
        resp = call_llm(prompt)
        score = int(resp.get("score", 3))
        if score < 4:
            ctx["revision_feedback"] = resp.get("feedback", "")
            return ("revise", None)
        return ("continue", None)


class ReviseNode(Node):
    async def __call__(self, ctx: Context, p: Params) -> tuple[str, Any]:
        feedback = ctx.pop("revision_feedback", "")
        ctx["problem"] += f"\nReviewer feedback: {feedback}"
        return ("continue", None)


# ------------------------------------------------------------------
# 3. Sub-agent spawning (mini-orchestrator)
# ------------------------------------------------------------------
class SpawnAgentNode(Node):
    async def __call__(self, ctx: Context, p: Params) -> tuple[str, Any]:
        sub_problem: str = p.data["sub_problem"]
        sub_ctx = ctx.copy()
        sub_params = Params({"problem": sub_problem})

        flow = Flow(ChainOfThoughtNode())
        answer = await flow.run(sub_ctx, sub_params)

        ctx.setdefault("sub_answers", []).append(answer)
        return ("continue", None)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def build_prompt(problem: str, history_json: str, thought_num: int) -> str:
    return f"""
You are an advanced reasoning engine.

Problem:
{problem}

Previous thoughts and plans:
{history_json}

Current thought number: {thought_num}

Instructions:
1. Evaluate the last step's result and impact.
2. Pick the next pending step and execute it.
3. Update the plan: mark steps as Done, Pending, or Verification Needed.
4. If a step fails, adjust the plan or insert corrective actions.
5. When the plan is entirely complete, set `next_thought_needed: false`.
6. Provide concise results for steps marked Done.
7. If an advanced capability will help—explore, critique, revise, or spawn—set `next_action` accordingly; otherwise leave "continue".

Return ONLY valid JSON matching this schema:
{{
  "current_thinking": "<detailed reasoning>",
  "planning": [
    {{
      "description": "<step text>",
      "status": "Pending|Done|Verification Needed",
      "result": "<concise outcome>",
      "mark": "<optional note>",
      "sub_steps": []
    }}
  ],
  "next_action": "continue|explore|critique|revise|spawn",
  "next_thought_needed": true|false
}}
"""


def json_history(thoughts: list[dict[str, Any]]) -> str:
    return json.dumps(
        [
            {
                "thought_number": t["thought_number"],
                "current_thinking": t["current_thinking"][:500],
                "planning": t["planning"],
            }
            for t in thoughts
        ],
        indent=2,
        ensure_ascii=True,
    )