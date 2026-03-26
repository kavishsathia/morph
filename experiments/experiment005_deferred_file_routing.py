"""
Deferred File Routing Experiment

Improvement over experiment004: file routing happens AFTER all agents finish,
not inline during generation. A single file router agent processes a queue of
functions (in pre-order), assigning each one a file path. The router sees the
full evolving index at each step, so it can make consistent grouping decisions.

Phase 1: Generate all functions using the async contract tree (experiment003).
Phase 2: Collect functions in pre-order. A router agent dequeues one at a time,
         sees the current index, and assigns a file path via a tool.

## Experiment Results (2026-03-27)

Model: claude-haiku-4-5
Root task: analyze_text — takes a string, returns word_count, sentence_count,
most_common_word, average_word_length.
Max depth: 2

### Tree Structure

    analyze_text                                   [src/text_analysis/analyze_text.py]
      count_words(text: str) -> int                [src/text_analysis/utils.py]
      count_sentences(text: str) -> int            [src/text_analysis/utils.py]
      get_most_common_word(text: str) -> str       [src/text_analysis/utils.py]

### File Index

    src/text_analysis/analyze_text.py  -> analyze_text
    src/text_analysis/utils.py         -> count_words, count_sentences, get_most_common_word

### Observations

- Deferred routing fixed the consistency problem from experiment004.
  All paths under one consistent directory: src/text_analysis/.
- Router grouped all 3 helper functions into utils.py after seeing the first
  one placed there — the evolving index gave it context to stay consistent.
- Pre-order queue meant the entry point (analyze_text) was routed first,
  then helpers followed, giving the router top-down context.
- The root agent even generated import statements (from count_words import ...)
  though the imports reference module names not file paths — a gap to address.
"""

from pathlib import Path
from dotenv import load_dotenv
import anthropic
import json
import threading
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from uuid import uuid4

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = anthropic.Anthropic()
executor = ThreadPoolExecutor(max_workers=8)

# ──────────────────────────────────────────────
# Phase 1: Async contract tree (from experiment003)
# ──────────────────────────────────────────────

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
                    "type": {"type": "string"},
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

GEN_TOOLS = [
    {
        "name": "spawn_child",
        "description": (
            "Spawn a child agent to implement a function according to a contract. "
            "Returns IMMEDIATELY with a task_id. Spawn all children first, then wait."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"contract": CONTRACT_SCHEMA},
            "required": ["contract"],
        },
    },
    {
        "name": "wait_for_child",
        "description": "Wait for a previously spawned child to finish.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "The task_id from spawn_child."},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "wait_all",
        "description": "Wait for ALL pending children at once.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "submit_function",
        "description": "Submit your implementation. Call once, after waiting for all children.",
        "input_schema": {
            "type": "object",
            "properties": {
                "function_code": {
                    "type": "string",
                    "description": "Your function code. Do NOT include child implementations.",
                },
            },
            "required": ["function_code"],
        },
    },
]

GEN_SYSTEM = """\
You are a function implementer.

Tools:
1. spawn_child(contract) - Spawn child. Returns immediately with task_id.
2. wait_for_child(task_id) - Wait for one child.
3. wait_all() - Wait for all children.
4. submit_function(code) - Submit your implementation.

Workflow: spawn children -> wait -> submit.
Rules: max 3 children, don't re-implement children, submit only your code.
"""

_print_lock = threading.Lock()


def safe_print(msg: str):
    with _print_lock:
        print(msg)


def format_contract(contract: dict) -> str:
    params = ", ".join(
        f"{p['name']}: {p['type']}" for p in contract.get("parameters", [])
    )
    sig = f"def {contract['function_name']}({params}) -> {contract['return_type']}"
    lines = [f"  Signature: {sig}", f"  Description: {contract['description']}"]
    if contract.get("constraints"):
        lines.append("  Constraints:")
        for c in contract["constraints"]:
            lines.append(f"    - {c}")
    return "\n".join(lines)


