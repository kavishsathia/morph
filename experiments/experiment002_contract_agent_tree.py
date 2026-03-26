"""
Contract-Based Recursive Agent Tree Experiment

Improvement over experiment001: parent agents define a "contract" for each child
specifying the function signature, types, and constraints. Children must implement
to the contract. The spawn_child tool returns only success/failure (not the code),
since the parent already knows the interface from the contract it wrote.

This eliminates:
- Lossy natural language coordination (replaced by typed contracts)
- Code duplication (parent doesn't re-inline children's code)
- Interface mismatches (contract enforces the shape)

## Experiment Results (2026-03-26)

Model: claude-haiku-4-5
Root task: analyze_text — takes a string, returns word_count, sentence_count,
most_common_word, average_word_length.
Max depth: 2

### Tree Structure (with contracts)

    analyze_text
      count_words(text: str) -> int
      count_sentences(text: str) -> int
      find_most_common_word(text: str) -> str

### Post-Order Output

    1. count_words
    2. count_sentences
    3. find_most_common_word
    4. analyze_text

### Observations

- No code duplication: analyze_text calls helpers by name without re-implementing.
- Children matched their contracts exactly — typed signatures enforced the shape.
- Combined module is valid Python that could run as-is.
- Tree was flatter (depth 1 only, no depth 2) because contracts made each task
  clear enough that children didn't need to decompose further.
- Root agent chose not to spawn a child for average_word_length, inlining it in
  analyze_text instead. The contract model lets agents make that judgment naturally.
- Compared to experiment001: cleaner output, no duplication, typed interfaces,
  but less deep recursion (contracts reduce ambiguity so decomposition isn't needed).
"""

from pathlib import Path
from dotenv import load_dotenv
import anthropic
import json

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = anthropic.Anthropic()

# Contract schema: what the parent specifies for each child
CONTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "function_name": {
            "type": "string",
            "description": "Name of the function the child must implement.",
        },
        "description": {
            "type": "string",
            "description": "What the function should do.",
        },
        "parameters": {
            "type": "array",
            "description": "List of parameters with name and type.",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string", "description": "Python type annotation, e.g. 'str', 'list[int]', 'dict[str, Any]'"},
                },
                "required": ["name", "type"],
            },
        },
        "return_type": {
            "type": "string",
            "description": "Python return type annotation.",
        },
        "constraints": {
            "type": "array",
            "description": "Behavioral constraints the implementation must follow.",
            "items": {"type": "string"},
        },
    },
    "required": ["function_name", "description", "parameters", "return_type"],
}

TOOLS = [
    {
        "name": "spawn_child",
        "description": (
            "Spawn a child agent to implement a function according to a contract. "
            "You define the contract (name, params, return type, constraints) and "
            "the child must implement it. Returns success/failure. "
            "You can then call the function by its contract name in your own code."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "contract": CONTRACT_SCHEMA,
            },
            "required": ["contract"],
        },
    },
    {
        "name": "submit_function",
        "description": (
            "Submit the function you implemented. Call this exactly once, "
            "AFTER you have spawned any children you need. "
            "Your function can call any child functions by their contract names."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "function_code": {
                    "type": "string",
                    "description": "The Python function code. Do NOT include child function implementations.",
                },
            },
            "required": ["function_code"],
        },
    },
]

SYSTEM_PROMPT = """\
You are a function implementer. You will be given a contract to implement.

You have two tools:
1. spawn_child - Define a contract for a helper function and spawn a child agent
   to implement it. The contract specifies: function_name, description, parameters
   (with types), return_type, and optional constraints. The child MUST follow the
   contract. You only get back success/failure — trust the contract interface.
2. submit_function - Submit your implementation. Only include YOUR function code,
   not the children's implementations. You can call child functions by name.

Rules:
- Only spawn children if decomposition makes sense.
- Do NOT spawn more than 3 children.
- Do NOT re-implement child functions in your submission.
- Trust the contract: call child functions by name with the specified signature.
- If a task is simple/atomic, just submit directly without spawning.
"""

CHILD_SYSTEM_PROMPT = """\
You are a function implementer. You will be given a contract that you MUST follow exactly.

The contract specifies: function name, parameters with types, return type, and constraints.
Your implementation must match this contract precisely.

You have two tools:
1. spawn_child - Define a contract for a helper function and spawn a child agent.
2. submit_function - Submit your implementation. Only YOUR function, not children's.

Rules:
- Your function MUST match the contract signature exactly.
- Only spawn children if decomposition makes sense.
- Do NOT spawn more than 3 children.
- If a task is simple/atomic, just submit directly without spawning.
"""


def format_contract(contract: dict) -> str:
    """Format a contract into a readable string for the child agent."""
    params = ", ".join(
        f"{p['name']}: {p['type']}" for p in contract.get("parameters", [])
    )
    sig = f"def {contract['function_name']}({params}) -> {contract['return_type']}"

    lines = [
        f"Contract:",
        f"  Signature: {sig}",
        f"  Description: {contract['description']}",
    ]
    if contract.get("constraints"):
        lines.append(f"  Constraints:")
        for c in contract["constraints"]:
            lines.append(f"    - {c}")
    return "\n".join(lines)


