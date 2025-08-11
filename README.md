# Nodex - AI Reasoning, Search, and Scraping Framework

This project implements a flexible framework for AI reasoning combined with web search and content scraping capabilities. It uses Large Language Models (LLMs) to solve problems through chain-of-thought reasoning while integrating with search engines and web scraping to gather and process information.

## Key Features

### 🔍 Chain-of-Thought Reasoning
- **Structured Problem Solving**: Breaks down complex problems into logical steps
- **Self-Looping Architecture**: Continues reasoning until a solution is found
- **Plan Tracking**: Maintains detailed plan states with statuses (Pending, Done, Verification Needed, Search Needed)
- **LLM Integration**: Uses Google's Gemini API for intelligent reasoning

### 🔎 Web Search Integration
- **Qwant Search**: Integrated with Qwant search API for privacy-focused web search
- **Automatic Search**: Chain-of-thought nodes can automatically request and perform web searches
- **Search Result Integration**: Search results are automatically incorporated into the reasoning process

### 🕵️ Content Scraping
- **Robust Web Scraper**: Extracts content from search result URLs
- **Content Processing**: Parses HTML and extracts relevant text content
- **Error Handling**: Comprehensive error handling with retries and timeouts
- **Content Integration**: Scraped content is automatically incorporated into the reasoning process

### 📝 Comprehensive Answer Synthesis
- **Final Answer Generation**: Automatically synthesizes all research into a coherent, comprehensive final answer
- **Source Compilation**: Automatically compiles and references all sources used
- **Structured Output**: Produces well-formatted, organized responses

### ⚙️ Flow Management
- **Async Framework**: Custom async flow engine for managing computational graphs
- **Concurrent Execution**: Supports semaphore-based concurrency control
- **Extensible Nodes**: Easy to add new types of reasoning nodes

## Project Structure

```
├── nodes.py              # ChainOfThoughtNode with search and scraping integration
├── flow.py               # Main flow execution example
├── pocketflow.py         # Flow framework engine
├── search.py             # Qwant search integration
├── scraper.py            # Web scraping functionality
├── utility.py            # LLM utilities and response parsing
├── search_demo.py        # Demo showing search and scraping integrated reasoning
├── test_search.py        # Simple search functionality test
├── test_scraper.py       # Web scraper functionality test
├── test_fix.py           # Test for validation error fixes
├── test_comprehensive.py # Test for comprehensive answer generation
├── pyproject.toml        # Project dependencies
└── README.md             # This file
```

## Installation

Install dependencies with uv:

```bash
uv sync
```

## API Keys

Create a `.env` file with your Gemini API key:

```
GEMINI_API_KEY=your_api_key_here
```

## Usage Examples

### Search and Scraping Reasoning Flow
```bash
# Run the search and scraping demo (may take several minutes)
uv run python search_demo.py
```

### Testing Search Functionality
```bash
# Test the Qwant search integration
uv run python test_search.py
```

### Testing Scraping Functionality
```bash
# Test the web scraper
uv run python test_scraper.py
```

### Testing Comprehensive Answer Generation
```bash
# Test comprehensive answer generation
uv run python test_comprehensive.py
```

## How It Works

1. **Problem Input**: User provides a complex problem to solve
2. **Chain-of-Thought**: System breaks down the problem into structured steps
3. **Reasoning Loop**: Each step is processed by the LLM with context from previous steps
4. **Search Integration**: When information is needed, steps can request web searches
5. **Automatic Search**: System automatically performs requested searches
6. **Content Scraping**: System scrapes content from top search results
7. **Content Integration**: Scraped content is incorporated into the context for reasoning
8. **Plan Execution**: System executes steps and updates plan status
9. **Verification**: Critical results can be marked for verification
10. **Answer Synthesis**: System automatically synthesizes all information into a comprehensive final answer
11. **Source Compilation**: System compiles and references all sources used

## Dependencies

Key dependencies:
- `google-genai`: For LLM integration
- `python-dotenv`: Environment variable management
- `pyyaml`: Configuration parsing
- `requests`: HTTP requests for search APIs
- `httpx[http2]`: Modern HTTP client for scraping
- `bs4`: BeautifulSoup for HTML parsing
- `pytest`: Testing framework

## Extending the Framework

The system is designed to be extensible:
- Add new node types in `nodes.py`
- Extend search capabilities in `search.py`
- Enhance scraping in `scraper.py`
- Modify the flow engine in `pocketflow.py`
- Improve parsing in `utility.py`