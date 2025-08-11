import asyncio
from pocketflow import Flow, Params
from nodes import ChainOfThoughtNode
from search import QwantSearch

async def main():
    """
    Run the Chain of Thought flow with a sample problem.
    """
    # Create a Qwant search client
    search_client = QwantSearch()
    
    # Create the Chain of Thought node with search integration
    cot_node = ChainOfThoughtNode(search_client)
    
    # Create a flow with the node
    flow = Flow(cot_node)
    
    # Set up a self-loop: continue -> cot_node
    flow.edge("continue", cot_node)
    
    # Define a problem to solve
    problem = """
    A line in the plane is called sunny if it is not parallel to any of the x-axis, the y-axis,
    and the line x + y = 0.
    Let n ⩾ 3 be a given integer. Determine all nonnegative integers k such that there
    exist n distinct lines in the plane satisfying both of the following:
    • for all positive integers a and b with a + b ⩽ n + 1, the point (a, b) is on at
    least one of the lines; and
    • exactly k of the n lines are sunny.
    """
    
    # Create parameters with the problem
    params = Params({"problem": problem})
    
    # Run the flow
    print("Starting Chain of Thought reasoning...")
    result = await flow.run({}, params)
    
    print("\nFlow completed.")
    print(f"Final result: {result}")

if __name__ == "__main__":
    asyncio.run(main())