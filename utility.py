import os
import yaml
import re
import json
from typing import Dict, Any, List
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

def call_llm(prompt: str) -> Dict[str, Any]:
    """
    Call the LLM with a prompt and return the parsed JSON response.
    
    Args:
        prompt: The prompt to send to the LLM
    Returns:
        Dictionary containing the parsed JSON response
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")
    client = genai.Client(api_key=api_key)
    model = "gemini-2.5-flash"
    contents = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=prompt)],
        ),
    ]
    generate_content_config = types.GenerateContentConfig(
        temperature=0,
        top_p=0.9,
        response_mime_type="application/json",
        thinking_config=types.ThinkingConfig(thinking_budget=-1),
    )
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=generate_content_config,
    )
    response_text = response.text
    return _parse_llm_response(response_text)

def _parse_llm_response(response_text: str) -> Dict[str, Any]:
    """
    Parse LLM response with multiple fallback strategies.
    
    Args:
        response_text: Raw response text from LLM
        
    Returns:
        Parsed dictionary from the response
        
    Raises:
        ValueError: If no valid JSON/YAML can be extracted
    """
    # Clean the response text
    response_text = response_text.strip()
    
    # Strategy 1: Try to parse as JSON directly
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Extract JSON from code block
    try:
        json_match = re.search(r'```(?:json)?\\s*({[\\s\\S]*?})\\s*```', response_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
    except (json.JSONDecodeError, AttributeError):
        pass
    
    # Strategy 3: Extract the first JSON object
    try:
        # Find the first '{' and last '}'
        start = response_text.find('{')
        if start != -1:
            # Count braces to find matching closing brace
            brace_count = 0
            for i, char in enumerate(response_text[start:], start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        json_str = response_text[start:i+1]
                        return json.loads(json_str)
    except json.JSONDecodeError:
        pass
    
    # Strategy 4: Try YAML parsing
    try:
        return yaml.safe_load(response_text)
    except yaml.YAMLError:
        pass
    
    # Strategy 5: Extract YAML from code block
    try:
        yaml_match = re.search(r'```(?:yaml)?\\s*([\\s\\S]*?)\\s*```', response_text, re.DOTALL)
        if yaml_match:
            return yaml.safe_load(yaml_match.group(1))
    except (yaml.YAMLError, AttributeError):
        pass
    
    # Strategy 6: Try to find and parse any valid JSON object
    try:
        # Look for any JSON object in the text
        objects = re.findall(r'{[^{}]*(?:{[^{}]*}[^{}]*)*}', response_text)
        for obj_str in objects:
            try:
                return json.loads(obj_str)
            except json.JSONDecodeError:
                continue
    except Exception:
        pass
    
    # If all strategies fail, raise an error with a sample of the response
    sample = response_text[:500] + ("..." if len(response_text) > 500 else "")
    raise ValueError(f"Failed to parse LLM response. Attempted multiple parsing strategies.\
Response sample: {sample}")

def format_plan(plan: List[Dict[str, Any]], indent: int = 0) -> str:
    """
    Format a plan structure into a readable string representation.
    
    Args:
        plan: The plan structure to format
        indent: Current indentation level
        
    Returns:
        Formatted string representation of the plan
    """
    if not plan:
        return ""
        
    result = []
    indent_str = "  " * indent
    
    for step in plan:
        # Format the main step
        status = step.get("status", "Unknown")
        result.append(f"{indent_str}- {step.get('description', 'No description')} [{status}]")
        
        # Add result if available
        if step.get("result"):
            result.append(f"{indent_str}  Result: {step['result']}")
            
        # Add query if search needed
        if status == "Search Needed" and step.get("query"):
            result.append(f"{indent_str}  Query: {step['query']}")
            
        # Add mark if verification needed
        if status == "Verification Needed" and step.get("mark"):
            result.append(f"{indent_str}  Mark: {step['mark']}")
            
        # Format sub-steps if available
        if step.get("sub_steps"):
            sub_plan_str = format_plan(step["sub_steps"], indent + 1)
            if sub_plan_str:
                result.append(sub_plan_str)
    
    return "\n".join(result)

def format_plan_for_prompt(plan: List[Dict[str, Any]]) -> str:
    """
    Format a plan structure specifically for inclusion in an LLM prompt.
    
    Args:
        plan: The plan structure to format
        
    Returns:
        Formatted string representation of the plan for prompts
    """
    formatted = format_plan(plan)
    return formatted if formatted else "No plan available"