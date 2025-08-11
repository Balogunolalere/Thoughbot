#!/usr/bin/env python3
"""
Test script for the Qwant search integration.
"""

from search import QwantSearch

def test_qwant_search():
    """Test the Qwant search functionality."""
    print("Testing Qwant search integration...")
    
    # Initialize the search client
    search_client = QwantSearch()
    
    try:
        # Perform a simple search
        query = "Milton Friedman economic theories"
        print(f"\nSearching for: {query}")
        
        response = search_client.search(query)
        
        # Parse the results
        results = search_client.parse_web_results(response)
        
        print(f"\nFound {len(results)} results:")
        for i, result in enumerate(results[:5], 1):  # Show first 5 results
            print(f"\n{i}. {result['title']}")
            print(f"   URL: {result['url']}")
            print(f"   Description: {result['description'][:100]}...")
        
        # Get related searches
        related = search_client.get_related_searches(response)
        if related:
            print(f"\nRelated searches:")
            for i, search in enumerate(related[:5], 1):
                print(f"   {i}. {search}")
                
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_qwant_search()