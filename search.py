import requests
import json
from typing import Dict, List, Optional, Any
import re

class QwantSearch:
    """A reusable client for the Qwant search API."""
    
    BASE_URL = "https://api.qwant.com/v3/search/web"
    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.qwant.com/',
        'Origin': 'https://www.qwant.com',
        'Connection': 'keep-alive',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'DNT': '1',
        'Cache-Control': 'no-cache',
    }
    
    def __init__(self, cookies: Optional[Dict[str, str]] = None):
        """
        Initialize the QwantSearch client.
        
        Args:
            cookies: Dictionary of cookies (didomi_token, euconsent-v2, datadome)
        """
        self.cookies = cookies or {
            'didomi_token': 'eyJ1c2VyX2lkIjoiMTkyNzY2ZTItMTUwYS02ZjVlLThkMzMtMjcxMDA4MzZlNGRiIiwiY3JlYXRlZCI6IjIwMjQtMTAtMTBUMTI6MzY6MjEuOTY4WiIsInVwZGF0ZWQiOiIyMDI0LTEwLTEwVDEyOjM2OjQ0LjY4NloiLCJ2ZW5kb3JzIjp7ImRpc2FibGVkIjpbImM6cXdhbnQtM01LS0paZHkiLCJjOnBpd2l3a3Byby1lQXJaREhXRCIsImM6bXNjbGFyaXR5LU1NcnBSSnJwIl19LCJ2ZW5kb3JzX2xpIjp7ImRpc2FibGVkIjpbImM6cXdhbnQtM01LS0paZHkiLCJjOnBpd2l3a3Byby1lQXJaREhXRCJdfSwidmVyc2lvbiI6Mn0',
            'euconsent-v2': 'CQGRvoAQGRvoAAHABBENBKFgAAAAAAAAAAqIAAAAAAAA.YAAAAAAAAAAA',
            'datadome': 'NXcXWUqx3NE9WDEu_2prgZN3wIOFUFlnDWr~_bW_MsbnRWBaZDlf~d0sxqXxnTM9_lJ79GKda_pxXuPpmepKLBagMNQKjCTQLcBA6AX9vjSojH_wefDpAnLtCZaS2MRh',
        }
    
    def search(
        self, 
        query: str, 
        count: int = 10, 
        offset: int = 0,
        locale: str = "en_gb",
        device: str = "desktop",
        safesearch: int = 1,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform a search on Qwant.
        
        Args:
            query: Search query
            count: Number of results to return (must be 10)
            offset: Result offset (must be multiple of 10, 0-40)
            locale: Language/locale code (e.g., "en_gb")
            device: Device type ("desktop", "smartphone", "tablet")
            safesearch: Safe search level (0, 1, or 2)
            **kwargs: Additional parameters
            
        Returns:
            Dictionary containing the API response
            
        Raises:
            ValueError: If parameters don't meet API requirements
            requests.exceptions.RequestException: If the request fails
        """
        # Validate parameters according to API requirements
        if count != 10:
            raise ValueError("count must be equal to 10")
        if offset % 10 != 0:
            raise ValueError("offset must be a factor of 10")
        if offset < 0 or offset > 40:
            raise ValueError("offset must be between 0 and 40")
        if device not in ["smartphone", "tablet", "desktop"]:
            raise ValueError("device must be one of: smartphone, tablet, desktop")
        
        # Prepare parameters
        params = {
            'q': query,
            'count': str(count),
            'locale': locale.lower(),  # Must be lowercase
            'offset': str(offset),
            'device': device,
            'tgp': '4',
            'safesearch': str(safesearch),
            'displayed': 'true',
            'llm': 'true',
            **kwargs
        }
        
        try:
            response = requests.get(
                self.BASE_URL,
                params=params,
                cookies=self.cookies,
                headers=self.DEFAULT_HEADERS,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Qwant API request failed: {str(e)}") from e
    
    def parse_web_results(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse the web search results from the API response.
        
        Args:
            response_data: The JSON response from the search API
            
        Returns:
            List of parsed search results
        """
        if response_data.get('status') != 'success':
            error_msg = response_data.get('data', {}).get('message', 'Unknown error')
            raise ValueError(f"API error: {error_msg}")
        
        results = []
        if 'mainline' in response_data['data']['result']['items']:
            for item in response_data['data']['result']['items']['mainline']:
                if item['type'] == 'web':
                    for result in item['items']:
                        results.append({
                            'title': result.get('title', ''),
                            'url': result.get('url', ''),
                            'domain': result.get('source', '').replace('https://', '').replace('http://', '').split('/')[0],
                            'description': result.get('desc', ''),
                            'favicon': result.get('favicon', ''),
                            'thumbnail': result.get('thumbnailUrl', '')
                        })
        return results
    
    def get_related_searches(self, response_data: Dict[str, Any]) -> List[str]:
        """
        Extract related searches from the API response.
        
        Args:
            response_data: The JSON response from the search API
            
        Returns:
            List of related search queries
        """
        if response_data.get('status') != 'success':
            return []
        
        related = []
        if 'mainline' in response_data['data']['result']['items']:
            for item in response_data['data']['result']['items']['mainline']:
                if item['type'] == 'related_searches':
                    for result in item['items']:
                        related.append(result.get('query', ''))
        
        # Also check sidebar related searches
        if 'sidebar' in response_data['data']['result']['items']:
            for item in response_data['data']['result']['items']['sidebar']:
                if item.get('type') == 'related_searches':
                    for result in item['items']:
                        related.append(result.get('query', ''))
                        
        return list(set(related))  # Remove duplicates
    
    def get_knowledge_panel(self, response_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract knowledge panel data if available.
        
        Args:
            response_data: The JSON response from the search API
            
        Returns:
            Dictionary with knowledge panel data
        """
        if response_data.get('status') != 'success':
            return {}
        
        if 'sidebar' in response_data['data']['result']['items']:
            for item in response_data['data']['result']['items']['sidebar']:
                if item.get('type') == 'ia/knowledge':
                    # In a real implementation, you'd need to fetch this endpoint
                    # For now, we'll just return the endpoint URL
                    return {
                        'endpoint': item.get('endpoint', ''),
                        'async': item.get('async', False)
                    }
        
        return {}