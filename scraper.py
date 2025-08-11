import re
import time
from typing import Dict, Any, List, Optional, Tuple
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import asyncio
from functools import partial

class WebScraper:
    """A robust web scraper with error handling and content extraction."""
    
    def __init__(self, timeout: int = 10, max_retries: int = 3, delay: float = 1.0):
        """
        Initialize the web scraper.
        
        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            delay: Delay between retries in seconds
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.delay = delay
        self.client = httpx.AsyncClient(
            timeout=timeout,
            headers={
                'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )
    
    async def scrape_url(self, url: str) -> Dict[str, Any]:
        """
        Scrape content from a URL with comprehensive error handling.
        
        Args:
            url: The URL to scrape
            
        Returns:
            Dictionary containing scraped content and metadata
        """
        # Validate URL
        if not self._is_valid_url(url):
            return {
                'url': url,
                'success': False,
                'error': 'Invalid URL format',
                'title': '',
                'content': '',
                'links': []
            }
        
        # Try to fetch the page with retries
        for attempt in range(self.max_retries):
            try:
                response = await self.client.get(url)
                response.raise_for_status()
                
                # Parse the content
                content = await self._parse_content(response, url)
                content['success'] = True
                content['error'] = None
                return content
                
            except httpx.TimeoutException:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.delay * (2 ** attempt))  # Exponential backoff
                    continue
                return {
                    'url': url,
                    'success': False,
                    'error': 'Timeout error',
                    'title': '',
                    'content': '',
                    'links': []
                }
                
            except httpx.RequestError as e:
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.delay * (2 ** attempt))  # Exponential backoff
                    continue
                return {
                    'url': url,
                    'success': False,
                    'error': f'Request error: {str(e)}',
                    'title': '',
                    'content': '',
                    'links': []
                }
                
            except Exception as e:
                return {
                    'url': url,
                    'success': False,
                    'error': f'Unexpected error: {str(e)}',
                    'title': '',
                    'content': '',
                    'links': []
                }
        
        # If we get here, all retries failed
        return {
            'url': url,
            'success': False,
            'error': 'Max retries exceeded',
            'title': '',
            'content': '',
            'links': []
        }
    
    async def scrape_multiple_urls(self, urls: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Scrape multiple URLs concurrently.
        
        Args:
            urls: List of URLs to scrape
            
        Returns:
            Dictionary mapping URLs to their scraped content
        """
        # Remove duplicates while preserving order
        unique_urls = list(dict.fromkeys(urls))
        
        # Scrape all URLs concurrently
        tasks = [self.scrape_url(url) for url in unique_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        scraped_data = {}
        for i, result in enumerate(results):
            url = unique_urls[i]
            if isinstance(result, Exception):
                scraped_data[url] = {
                    'url': url,
                    'success': False,
                    'error': f'Exception during scraping: {str(result)}',
                    'title': '',
                    'content': '',
                    'links': []
                }
            else:
                scraped_data[url] = result
                
        return scraped_data
    
    async def _parse_content(self, response: httpx.Response, url: str) -> Dict[str, Any]:
        """
        Parse HTML content and extract relevant information.
        
        Args:
            response: HTTP response object
            url: The URL of the page
            
        Returns:
            Dictionary containing parsed content
        """
        try:
            # Handle different content types
            content_type = response.headers.get('content-type', '').lower()
            
            # If it's not HTML, return minimal information
            if 'text/html' not in content_type:
                return {
                    'url': url,
                    'title': url,
                    'content': f'Non-HTML content (Content-Type: {content_type})',
                    'links': [],
                    'images': []
                }
            
            # Parse HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title = self._extract_title(soup)
            
            # Extract main content
            content = self._extract_main_content(soup)
            
            # Extract links
            links = self._extract_links(soup, url)
            
            # Extract images
            images = self._extract_images(soup, url)
            
            return {
                'url': url,
                'title': title,
                'content': content,
                'links': links,
                'images': images
            }
            
        except Exception as e:
            return {
                'url': url,
                'title': url,
                'content': f'Error parsing content: {str(e)}',
                'links': [],
                'images': []
            }
    
    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        try:
            title_tag = soup.find('title')
            if title_tag:
                return title_tag.get_text().strip()
            
            # Try other title-like elements
            h1_tag = soup.find('h1')
            if h1_tag:
                return h1_tag.get_text().strip()
                
            return 'No title found'
        except Exception:
            return 'Error extracting title'
    
    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """
        Extract main content from HTML, trying multiple strategies.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Extracted text content
        """
        try:
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer", "header", "aside"]):
                script.decompose()
            
            # Try to find main content areas
            content_selectors = [
                'main',
                'article',
                '[role="main"]',
                '.content',
                '.main-content',
                '#content',
                '.post-content',
                '.entry-content',
                'body'
            ]
            
            content_element = None
            for selector in content_selectors:
                content_element = soup.select_one(selector)
                if content_element and len(content_element.get_text().strip()) > 100:
                    break
            
            if not content_element:
                content_element = soup
            
            # Extract text and clean it
            text = content_element.get_text()
            
            # Clean up the text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Limit content length to prevent overwhelming the LLM
            if len(text) > 5000:
                text = text[:5000] + '... [content truncated]'
                
            return text
            
        except Exception as e:
            return f'Error extracting content: {str(e)}'
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract links from the page."""
        try:
            links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                absolute_url = urljoin(base_url, href)
                text = link.get_text().strip()
                
                # Skip empty links and anchors
                if not text or href.startswith('#') or href.startswith('mailto:'):
                    continue
                    
                # Skip very long URLs (likely tracking links)
                if len(absolute_url) > 500:
                    continue
                    
                links.append({
                    'url': absolute_url,
                    'text': text[:100]  # Limit text length
                })
                
                # Limit number of links
                if len(links) >= 50:
                    break
                    
            return links
        except Exception:
            return []
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[Dict[str, str]]:
        """Extract images from the page."""
        try:
            images = []
            for img in soup.find_all('img', src=True):
                src = img['src']
                absolute_url = urljoin(base_url, src)
                alt = img.get('alt', '').strip()
                
                images.append({
                    'url': absolute_url,
                    'alt': alt[:100]  # Limit alt text length
                })
                
                # Limit number of images
                if len(images) >= 20:
                    break
                    
            return images
        except Exception:
            return []
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if a URL is valid."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
        except Exception:
            return False
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

# Convenience function for simple scraping
async def scrape_url(url: str, timeout: int = 10, max_retries: int = 3) -> Dict[str, Any]:
    """
    Convenience function to scrape a single URL.
    
    Args:
        url: URL to scrape
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dictionary containing scraped content
    """
    async with WebScraper(timeout=timeout, max_retries=max_retries) as scraper:
        return await scraper.scrape_url(url)

# Convenience function for scraping multiple URLs
async def scrape_urls(urls: List[str], timeout: int = 10, max_retries: int = 3) -> Dict[str, Dict[str, Any]]:
    """
    Convenience function to scrape multiple URLs.
    
    Args:
        urls: List of URLs to scrape
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        
    Returns:
        Dictionary mapping URLs to their scraped content
    """
    async with WebScraper(timeout=timeout, max_retries=max_retries) as scraper:
        return await scraper.scrape_multiple_urls(urls)