def run_agent(
    task: str,
    contract: dict | None = None,
    depth: int = 0,
    max_depth: int = 2,
) -> dict:
    """
    Run a single agent that implements a function, optionally spawning children.

    Args:
        task: Natural language task (for root) or ignored if contract is given.
        contract: If provided, the agent must implement this contract.
        depth: Current recursion depth.
        max_depth: Maximum recursion depth.

    Returns a tree node:
    {
        "function_name": str,
        "function_code": str,
        "contract": dict | None,
        "children": [child_node, ...],
    }
    """
    indent = "  " * depth

    # Build the user prompt
    if contract:
        contract_str = format_contract(contract)
        fn_name = contract["function_name"]
        print(f"{indent}[depth={depth}] Agent started: {fn_name}")
        user_prompt = f"Implement the following function according to this contract:\n\n{contract_str}"
    else:
        fn_name = "root"
        print(f"{indent}[depth={depth}] Agent started: {task[:80]}")
        user_prompt = f"Generate a Python function for this task: {task}"

    # At max depth, only give submit_function
    tools = TOOLS if depth < max_depth else [TOOLS[1]]

    if depth >= max_depth:
        user_prompt += "\n\nIMPORTANT: You are at maximum depth. You cannot spawn children. Just implement and submit directly."

    system = CHILD_SYSTEM_PROMPT if contract else SYSTEM_PROMPT
    messages = [{"role": "user", "content": user_prompt}]

    children = []
    my_function = None

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=4096,
            system=system,
            tools=tools,
            messages=messages,
        )

        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if response.stop_reason == "end_turn" and not tool_use_blocks:
            if my_function is None:
                text = next((b.text for b in response.content if b.type == "text"), "")
                my_function = {"function_code": text}
            break

        if not tool_use_blocks:
            break

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for block in tool_use_blocks:
            if block.name == "spawn_child":
                child_contract = block.input["contract"]
                child_name = child_contract["function_name"]
                print(f"{indent}  -> Spawning child: {child_name}")
                print(f"{indent}     Contract: {format_contract(child_contract)}")

                child_node = run_agent(
                    task=child_name,
                    contract=child_contract,
                    depth=depth + 1,
                    max_depth=max_depth,
                )
                children.append(child_node)

                # Only return success/failure, not the code
                if child_node["function_code"] and child_node["function_code"] != "pass":
                    result = json.dumps({
                        "success": True,
                        "message": f"Child agent successfully implemented '{child_name}'. You can call it with the contract signature.",
                    })
                else:
                    result = json.dumps({
                        "success": False,
                        "message": f"Child agent failed to implement '{child_name}'.",
                    })

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

            elif block.name == "submit_function":
                code = block.input["function_code"]
                # Extract function name from the code
                extracted_name = fn_name
                for line in code.split("\n"):
                    if line.strip().startswith("def "):
                        extracted_name = line.strip().split("(")[0].replace("def ", "")
                        break

                my_function = {
                    "function_code": code,
                    "function_name": extracted_name,
                }
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "Function submitted successfully.",
                })

        messages.append({"role": "user", "content": tool_results})

        if my_function is not None and response.stop_reason != "tool_use":
            break

        if my_function is not None:
            final = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1024,
                system=system,
                tools=tools,
                messages=messages,
            )
            break

    if my_function is None:
        my_function = {"function_code": "pass", "function_name": fn_name}

    actual_name = my_function.get("function_name", fn_name)
    node = {
        "function_name": actual_name,
        "function_code": my_function["function_code"],
        "contract": contract,
        "children": children,
    }

    print(f"{indent}[depth={depth}] Agent done: {actual_name}")
    return node


def post_order_collect(node: dict) -> list[dict]:
    """Collect functions from the tree in post-order (children before parent)."""
    result = []
    for child in node["children"]:
        result.extend(post_order_collect(child))
    result.append({
        "function_name": node["function_name"],
        "function_code": node["function_code"],
        "contract": node.get("contract"),
    })
    return result


def print_tree(node: dict, indent: int = 0) -> None:
    """Print the tree structure with contract info."""
    prefix = "  " * indent
    name = node["function_name"]
    contract = node.get("contract")
    if contract:
        params = ", ".join(f"{p['name']}: {p['type']}" for p in contract.get("parameters", []))
        sig = f"{name}({params}) -> {contract['return_type']}"
        print(f"{prefix}{sig}")
    else:
        print(f"{prefix}{name}")
    for child in node["children"]:
        print_tree(child, indent + 1)


def main():
    root_task = (
        "Create a function called 'analyze_text' that takes a string and returns "
        "a dictionary with: word_count, sentence_count, most_common_word, "
        "and average_word_length. Break this into helper functions."
    )

    print("=" * 60)
    print("CONTRACT-BASED RECURSIVE AGENT TREE")
    print("=" * 60)
    print(f"\nRoot task: {root_task}\n")

    tree = run_agent(root_task, depth=0, max_depth=2)

    print("\n" + "=" * 60)
    print("TREE STRUCTURE (with contracts)")
    print("=" * 60)
    print_tree(tree)

    print("\n" + "=" * 60)
    print("FUNCTIONS IN POST-ORDER")
    print("=" * 60)
    functions = post_order_collect(tree)
    for i, fn in enumerate(functions, 1):
        print(f"\n--- Function {i}: {fn['function_name']} ---")
        if fn.get("contract"):
            print(f"Contract: {format_contract(fn['contract'])}")
            print()
        print(fn["function_code"])

    # Combine all functions into a single module
    print("\n" + "=" * 60)
    print("COMBINED MODULE")
    print("=" * 60)
    combined = "\n\n".join(fn["function_code"] for fn in functions)
    print(combined)


if __name__ == "__main__":
    main()
