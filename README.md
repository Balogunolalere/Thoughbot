# Self-Critique Loop Implementation

This project implements a self-critique loop for chain-of-thought reasoning, automatically inserting verification steps after each completed task and handling verification failures with corrective actions.

## Key Features

### 🔍 Automatic Verification Insertion
- **After every "Done" leaf node**: The system automatically inserts a verification step
- **Depth limiting**: Prevents infinite verification recursion by limiting to 3 levels
- **Smart detection**: Only adds verification to leaf nodes that don't already have sub-steps

### ⚠️ Verification Failure Handling
- **Automatic detection**: Identifies when verification fails based on result content
- **Rollback mechanism**: Marks failed steps back to "Pending" status  
- **Corrective actions**: Automatically adds corrective sub-steps to address issues
- **Clear marking**: Adds helpful marks to indicate verification failures

### 🔄 Self-Critique Workflow

```
[Done] Compute step
  └── [Verification Needed] Check result against constraints
       ├── [Done] → "Verification passed" ✅
       └── [Done] → "Verification failed" ❌
            └── Triggers: Parent → [Pending] + Add corrective sub-step
```

## Implementation Details

### Core Functions

#### `_insert_verification_steps(plan)`
- Recursively processes the plan tree
- Inserts verification steps after "Done" leaf nodes
- Limits verification depth to prevent infinite loops
- Returns modified plan with verification steps

#### `_handle_verification_failures(plan)`
- Scans for failed verification steps (containing "failed" in result)
- Marks parent steps back to "Pending" 
- Adds corrective sub-steps with specific failure details
- Preserves failed verification for reference

#### `count_verification_depth(description)`
- Counts nested "Verify result of" levels in descriptions
- Used to limit verification depth and prevent recursion
- Returns integer count of verification nesting

### Usage Examples

#### Basic Usage
```python
import asyncio
from pocketflow import Flow
from node import ChainOfThoughtNode

async def solve_problem():
    problem = "Calculate 2 + 2 and verify the result."
    
    flow = Flow(ChainOfThoughtNode())
    flow.edge("continue", ChainOfThoughtNode())
    
    ctx = {"problem": problem}
    result = await flow.run(ctx)
    return result

# Run with uv
asyncio.run(solve_problem())
```

#### Running Demos
```bash
# Simple math problem with verification
uv run python simple_demo.py

# Demo with potential verification failures  
uv run python failure_demo.py

# Basic verification capabilities
uv run python demo_verification.py

# Original complex problem
uv run python flow.py
```

## Project Structure

```
├── node.py              # Core ChainOfThoughtNode with self-critique loop
├── flow.py              # Main flow execution
├── pocketflow.py        # Flow framework
├── utility.py           # LLM utilities and rate limiting
├── simple_demo.py       # Simple verification demo
├── failure_demo.py      # Verification failure demo  
├── demo_verification.py # Basic verification demo
├── pyproject.toml       # Project dependencies
└── README.md           # This file
```

## Configuration

The system uses JSON format for LLM communication (more robust than YAML) and includes:
- **Rate limiting**: Built-in rate limiting for Gemini API
- **Error handling**: Comprehensive error handling with debugging output
- **Depth limiting**: Configurable verification depth (default: 3 levels)
- **Environment setup**: Uses `.env` file for API keys

## Dependencies

Install with uv:
```bash
uv sync
```

Key dependencies:
- `google-genai`: For LLM integration
- `python-dotenv`: Environment variable management  
- `pyyaml`: Configuration parsing
- `pytest`: Testing framework

## API Keys

Create a `.env` file with:
```
GEMINI_API_KEY=your_api_key_here
```

## How It Works

1. **Problem Input**: User provides a problem to solve
2. **Chain-of-Thought**: System breaks down problem into steps
3. **Step Execution**: Each step is executed and marked "Done"
4. **Auto-Verification**: System automatically adds verification steps
5. **Verification Check**: Each verification examines the parent result
6. **Failure Handling**: If verification fails, parent goes back to "Pending"
7. **Corrective Action**: System adds specific corrective sub-steps
8. **Iteration**: Process continues until all steps pass verification

## Example Output

```
--- Thought 1 ---
Creating plan for: Calculate 5 * 3

Current plan:
- [Pending] Calculate the product of 5 and 3
- [Pending] Verify the result

--- Thought 2 ---  
Executing calculation step...

Current plan:
- [Done] Calculate the product of 5 and 3  → 5 * 3 = 15
  - [Verification Needed] Verify result of 'Calculate the product of 5 and 3'
- [Pending] Verify the result

--- Thought 3 ---
Performing verification...

Current plan:
- [Done] Calculate the product of 5 and 3  → 5 * 3 = 15
  - [Done] Verify result of 'Calculate the product of 5 and 3'  → Verification passed - calculation is correct
    - [Verification Needed] Verify result of 'Verify result of...'
```

## Benefits

- **Reliability**: Catches computation errors automatically
- **Transparency**: Shows complete verification chain  
- **Self-correction**: Handles failures gracefully with corrective actions
- **Depth control**: Prevents infinite verification loops
- **Extensible**: Easy to customize verification criteria

## Future Enhancements

- Custom verification criteria per problem type
- Parallel verification for independent steps
- Verification confidence scoring
- Integration with external validation tools
- Performance optimization for large problem trees
