"""
Recursive Agent Tree Experiment

An agent generates a function and can call a tool to spawn a sub-agent
that generates another function. Sub-agents also have access to the same tool,
forming a recursive tree. All generated functions are collected in post-order.
"""

from pathlib import Path
from dotenv import load_dotenv
import anthropic
import json

# Load .env from project root (one level up from experiments/)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = anthropic.Anthropic()

TOOLS = [
    {
        "name": "spawn_child",
        "description": (
            "Spawn a child agent that will generate its own function. "
            "The child also has this tool and can spawn further children. "
            "Use this to decompose your function into helper functions. "
            "You can call this multiple times to create multiple children."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "A description of what helper function the child should generate.",
                }
            },
            "required": ["task"],
        },
    },
    {
        "name": "submit_function",
        "description": (
            "Submit the function you generated. Call this exactly once, "
            "AFTER you have spawned any children you need. "
            "Your function can call the helper functions your children generated."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "function_code": {
                    "type": "string",
                    "description": "The Python function code you generated.",
                },
                "function_name": {
                    "type": "string",
                    "description": "The name of the function.",
                },
            },
            "required": ["function_code", "function_name"],
        },
    },
]

SYSTEM_PROMPT = """\
You are a function generator. Given a task, you will generate a Python function.

You have two tools:
1. spawn_child - Spawn a child agent to generate a helper function for you.
   You SHOULD use this to break your task into smaller helper functions.
   Each child will return the code of the helper function they generated.
2. submit_function - Submit your final function code. Your function may call
   any helper functions that your children generated.

Rules:
- Only spawn children if it makes sense to decompose the task into helpers.
- Do NOT spawn more than 3 children.
- After spawning children and receiving their results, submit your own function.
- Keep functions short and focused.
- If a task is simple/atomic, just submit your function directly without spawning.
"""


def run_agent(task: str, depth: int = 0, max_depth: int = 2) -> dict:
    """
    Run a single agent that generates a function and optionally spawns children.

    Returns a tree node:
    {
        "function_name": str,
        "function_code": str,
        "children": [child_node, ...],
    }
    """
    indent = "  " * depth
    print(f"{indent}[depth={depth}] Agent started: {task[:80]}")

    # At max depth, don't give the spawn tool
    tools = TOOLS if depth < max_depth else [TOOLS[1]]  # only submit_function

    depth_note = ""
    if depth >= max_depth:
        depth_note = "\n\nIMPORTANT: You are at maximum depth. You cannot spawn children. Just generate and submit your function directly."

    messages = [
        {"role": "user", "content": f"Generate a Python function for this task: {task}{depth_note}"}
    ]

    children = []
    my_function = None

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=tools,
            messages=messages,
        )

        # Process response
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if response.stop_reason == "end_turn" and not tool_use_blocks:
            # Agent finished without submitting - extract any text
            if my_function is None:
                text = next((b.text for b in response.content if b.type == "text"), "")
                my_function = {
                    "function_name": "unknown",
                    "function_code": text,
                }
            break

        if not tool_use_blocks:
            break

        # Append assistant response
        messages.append({"role": "assistant", "content": response.content})

        # Process each tool call
        tool_results = []
        for block in tool_use_blocks:
            if block.name == "spawn_child":
                child_task = block.input["task"]
                print(f"{indent}  -> Spawning child for: {child_task[:60]}")
                child_node = run_agent(child_task, depth + 1, max_depth)
                children.append(child_node)

                result_text = (
                    f"Child generated function '{child_node['function_name']}':\n"
                    f"```python\n{child_node['function_code']}\n```\n"
                    f"You can call {child_node['function_name']}() in your function."
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })

            elif block.name == "submit_function":
                my_function = {
                    "function_name": block.input["function_name"],
                    "function_code": block.input["function_code"],
                }
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": "Function submitted successfully.",
                })

        messages.append({"role": "user", "content": tool_results})

        if my_function is not None and response.stop_reason != "tool_use":
            break

        # If we submitted, let the model finish
        if my_function is not None:
            # One more turn to let it wrap up
            final = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )
            break

    if my_function is None:
        my_function = {"function_name": "unknown", "function_code": "pass"}

    node = {
        "function_name": my_function["function_name"],
        "function_code": my_function["function_code"],
        "children": children,
    }

    print(f"{indent}[depth={depth}] Agent done: {my_function['function_name']}")
    return node


def post_order_collect(node: dict) -> list[dict]:
    """Collect functions from the tree in post-order (children before parent)."""
    result = []
    for child in node["children"]:
        result.extend(post_order_collect(child))
    result.append({
        "function_name": node["function_name"],
        "function_code": node["function_code"],
    })
    return result


def print_tree(node: dict, indent: int = 0) -> None:
    """Print the tree structure."""
    prefix = "  " * indent
    print(f"{prefix}{node['function_name']}")
    for child in node["children"]:
        print_tree(child, indent + 1)


def main():
    root_task = (
        "Create a function called 'analyze_text' that takes a string and returns "
        "a dictionary with: word_count, sentence_count, most_common_word, "
        "and average_word_length. Break this into helper functions."
    )

    print("=" * 60)
    print("RECURSIVE AGENT TREE EXPERIMENT")
    print("=" * 60)
    print(f"\nRoot task: {root_task}\n")

    tree = run_agent(root_task, depth=0, max_depth=2)

    print("\n" + "=" * 60)
    print("TREE STRUCTURE")
    print("=" * 60)
    print_tree(tree)

    print("\n" + "=" * 60)
    print("FUNCTIONS IN POST-ORDER")
    print("=" * 60)
    functions = post_order_collect(tree)
    for i, fn in enumerate(functions, 1):
        print(f"\n--- Function {i}: {fn['function_name']} ---")
        print(fn["function_code"])

    # Combine all functions into a single module
    print("\n" + "=" * 60)
    print("COMBINED MODULE")
    print("=" * 60)
    combined = "\n\n".join(fn["function_code"] for fn in functions)
    print(combined)


if __name__ == "__main__":
    main()
