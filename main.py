#!/usr/bin/env python3
"""
main.py
Run a CoT agent that executes **only** shell commands to satisfy
a one-shot natural-language request.

Usage
-----
uv run main.py --"implement a json search algorithm that is optimal for any file size and write it to jsonalgo.py"
"""
from __future__ import annotations

import argparse
import asyncio
import sys

from pocketflow import Context, Params
from nodes import ChainOfThoughtNode


async def run_once(task: str) -> None:
    ctx: Context = {}
    params = Params({"problem": task})

    node = ChainOfThoughtNode()
    while True:
        action, value = await node(ctx, params)
        if action == "end":
            print("\n✅ Agent finished; final reasoning above.")
            break


def cli(argv: list[str] | None = None) -> str:
    parser = argparse.ArgumentParser(
        description="CoT agent driven by shell commands only."
    )
    parser.add_argument(
        "task",
        help='Natural-language task (enclose in quotes), e.g. "create a fast JSON search utility"',
    )
    args = parser.parse_args(argv)
    return args.task


async def main() -> None:
    task = cli()
    await run_once(task)


if __name__ == "__main__":
    asyncio.run(main())