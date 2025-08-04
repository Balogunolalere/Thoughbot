#!/usr/bin/env python3
"""
main.py – Orchestrator that keeps looping and exposes
ParallelExplore, Critique, Revise, SpawnAgent nodes.
"""
from __future__ import annotations

import argparse
import asyncio

from pocketflow import Context, Params
from nodes import (
    ChainOfThoughtNode,
    ParallelExploreNode,
    CritiqueNode,
    ReviseNode,
    SpawnAgentNode,
)


async def run_once(task: str) -> None:
    """
    Loop on the same ChainOfThoughtNode instance and branch into any
    of the four utility nodes when the agent requests it.
    """
    ctx: Context = {}
    params = Params({"problem": task})

    # One shared CoT instance so state persists across loop iterations
    cot = ChainOfThoughtNode()

    while True:
        action, value = await cot(ctx, params)

        # Agent signalled completion
        if action == "end":
            print("\n✅ Agent finished; final reasoning above.")
            break

        # Branch to advanced nodes if explicitly requested
        if action == "explore":
            _, _ = await ParallelExploreNode()(ctx, params)
        elif action == "critique":
            _, _ = await CritiqueNode()(ctx, params)
        elif action == "revise":
            _, _ = await ReviseNode()(ctx, params)
        elif action == "spawn":
            _, _ = await SpawnAgentNode()(ctx, params)

        # Any other action (including "continue") just loops back to CoT


def cli(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(
        description="CoT agent with parallel, critique, and sub-agent features."
    )
    parser.add_argument(
        "task",
        help='Natural-language task (enclose in quotes), e.g. "explore three ways to …"',
    )
    args = parser.parse_args(argv)
    return args.task


async def main() -> None:
    task = cli()
    await run_once(task)


if __name__ == "__main__":
    asyncio.run(main())