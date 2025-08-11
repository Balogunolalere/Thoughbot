#!/usr/bin/env python3
"""
Test script for the web scraper functionality.
"""

import asyncio
from scraper import WebScraper, scrape_url, scrape_urls

async def test_single_scraping():
    """Test scraping a single URL."""
    print("Testing single URL scraping...")
    
    url = "https://en.wikipedia.org/wiki/Milton_Friedman"
    print(f"Scraping: {url}")
    
    result = await scrape_url(url, timeout=15)
    
    if result['success']:
        print(f"Success! Title: {result['title']}")
        print(f"Content length: {len(result['content'])} characters")
        print(f"First 200 characters: {result['content'][:200]}...")
        print(f"Found {len(result['links'])} links")
        print(f"Found {len(result['images'])} images")
    else:
        print(f"Failed: {result['error']}")

async def test_multiple_scraping():
    """Test scraping multiple URLs."""
    print("\nTesting multiple URL scraping...")
    
    urls = [
        "https://en.wikipedia.org/wiki/Milton_Friedman",
        "https://en.wikipedia.org/wiki/John_Maynard_Keynes",
        "https://example.com"  # This should fail gracefully
    ]
    
    results = await scrape_urls(urls, timeout=15)
    
    for url, result in results.items():
        print(f"\nURL: {url}")
        if result['success']:
            print(f"  Success! Title: {result['title']}")
            print(f"  Content length: {len(result['content'])} characters")
            print(f"  Found {len(result['links'])} links")
        else:
            print(f"  Failed: {result['error']}")

async def test_scraper_class():
    """Test the WebScraper class directly."""
    print("\nTesting WebScraper class directly...")
    
    async with WebScraper(timeout=15) as scraper:
        url = "https://httpbin.org/html"
        print(f"Scraping: {url}")
        
        result = await scraper.scrape_url(url)
        
        if result['success']:
            print(f"Success! Title: {result['title']}")
            print(f"Content: {result['content'][:100]}...")
        else:
            print(f"Failed: {result['error']}")

async def main():
    """Run all tests."""
    await test_single_scraping()
    await test_multiple_scraping()
    await test_scraper_class()

if __name__ == "__main__":
    asyncio.run(main())