#!/usr/bin/env python3
"""
Test script to verify the system produces comprehensive answers.
"""

import asyncio
from pocketflow import Flow, Params
from nodes import ChainOfThoughtNode
from search import QwantSearch

async def main():
    """
    Run a test to verify comprehensive answers.
    """
    # Create a Qwant search client
    search_client = QwantSearch()
    
    # Create the Chain of Thought node with search and scraping integration
    cot_node = ChainOfThoughtNode(search_client, max_scraped_urls=2)
    
    # Create a flow with the node
    flow = Flow(cot_node)
    
    # Set up a self-loop: continue -> cot_node
    flow.edge("continue", cot_node)
    
    # Define a problem that requires research
    problem = """
    Briefly explain the theory of relativity and its significance. 
    Include both special and general relativity. Reference sources used.
    """
    
    # Create parameters with the problem
    params = Params({"problem": problem})
    
    # Run the flow
    print("Starting comprehensive answer test...")
    try:
        result = await flow.run({}, params)
        print("\nTest completed successfully.")
        print(f"Final result: {result}")
    except Exception as e:
        print(f"\nTest failed with error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())