def run_agent(
    task: str,
    contract: dict | None = None,
    depth: int = 0,
    max_depth: int = 2,
) -> dict:
    indent = "  " * depth

    if contract:
        fn_name = contract["function_name"]
        safe_print(f"{indent}[depth={depth}] Agent started: {fn_name}")
        user_prompt = f"Implement this contract:\n\n{format_contract(contract)}"
    else:
        fn_name = "root"
        safe_print(f"{indent}[depth={depth}] Agent started: {task[:80]}")
        user_prompt = f"Generate a Python function for this task: {task}"

    tools = GEN_TOOLS if depth < max_depth else [GEN_TOOLS[3]]
    if depth >= max_depth:
        user_prompt += "\n\nYou are at maximum depth. Just implement and submit directly."

    messages = [{"role": "user", "content": user_prompt}]
    children = []
    pending_futures: dict[str, tuple[Future, dict]] = {}
    my_function = None

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=4096,
            system=GEN_SYSTEM,
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
                task_id = str(uuid4())[:8]
                safe_print(f"{indent}  -> Spawning: {child_name} [task_id={task_id}]")

                future = executor.submit(
                    run_agent, task=child_name, contract=child_contract,
                    depth=depth + 1, max_depth=max_depth,
                )
                pending_futures[task_id] = (future, child_contract)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps({"task_id": task_id}),
                })

            elif block.name == "wait_for_child":
                task_id = block.input["task_id"]
                if task_id not in pending_futures:
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": block.id,
                        "content": json.dumps({"success": False, "message": f"Unknown task_id '{task_id}'."}),
                        "is_error": True,
                    })
                else:
                    future, child_contract = pending_futures.pop(task_id)
                    child_name = child_contract["function_name"]
                    safe_print(f"{indent}  <- Waiting: {child_name}")
                    child_node = future.result()
                    children.append(child_node)
                    success = bool(child_node["function_code"] and child_node["function_code"] != "pass")
                    safe_print(f"{indent}  <- Done: {child_name}")
                    tool_results.append({
                        "type": "tool_result", "tool_use_id": block.id,
                        "content": json.dumps({"success": success}),
                    })

            elif block.name == "wait_all":
                safe_print(f"{indent}  <- Waiting for all {len(pending_futures)} children...")
                results_list = []
                for tid, (future, child_contract) in list(pending_futures.items()):
                    child_name = child_contract["function_name"]
                    child_node = future.result()
                    children.append(child_node)
                    success = bool(child_node["function_code"] and child_node["function_code"] != "pass")
                    safe_print(f"{indent}  <- Done: {child_name} ({'ok' if success else 'fail'})")
                    results_list.append({"task_id": tid, "function_name": child_name, "success": success})
                pending_futures.clear()
                tool_results.append({
                    "type": "tool_result", "tool_use_id": block.id,
                    "content": json.dumps({"results": results_list}),
                })

            elif block.name == "submit_function":
                code = block.input["function_code"]
                extracted_name = fn_name
                for line in code.split("\n"):
                    if line.strip().startswith("def "):
                        extracted_name = line.strip().split("(")[0].replace("def ", "")
                        break
                my_function = {"function_code": code, "function_name": extracted_name}
                tool_results.append({
                    "type": "tool_result", "tool_use_id": block.id,
                    "content": "Function submitted.",
                })

        messages.append({"role": "user", "content": tool_results})

        if my_function is not None and response.stop_reason != "tool_use":
            break
        if my_function is not None:
            client.messages.create(
                model="claude-haiku-4-5", max_tokens=1024,
                system=GEN_SYSTEM, tools=tools, messages=messages,
            )
            break

    for task_id, (future, child_contract) in pending_futures.items():
        children.append(future.result())

    if my_function is None:
        my_function = {"function_code": "pass", "function_name": fn_name}

    actual_name = my_function.get("function_name", fn_name)
    safe_print(f"{indent}[depth={depth}] Agent done: {actual_name}")
    return {
        "function_name": actual_name,
        "function_code": my_function["function_code"],
        "contract": contract,
        "children": children,
    }


# ──────────────────────────────────────────────
# Phase 2: Deferred file routing
# ──────────────────────────────────────────────

ROUTER_TOOLS = [
    {
        "name": "assign_file",
        "description": (
            "Assign the current function to a file path. "
            "You can place it in an existing file or create a new one."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The file path, e.g. 'src/utils/text.py'. Use Python conventions.",
                },
            },
            "required": ["file_path"],
        },
    },
]

ROUTER_SYSTEM = """\
You are a file router for a Python project. You will be given functions one at a
time and must assign each to a file path using the assign_file tool.

Think about good project organization:
- Group related functions in the same file
- Use descriptive directory and file names
- Follow Python conventions (snake_case, logical module structure)
- Keep files focused — don't dump everything in one file
- Look at the current file index to stay consistent with previous assignments

You MUST call assign_file exactly once for each function.
"""


def pre_order_collect(node: dict) -> list[dict]:
    """Collect functions from the tree in pre-order (parent before children)."""
    result = [{
        "function_name": node["function_name"],
        "function_code": node["function_code"],
        "contract": node.get("contract"),
    }]
    for child in node["children"]:
        result.extend(pre_order_collect(child))
    return result


def post_order_collect(node: dict) -> list[dict]:
    """Collect functions in post-order (children before parent)."""
    result = []
    for child in node["children"]:
        result.extend(post_order_collect(child))
    result.append({
        "function_name": node["function_name"],
        "function_code": node["function_code"],
        "contract": node.get("contract"),
    })
    return result


