from typing import Dict, Any, List, Tuple, Optional
from pocketflow import Node, Context, Params
from utility import call_llm, format_plan_for_prompt
from search import QwantSearch
from scraper import WebScraper
import asyncio
import json

class ChainOfThoughtNode(Node):
    """
    A self-looping Chain of Thought node that solves problems step-by-step
    by maintaining and executing a structured plan with search and scraping capabilities.
    """
    
    def __init__(self, search_client: Optional[QwantSearch] = None, max_scraped_urls: int = 5):
        """
        Initialize the ChainOfThoughtNode.
        
        Args:
            search_client: Optional QwantSearch client for web search integration
            max_scraped_urls: Maximum number of URLs to scrape per search query
        """
        self.search_client = search_client or QwantSearch()
        self.max_scraped_urls = max_scraped_urls
        self.scraper = WebScraper()
    
    async def __call__(self, ctx: Context, p: Params) -> Tuple[str, Any]:
        """
        Execute the chain of thought reasoning process.
        
        Args:
            ctx: The shared context
            p: Parameters for this run
            
        Returns:
            Tuple of (action, value) where action is "continue" or "end"
        """
        # Initialize shared store if not present
        if "problem" not in ctx:
            ctx["problem"] = p.data.get("problem", "")
            ctx["thoughts"] = []
            ctx["current_thought_number"] = 0
            ctx["solution"] = None
            ctx["search_results"] = {}
            ctx["scraped_content"] = {}
        
        # Prep phase: Read problem and previous thoughts
        problem = ctx["problem"]
        thoughts = ctx["thoughts"]
        thought_number = ctx["current_thought_number"] + 1
        ctx["current_thought_number"] = thought_number
        
        # Format history of thoughts and the last known plan
        thoughts_history = ""
        if thoughts:
            last_thought = thoughts[-1]
            thoughts_history = f"Previous thought #{last_thought['thought_number']}:\n{last_thought['current_thinking']}\n\n"
            thoughts_history += f"Current plan status:\n{format_plan_for_prompt(last_thought['planning'])}\n\n"
        
        # Check if we need to perform any searches
        search_queries = self._extract_search_queries(thoughts)
        if search_queries:
            # Perform searches
            search_results = await self._perform_searches(search_queries, ctx["search_results"])
            ctx["search_results"].update(search_results)
            
            # Scrape content from search results
            scraped_content = await self._scrape_search_results(search_results, ctx["scraped_content"])
            ctx["scraped_content"].update(scraped_content)
            
            # Add search results and scraped content to thoughts history
            thoughts_history += f"Recent search results:\n{self._format_search_results(search_results)}\n\n"
            thoughts_history += f"Scraped content from top results:\n{self._format_scraped_content(scraped_content)}\n\n"
        
        # Determine if this is the first thought
        is_first_thought = len(thoughts) == 0
        
        # Exec phase: Construct prompt and call LLM
        prompt = self._construct_prompt(problem, thoughts_history, is_first_thought)
        llm_response = call_llm(prompt)
        
        # Validate response
        try:
            self._validate_response(llm_response)
        except ValueError as e:
            print(f"\n[VALIDATION ERROR] {str(e)}")
            print(f"LLM response: {json.dumps(llm_response, indent=2)[:500]}...")
            # Try to fix common issues
            llm_response = self._fix_llm_response(llm_response)
            # Re-validate
            self._validate_response(llm_response)
        
        # Add thought number
        llm_response["thought_number"] = thought_number
        
        # Post phase: Process the response
        ctx["thoughts"].append(llm_response)
        
        # Check if we need more thoughts
        if not llm_response["next_thought_needed"]:
            # Extract final solution
            ctx["solution"] = self._extract_final_solution(llm_response, thoughts)
            
            # Print final information
            print("\n=== FINAL THOUGHT ===")
            print(f"Thought #{thought_number}:")
            print(llm_response["current_thinking"])
            print("\n=== FINAL PLAN ===")
            print(format_plan_for_prompt(llm_response["planning"]))
            print("\n=== SOLUTION ===")
            print(ctx["solution"])
            
            return "end", ctx["solution"]
        else:
            # Print current thought and plan
            print(f"\n=== THOUGHT #{thought_number} ===")
            print(llm_response["current_thinking"])
            print("\n=== CURRENT PLAN ===")
            print(format_plan_for_prompt(llm_response["planning"]))
            
            return "continue", None
    
    def _extract_final_solution(self, final_response: Dict[str, Any], all_thoughts: List[Dict[str, Any]]) -> str:
        """
        Extract a comprehensive final solution from all thoughts.
        
        Args:
            final_response: The final LLM response
            all_thoughts: All previous thoughts
            
        Returns:
            Comprehensive final solution
        """
        # If we have a clear final answer in the current response, use it
        if "final_answer" in final_response:
            return final_response["final_answer"]
        
        # Otherwise, synthesize from all thoughts
        solution_parts = []
        
        # Add the final thinking
        solution_parts.append(final_response["current_thinking"])
        
        # Compile all results from the plan
        if "planning" in final_response:
            results = self._extract_plan_results(final_response["planning"])
            if results:
                solution_parts.append("\nKey Findings:")
                solution_parts.extend(results)
        
        # Compile sources if available
        sources = self._extract_sources(all_thoughts)
        if sources:
            solution_parts.append("\nSources:")
            solution_parts.extend(sources)
        
        return "\n".join(solution_parts)
    
    def _extract_plan_results(self, plan: List[Dict[str, Any]]) -> List[str]:
        """
        Extract results from a plan.
        
        Args:
            plan: The plan to extract results from
            
        Returns:
            List of result strings
        """
        results = []
        for step in plan:
            if step.get("status") == "Done" and "result" in step:
                results.append(f"- {step['description']}: {step['result']}")
            if "sub_steps" in step:
                sub_results = self._extract_plan_results(step["sub_steps"])
                results.extend(sub_results)
        return results
    
    def _extract_sources(self, thoughts: List[Dict[str, Any]]) -> List[str]:
        """
        Extract sources from all thoughts.
        
        Args:
            thoughts: List of thoughts
            
        Returns:
            List of source strings
        """
        sources = []
        for thought in thoughts:
            # Look for source mentions in the thinking
            thinking = thought.get("current_thinking", "")
            if "Source:" in thinking or "source:" in thinking:
                # Extract source lines
                lines = thinking.split("\n")
                for line in lines:
                    if "Source:" in line or "source:" in line:
                        sources.append(line.strip())
        return list(set(sources))  # Remove duplicates
    
    def _fix_llm_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Attempt to fix common issues in LLM responses.
        
        Args:
            response: The LLM response to fix
            
        Returns:
            Fixed response
        """
        if "planning" in response and isinstance(response["planning"], list):
            for step in response["planning"]:
                # Fix missing result for Done status
                if step.get("status") == "Done" and "result" not in step:
                    step["result"] = "Completed"  # Default result
                
                # Fix missing query for Search Needed status
                if step.get("status") == "Search Needed" and "query" not in step:
                    step["query"] = "information needed"  # Default query
                
                # Fix missing mark for Verification Needed status
                if step.get("status") == "Verification Needed" and "mark" not in step:
                    step["mark"] = "Verification required"  # Default mark
                
                # Fix sub-steps if present
                if "sub_steps" in step and isinstance(step["sub_steps"], list):
                    for sub_step in step["sub_steps"]:
                        if sub_step.get("status") == "Done" and "result" not in sub_step:
                            sub_step["result"] = "Completed"  # Default result
                        if sub_step.get("status") == "Search Needed" and "query" not in sub_step:
                            sub_step["query"] = "information needed"  # Default query
        
        return response
    
    def _extract_search_queries(self, thoughts: List[Dict[str, Any]]) -> List[str]:
        """
        Extract search queries from the current plan.
        
        Args:
            thoughts: List of previous thoughts
            
        Returns:
            List of search queries to perform
        """
        if not thoughts:
            return []
            
        queries = []
        current_plan = thoughts[-1].get("planning", [])
        
        def extract_queries_from_plan(plan):
            for step in plan:
                if step.get("status") == "Search Needed" and step.get("query"):
                    queries.append(step["query"])
                if step.get("sub_steps"):
                    extract_queries_from_plan(step["sub_steps"])
        
        extract_queries_from_plan(current_plan)
        return queries
    
    async def _perform_searches(self, queries: List[str], previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform searches for the given queries.
        
        Args:
            queries: List of search queries
            previous_results: Previously cached search results
            
        Returns:
            Dictionary of query -> search results
        """
        results = {}
        
        for query in queries:
            # Skip if we already have results for this query
            if query in previous_results:
                results[query] = previous_results[query]
                continue
                
            try:
                print(f"\n[SEARCH] Performing search for: {query}")
                response = self.search_client.search(query)
                search_results = self.search_client.parse_web_results(response)
                results[query] = search_results
                
                # Print summary of search results
                print(f"[SEARCH] Found {len(search_results)} results for: {query}")
                for i, result in enumerate(search_results[:3], 1):  # Show first 3 results
                    print(f"  {i}. {result['title'][:60]}...")
                    
            except Exception as e:
                print(f"[SEARCH] Error performing search for '{query}': {str(e)}")
                results[query] = []
                
        return results
    
    async def _scrape_search_results(self, search_results: Dict[str, Any], previous_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scrape content from search results.
        
        Args:
            search_results: Dictionary of query -> search results
            previous_content: Previously scraped content
            
        Returns:
            Dictionary of URL -> scraped content
        """
        scraped_content = {}
        
        # Collect URLs to scrape
        urls_to_scrape = []
        for query, results in search_results.items():
            for result in results[:self.max_scraped_urls]:  # Limit number of URLs per query
                url = result.get('url')
                if url and url not in previous_content and url not in urls_to_scrape:
                    urls_to_scrape.append(url)
        
        if not urls_to_scrape:
            return scraped_content
        
        print(f"\n[SCRAPING] Scraping content from {len(urls_to_scrape)} URLs...")
        
        # Scrape URLs concurrently
        scraped_data = await self.scraper.scrape_multiple_urls(urls_to_scrape)
        
        # Process scraped data
        for url, data in scraped_data.items():
            if data.get('success'):
                scraped_content[url] = {
                    'title': data.get('title', ''),
                    'content': data.get('content', ''),
                    'url': url
                }
                print(f"[SCRAPING] Successfully scraped: {url[:60]}...")
            else:
                scraped_content[url] = {
                    'title': 'Error',
                    'content': f"Error scraping content: {data.get('error', 'Unknown error')}",
                    'url': url
                }
                print(f"[SCRAPING] Failed to scrape: {url[:60]}... ({data.get('error', 'Unknown error')})")
        
        return scraped_content
    
    def _format_search_results(self, search_results: Dict[str, Any]) -> str:
        """
        Format search results for inclusion in the prompt.
        
        Args:
            search_results: Dictionary of query -> results
            
        Returns:
            Formatted string of search results
        """
        if not search_results:
            return "No recent search results."
            
        formatted = []
        for query, results in search_results.items():
            formatted.append(f"Results for '{query}':")
            for i, result in enumerate(results[:3], 1):  # Show first 3 results
                formatted.append(f"  {i}. {result['title']}")
                formatted.append(f"     {result['description'][:100]}...")
                formatted.append(f"     URL: {result['url']}")
            if len(results) > 3:
                formatted.append(f"  ... and {len(results) - 3} more results")
            formatted.append("")  # Empty line between queries
            
        return "\n".join(formatted)
    
    def _format_scraped_content(self, scraped_content: Dict[str, Any]) -> str:
        """
        Format scraped content for inclusion in the prompt.
        
        Args:
            scraped_content: Dictionary of URL -> scraped content
            
        Returns:
            Formatted string of scraped content
        """
        if not scraped_content:
            return "No scraped content."
            
        formatted = []
        for url, content_data in list(scraped_content.items())[:5]:  # Limit to top 5
            title = content_data.get('title', 'No title')
            content = content_data.get('content', '')[:500] + ('...' if len(content_data.get('content', '')) > 500 else '')
            formatted.append(f"From '{title}':")
            formatted.append(f"  {content}")
            formatted.append(f"  Source: {url}")
            formatted.append("")  # Empty line between sources
            
        if len(scraped_content) > 5:
            formatted.append(f"... and {len(scraped_content) - 5} more sources")
            
        return "\n".join(formatted)
    
    def _construct_prompt(self, problem: str, thoughts_history: str, is_first_thought: bool) -> str:
        """
        Construct the prompt for the LLM based on the current state.
        
        Args:
            problem: The problem statement
            thoughts_history: Formatted history of previous thoughts
            is_first_thought: Whether this is the first thought
            
        Returns:
            The complete prompt to send to the LLM
        """
        prompt = f"""You are an expert problem solver using a Chain of Thought approach. 
You break down complex problems into clear, logical steps and solve them systematically.
You are thorough, accurate, and verify your work when possible.
You can search the web for information and use scraped content to inform your answers.

PROBLEM:
{problem}

"""

        if is_first_thought:
            prompt += """This is the first step in solving this problem. Please:
1. Analyze the problem carefully, identifying key components and requirements
2. Create a comprehensive initial plan with clear, actionable steps
3. Begin executing the first step of your plan with detailed reasoning
4. Update the plan status accordingly with specific results
5. If you need to search for information, mark the step as "Search Needed" with a specific query

"""
        else:
            prompt += f"""PREVIOUS THOUGHTS AND PLAN:
{thoughts_history}
Based on the previous thought, plan status, search results, and scraped content, please:
1. Critically evaluate the previous step's reasoning and results for accuracy
2. Identify any errors, gaps, or issues that need to be addressed
3. Use the scraped content to inform your answers when relevant
4. Execute the next pending step in the plan with detailed reasoning
5. If needed, refine the plan by breaking down complex steps into more granular sub-steps
6. Update the status of plan steps and record specific, concise results
7. If you need to search for information, mark steps as "Search Needed" with a specific query
8. If verification is needed, mark steps as "Verification Needed" with a clear reason
9. When you have completed all steps and have a comprehensive answer, set next_thought_needed to false and provide a final_answer field with your complete response

"""

        prompt += """Please provide your response in JSON format with the following structure (strictly follow this schema):

```
{
  "current_thinking": "[Your detailed evaluation and thinking for this step - be comprehensive and logical. Reference scraped content when relevant.]",
  "planning": [
    {
      "description": "[Step description - specific and actionable]",
      "status": "[Pending|Done|Verification Needed|Search Needed]",
      "result": "[REQUIRED IF STATUS IS DONE: Concise result when status is Done]",
      "query": "[REQUIRED IF STATUS IS SEARCH NEEDED: Specific search query when status is Search Needed]",
      "mark": "[REQUIRED IF STATUS IS VERIFICATION NEEDED: Reason for Verification Needed]",
      "sub_steps": [
        {
          "description": "[Sub-step description - specific and actionable]",
          "status": "[Pending|Done|Search Needed]",
          "result": "[REQUIRED IF STATUS IS DONE: Concise result when status is Done]",
          "query": "[REQUIRED IF STATUS IS SEARCH NEEDED: Specific search query when status is Search Needed]"
        }
        // ... more sub-steps if needed
      ]
    }
    // ... more steps if needed
  ],
  "next_thought_needed": true,
  "final_answer": "[REQUIRED ONLY WHEN next_thought_needed IS false: Your complete, comprehensive final answer to the original problem]"
}
```

IMPORTANT REQUIREMENTS:
- Status meanings:
  * "Pending": For steps not yet started
  * "Done": For completed steps (MUST include "result" field)
  * "Verification Needed": For steps that need verification (MUST include "mark" field)
  * "Search Needed": For steps requiring external information (MUST include "query" field)
- All "Done" steps MUST have a "result" field with a concise result description
- All "Search Needed" steps MUST have a "query" field with a specific search query
- All "Verification Needed" steps MUST have a "mark" field with a clear reason
- When you have completed your analysis and have a comprehensive answer to the original problem:
  * Set next_thought_needed to false
  * Provide a "final_answer" field containing your complete, well-structured response to the original problem
  * The final_answer should synthesize all your findings into a coherent, comprehensive response
- Ensure all JSON is properly formatted and all fields are correctly filled out
- When using scraped content, reference the source URL in your thinking

Example of correct "Done" step:
{
  "description": "Research Keynesian fiscal policy",
  "status": "Done",
  "result": "Keynes advocated for government spending during recessions to stimulate demand"
}

Example of correct "Search Needed" step:
{
  "description": "Research modern applications of Keynesian theory",
  "status": "Search Needed",
  "query": "modern applications of Keynesian economic theory 2020s"
}

Example of final response:
{
  "current_thinking": "All steps have been completed and I have a comprehensive understanding...",
  "planning": [...],
  "next_thought_needed": false,
  "final_answer": "This is my complete, comprehensive answer to the original problem..."
}
"""
        return prompt

    def _validate_response(self, response: Dict[str, Any]) -> None:
        """
        Validate the LLM response has the required structure.
        
        Args:
            response: The response from the LLM
            
        Raises:
            ValueError: If the response is missing required fields or has invalid types
        """
        required_fields = ["current_thinking", "planning", "next_thought_needed"]
        
        for field in required_fields:
            if field not in response:
                raise ValueError(f"LLM response missing required field: {field}")
        
        if not isinstance(response["current_thinking"], str):
            raise ValueError("current_thinking must be a string")
        
        if not isinstance(response["planning"], list):
            raise ValueError("planning must be a list")
        
        if not isinstance(response["next_thought_needed"], bool):
            raise ValueError("next_thought_needed must be a boolean")
        
        # If this is the final response, it must have a final_answer
        if not response["next_thought_needed"] and "final_answer" not in response:
            raise ValueError("Final response must include a 'final_answer' field")
        
        # Validate plan structure
        for step in response["planning"]:
            self._validate_plan_step(step)

    def _validate_plan_step(self, step: Dict[str, Any]) -> None:
        """
        Validate a plan step has the required structure.
        
        Args:
            step: The plan step to validate
            
        Raises:
            ValueError: If the step is missing required fields or has invalid types
        """
        if "description" not in step:
            raise ValueError("Plan step missing description field")
        
        if "status" not in step:
            raise ValueError("Plan step missing status field")
        
        valid_statuses = ["Pending", "Done", "Verification Needed", "Search Needed"]
        if step["status"] not in valid_statuses:
            raise ValueError(f"Invalid status: {step['status']}. Must be one of {valid_statuses}")
        
        # For "Done" status, result is required
        if step["status"] == "Done" and ("result" not in step or not step["result"]):
            raise ValueError("Plan step with 'Done' status must have a non-empty result field")
        
        # For "Search Needed" status, query is required
        if step["status"] == "Search Needed" and ("query" not in step or not step["query"]):
            raise ValueError("Plan step with 'Search Needed' status must have a non-empty query field")
        
        # For "Verification Needed" status, mark is required
        if step["status"] == "Verification Needed" and ("mark" not in step or not step["mark"]):
            raise ValueError("Plan step with 'Verification Needed' status must have a non-empty mark field")
        
        # Validate sub-steps if present
        if "sub_steps" in step and step["sub_steps"]:
            if not isinstance(step["sub_steps"], list):
                raise ValueError("sub_steps must be a list")
            
            for sub_step in step["sub_steps"]:
                self._validate_plan_step(sub_step)
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources."""
        await self.scraper.close()