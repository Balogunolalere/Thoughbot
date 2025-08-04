import asyncio, sys
from pocketflow import Context, Params
from nodes import ParallelExploreNode

async def demo():
    ctx = {}
    params = Params({
        "sub_problems": [
            "Solve a 10-city TSP exactly with Branch-and-Bound and report optimal tour length",
            "Solve a 10-city TSP with Genetic Algorithm and report best tour length",
            "Solve a 10-city TSP with Simulated Annealing and report best tour length"
        ]
    })
    await ParallelExploreNode()(ctx, params)
    print("Results from 3 parallel agents:", ctx["candidates"])

asyncio.run(demo())