def route_all_functions(queue: deque[dict]) -> dict[str, str]:
    """
    Run the router agent. It processes the queue one function at a time,
    using an agentic loop with the assign_file tool.

    Returns a dict: function_name -> file_path
    """
    file_index: dict[str, list[str]] = {}  # file_path -> [function_names]
    assignments: dict[str, str] = {}       # function_name -> file_path

    print("\n[Router] Starting file routing...")

    while queue:
        fn = queue.popleft()
        fn_name = fn["function_name"]
        fn_code = fn["function_code"]
        contract = fn.get("contract")

        index_str = json.dumps(file_index, indent=2) if file_index else "(empty)"
        contract_str = f"\n\nContract:\n{format_contract(contract)}" if contract else ""

        prompt = (
            f"Assign this function to a file:\n\n"
            f"Function: {fn_name}\n"
            f"```python\n{fn_code}\n```"
            f"{contract_str}\n\n"
            f"Current file index:\n{index_str}\n\n"
            f"Remaining in queue: {len(queue)} functions"
        )

        messages = [{"role": "user", "content": prompt}]
        assigned = False

        while not assigned:
            response = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=512,
                system=ROUTER_SYSTEM,
                tools=ROUTER_TOOLS,
                messages=messages,
            )

            for block in response.content:
                if block.type == "tool_use" and block.name == "assign_file":
                    file_path = block.input["file_path"]
                    assignments[fn_name] = file_path
                    if file_path not in file_index:
                        file_index[file_path] = []
                    file_index[file_path].append(fn_name)
                    print(f"  [Router] {fn_name} -> {file_path}")
                    assigned = True

            if not assigned:
                # Model didn't call the tool, nudge it
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": "Please use the assign_file tool to assign this function to a file path."})

    return assignments


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def print_tree(node: dict, assignments: dict[str, str], indent: int = 0) -> None:
    prefix = "  " * indent
    name = node["function_name"]
    path = assignments.get(name, "?")
    contract = node.get("contract")
    if contract:
        params = ", ".join(f"{p['name']}: {p['type']}" for p in contract.get("parameters", []))
        sig = f"{name}({params}) -> {contract['return_type']}"
        print(f"{prefix}{sig}  [{path}]")
    else:
        print(f"{prefix}{name}  [{path}]")
    for child in node["children"]:
        print_tree(child, assignments, indent + 1)


def main():
    root_task = (
        "Create a function called 'analyze_text' that takes a string and returns "
        "a dictionary with: word_count, sentence_count, most_common_word, "
        "and average_word_length. Break this into helper functions."
    )

    print("=" * 60)
    print("DEFERRED FILE ROUTING EXPERIMENT")
    print("=" * 60)
    print(f"\nRoot task: {root_task}\n")

    # Phase 1: Generate
    print("--- Phase 1: Generate ---\n")
    tree = run_agent(root_task, depth=0, max_depth=2)

    # Phase 2: Route (pre-order queue)
    print("\n--- Phase 2: Route (pre-order) ---")
    pre_order = pre_order_collect(tree)
    queue = deque(pre_order)
    print(f"\nQueue ({len(queue)} functions): {[f['function_name'] for f in queue]}")
    assignments = route_all_functions(queue)

    # Results
    print("\n" + "=" * 60)
    print("TREE STRUCTURE (with file paths)")
    print("=" * 60)
    print_tree(tree, assignments)

    print("\n" + "=" * 60)
    print("FILE INDEX")
    print("=" * 60)
    # Invert assignments to file_path -> [functions]
    index: dict[str, list[str]] = {}
    for fn_name, path in assignments.items():
        if path not in index:
            index[path] = []
        index[path].append(fn_name)
    for path, funcs in sorted(index.items()):
        print(f"\n  {path}:")
        for fn in funcs:
            print(f"    - {fn}")

    print("\n" + "=" * 60)
    print("FUNCTIONS IN POST-ORDER (with file paths)")
    print("=" * 60)
    post_order = post_order_collect(tree)
    for i, fn in enumerate(post_order, 1):
        path = assignments.get(fn["function_name"], "?")
        print(f"\n--- {i}. {fn['function_name']} -> {path} ---")
        print(fn["function_code"])

    # Project layout grouped by file
    print("\n" + "=" * 60)
    print("PROJECT LAYOUT")
    print("=" * 60)
    files: dict[str, list[str]] = {}
    fn_map = {fn["function_name"]: fn["function_code"] for fn in post_order}
    for fn_name, path in sorted(assignments.items(), key=lambda x: x[1]):
        if path not in files:
            files[path] = []
        files[path].append(fn_map[fn_name])

    for fp, codes in sorted(files.items()):
        print(f"\n# ===== {fp} =====")
        print("\n\n".join(codes))

    executor.shutdown(wait=False)


if __name__ == "__main__":
    main()
