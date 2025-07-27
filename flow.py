"""
flow.py – Stand-alone runner to test the Chain-of-Thought node.
"""
import asyncio

from pocketflow import Context, Params
from nodes import ChainOfThoughtNode

# ------------------------------------------------------------------
# Example usage
# ------------------------------------------------------------------
PROBLEM = """
Find the smallest positive integer n such that:
  - n is divisible by 3,
  - n + 1 is divisible by 5,
  - n + 2 is divisible by 7.
"""

async def main():
    ctx: Context = {}
    params = Params({"problem": PROBLEM})

    start = ChainOfThoughtNode()
    while True:
        action, value = await start(ctx, params)
        if action == "end":
            print("\n✅ Finished with solution:", value)
            break


if __name__ == "__main__":
    asyncio.run(main())