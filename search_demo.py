import asyncio
from pocketflow import Flow, Params
from nodes import ChainOfThoughtNode
from search import QwantSearch

async def main():
    """
    Run the Chain of Thought flow with a sample problem that requires search and scraping.
    """
    # Create a Qwant search client
    search_client = QwantSearch()
    
    # Create the Chain of Thought node with search and scraping integration
    cot_node = ChainOfThoughtNode(search_client, max_scraped_urls=10)
    
    # Create a flow with the node
    flow = Flow(cot_node)
    
    # Set up a self-loop: continue -> cot_node
    flow.edge("continue", cot_node)
    
    # Define a problem that would benefit from search and scraping
    problem = """
    what comics from dc are coming out august 2025
    """
    
    # Create parameters with the problem
    params = Params({"problem": problem})
    
    # Run the flow
    print("Starting Chain of Thought reasoning with search and scraping capabilities...")
    result = await flow.run({}, params)
    
    print("\nFlow completed.")
    print(f"Final result: {result}")

if __name__ == "__main__":
    asyncio.run(main())