"""
Filesystem Routing Experiment

Improvement over experiment005: the router agent now physically writes files to
disk under a tmp folder. It has access to read_file, append_to_file, and
replace_text tools. The index (agent -> file path) is still maintained as the
source of truth for where each agent's function lives.

Phase 1: Generate all functions using the async contract tree.
Phase 2: Router agent dequeues functions (pre-order), assigns file paths (index),
         and writes the actual code to disk using filesystem tools.

## Experiment Results (2026-03-27)

Model: claude-haiku-4-5
Root task: analyze_text
Max depth: 2

### File Index

    src/text_analysis/analyzer.py:
      - count_words, count_sentences, get_most_common_word,
        calculate_average_word_length, analyze_text

### Observations

- Router wrote a real Python file to disk — valid, runnable code.
- All functions placed in one file (src/text_analysis/analyzer.py) since the
  project is small enough. Router made a reasonable judgment call.
- Router used read_file before writing to check existing content, then used
  replace_text to update functions rather than blindly appending duplicates.
- Bug: root agent extracted its own name as "count_words" instead of
  "analyze_text" because the name extraction heuristic matched the first `def`
  in the submitted code (which included helper references). This caused a
  duplicate in the pre-order queue.
- The router handled the duplicate gracefully — it read the file, saw the
  function existed, and used replace_text to update it.
- Imports (re, Counter) were placed at the top of the file correctly.
"""

from pathlib import Path
from dotenv import load_dotenv
import anthropic
import json
import os
import shutil
import tempfile
import threading
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from uuid import uuid4

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = anthropic.Anthropic()
executor = ThreadPoolExecutor(max_workers=8)

# ──────────────────────────────────────────────
# Phase 1: Async contract tree (same as experiment005)
# ──────────────────────────────────────────────

CONTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "function_name": {"type": "string"},
        "description": {"type": "string"},
        "parameters": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "type": {"type": "string"}},
                "required": ["name", "type"],
            },
        },
        "return_type": {"type": "string"},
        "constraints": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["function_name", "description", "parameters", "return_type"],
}

GEN_TOOLS = [
    {
        "name": "spawn_child",
        "description": "Spawn a child agent. Returns immediately with task_id.",
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
            "properties": {"task_id": {"type": "string"}},
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
        "description": "Submit your implementation. Only your code, not children's.",
        "input_schema": {
            "type": "object",
            "properties": {"function_code": {"type": "string"}},
            "required": ["function_code"],
        },
    },
]

GEN_SYSTEM = """\
You are a function implementer.

Tools: spawn_child(contract), wait_for_child(task_id), wait_all(), submit_function(code).
Workflow: spawn children -> wait -> submit.
Rules: max 3 children, don't re-implement children, submit only your code.
"""

_print_lock = threading.Lock()


def safe_print(msg: str):
    with _print_lock:
        print(msg)


def format_contract(contract: dict) -> str:
    params = ", ".join(f"{p['name']}: {p['type']}" for p in contract.get("parameters", []))
    sig = f"def {contract['function_name']}({params}) -> {contract['return_type']}"
    lines = [f"  Signature: {sig}", f"  Description: {contract['description']}"]
    if contract.get("constraints"):
        lines.append("  Constraints:")
        for c in contract["constraints"]:
            lines.append(f"    - {c}")
    return "\n".join(lines)


def run_agent(task: str, contract: dict | None = None, depth: int = 0, max_depth: int = 2) -> dict:
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
        user_prompt += "\n\nMax depth reached. Just implement and submit directly."

    messages = [{"role": "user", "content": user_prompt}]
    children = []
    pending_futures: dict[str, tuple[Future, dict]] = {}
    my_function = None

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5", max_tokens=4096, system=GEN_SYSTEM,
            tools=tools, messages=messages,
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
                safe_print(f"{indent}  -> Spawning: {child_name} [{task_id}]")
                future = executor.submit(run_agent, child_name, child_contract, depth + 1, max_depth)
                pending_futures[task_id] = (future, child_contract)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"task_id": task_id})})

            elif block.name == "wait_for_child":
                task_id = block.input["task_id"]
                if task_id not in pending_futures:
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"success": False}), "is_error": True})
                else:
                    future, cc = pending_futures.pop(task_id)
                    safe_print(f"{indent}  <- Waiting: {cc['function_name']}")
                    child_node = future.result()
                    children.append(child_node)
                    safe_print(f"{indent}  <- Done: {cc['function_name']}")
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"success": True})})

            elif block.name == "wait_all":
                safe_print(f"{indent}  <- Waiting for all {len(pending_futures)} children...")
                results_list = []
                for tid, (future, cc) in list(pending_futures.items()):
                    child_node = future.result()
                    children.append(child_node)
                    safe_print(f"{indent}  <- Done: {cc['function_name']}")
                    results_list.append({"function_name": cc["function_name"], "success": True})
                pending_futures.clear()
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"results": results_list})})

            elif block.name == "submit_function":
                code = block.input["function_code"]
                extracted_name = fn_name
                for line in code.split("\n"):
                    if line.strip().startswith("def "):
                        extracted_name = line.strip().split("(")[0].replace("def ", "")
                        break
                my_function = {"function_code": code, "function_name": extracted_name}
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": "Submitted."})

        messages.append({"role": "user", "content": tool_results})
        if my_function is not None and response.stop_reason != "tool_use":
            break
        if my_function is not None:
            client.messages.create(model="claude-haiku-4-5", max_tokens=1024, system=GEN_SYSTEM, tools=tools, messages=messages)
            break

    for tid, (future, cc) in pending_futures.items():
        children.append(future.result())
    if my_function is None:
        my_function = {"function_code": "pass", "function_name": fn_name}

    actual_name = my_function.get("function_name", fn_name)
    safe_print(f"{indent}[depth={depth}] Agent done: {actual_name}")
    return {"function_name": actual_name, "function_code": my_function["function_code"], "contract": contract, "children": children}


# ──────────────────────────────────────────────
# Phase 2: Filesystem routing
# ──────────────────────────────────────────────

def make_router_tools(project_root: str) -> list[dict]:
    return [
        {
            "name": "read_file",
            "description": "Read the contents of a file. Returns the file content or an error if it doesn't exist.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path from project root, e.g. 'src/utils.py'"},
                },
                "required": ["file_path"],
            },
        },
        {
            "name": "append_to_file",
            "description": "Append content to a file. Creates the file (and directories) if it doesn't exist.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path from project root"},
                    "content": {"type": "string", "description": "Content to append"},
                },
                "required": ["file_path", "content"],
            },
        },
        {
            "name": "replace_text",
            "description": "Replace a specific string in a file with new text. Fails if old_text is not found.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "file_path": {"type": "string", "description": "Relative path from project root"},
                    "old_text": {"type": "string", "description": "Text to find and replace"},
                    "new_text": {"type": "string", "description": "Replacement text"},
                },
                "required": ["file_path", "old_text", "new_text"],
            },
        },
        {
            "name": "assign_file",
            "description": (
                "Record in the index which file this function belongs to. "
                "Call this ONCE per function to register it, then use the filesystem tools to write the code."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "function_name": {"type": "string"},
                    "file_path": {"type": "string", "description": "Relative path, e.g. 'src/text_analysis/utils.py'"},
                },
                "required": ["function_name", "file_path"],
            },
        },
        {
            "name": "done",
            "description": "Signal that you are done placing this function.",
            "input_schema": {"type": "object", "properties": {}},
        },
    ]


ROUTER_SYSTEM = """\
You are a file router for a Python project. You will be given functions one at a
time. For each function you must:

1. Call assign_file to register which file this function belongs to (updates the index).
2. Use the filesystem tools (read_file, append_to_file, replace_text) to actually
   write the function code into the correct file. Create directories as needed.
3. Add any necessary imports at the top of the file.
4. Call done when finished with this function.

Guidelines:
- Group related functions in the same file.
- Use descriptive paths (e.g. src/text_analysis/utils.py).
- Follow Python conventions (snake_case files, logical modules).
- Check what's already in a file before appending to avoid duplicates.
- Add imports where the function is USED, not where it's defined.
- Look at the current index to stay consistent.
"""


def execute_router_tool(tool_name: str, tool_input: dict, project_root: str,
                        file_index: dict[str, list[str]], assignments: dict[str, str]) -> str:
    """Execute a router tool and return the result."""
    if tool_name == "read_file":
        fpath = os.path.join(project_root, tool_input["file_path"])
        if os.path.exists(fpath):
            with open(fpath) as f:
                content = f.read()
            return content if content else "(empty file)"
        else:
            return f"Error: file '{tool_input['file_path']}' does not exist."

    elif tool_name == "append_to_file":
        fpath = os.path.join(project_root, tool_input["file_path"])
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "a") as f:
            f.write(tool_input["content"])
        return f"Appended to {tool_input['file_path']}."

    elif tool_name == "replace_text":
        fpath = os.path.join(project_root, tool_input["file_path"])
        if not os.path.exists(fpath):
            return f"Error: file '{tool_input['file_path']}' does not exist."
        with open(fpath) as f:
            content = f.read()
        old = tool_input["old_text"]
        if old not in content:
            return f"Error: old_text not found in '{tool_input['file_path']}'."
        content = content.replace(old, tool_input["new_text"], 1)
        with open(fpath, "w") as f:
            f.write(content)
        return f"Replaced text in {tool_input['file_path']}."

    elif tool_name == "assign_file":
        fn_name = tool_input["function_name"]
        fp = tool_input["file_path"]
        assignments[fn_name] = fp
        if fp not in file_index:
            file_index[fp] = []
        file_index[fp].append(fn_name)
        return f"Indexed: {fn_name} -> {fp}"

    elif tool_name == "done":
        return "Done."

    return f"Unknown tool: {tool_name}"


def route_all_functions(queue: deque[dict], project_root: str) -> dict[str, str]:
    """Router agent processes the queue, writing files to disk."""
    file_index: dict[str, list[str]] = {}
    assignments: dict[str, str] = {}
    router_tools = make_router_tools(project_root)

    print(f"\n[Router] Writing to: {project_root}")

    while queue:
        fn = queue.popleft()
        fn_name = fn["function_name"]
        fn_code = fn["function_code"]
        contract = fn.get("contract")

        index_str = json.dumps(file_index, indent=2) if file_index else "(empty)"
        contract_str = f"\n\nContract:\n{format_contract(contract)}" if contract else ""

        prompt = (
            f"Place this function in the project:\n\n"
            f"Function: {fn_name}\n"
            f"```python\n{fn_code}\n```"
            f"{contract_str}\n\n"
            f"Current index:\n{index_str}\n\n"
            f"Remaining in queue: {len(queue)} functions\n"
            f"Project root: {project_root}"
        )

        messages = [{"role": "user", "content": prompt}]
        done = False

        while not done:
            response = client.messages.create(
                model="claude-haiku-4-5", max_tokens=2048,
                system=ROUTER_SYSTEM, tools=router_tools, messages=messages,
            )

            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            if not tool_use_blocks:
                # No tool calls — nudge
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": "Please use the tools to assign and write this function."})
                continue

            messages.append({"role": "assistant", "content": response.content})
            tool_results = []

            for block in tool_use_blocks:
                result = execute_router_tool(block.name, block.input, project_root, file_index, assignments)
                print(f"  [Router] {block.name}({json.dumps(block.input)[:80]}) -> {result[:60]}")
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})

                if block.name == "done":
                    done = True

            messages.append({"role": "user", "content": tool_results})

    return assignments


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def pre_order_collect(node: dict) -> list[dict]:
    result = [{"function_name": node["function_name"], "function_code": node["function_code"], "contract": node.get("contract")}]
    for child in node["children"]:
        result.extend(pre_order_collect(child))
    return result


def post_order_collect(node: dict) -> list[dict]:
    result = []
    for child in node["children"]:
        result.extend(post_order_collect(child))
    result.append({"function_name": node["function_name"], "function_code": node["function_code"], "contract": node.get("contract")})
    return result


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


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    root_task = (
        "Create a function called 'analyze_text' that takes a string and returns "
        "a dictionary with: word_count, sentence_count, most_common_word, "
        "and average_word_length. Break this into helper functions."
    )

    # Create tmp project directory
    project_root = tempfile.mkdtemp(prefix="morph_exp006_")

    print("=" * 60)
    print("FILESYSTEM ROUTING EXPERIMENT")
    print("=" * 60)
    print(f"\nRoot task: {root_task}")
    print(f"Project root: {project_root}\n")

    # Phase 1: Generate
    print("--- Phase 1: Generate ---\n")
    tree = run_agent(root_task, depth=0, max_depth=2)

    # Phase 2: Route + write to disk
    print("\n--- Phase 2: Route + Write ---")
    pre_order = pre_order_collect(tree)
    queue = deque(pre_order)
    print(f"\nQueue ({len(queue)} functions): {[f['function_name'] for f in queue]}")
    assignments = route_all_functions(queue, project_root)

    # Results
    print("\n" + "=" * 60)
    print("TREE STRUCTURE")
    print("=" * 60)
    print_tree(tree, assignments)

    print("\n" + "=" * 60)
    print("FILE INDEX")
    print("=" * 60)
    index: dict[str, list[str]] = {}
    for fn_name, path in assignments.items():
        index.setdefault(path, []).append(fn_name)
    for path, funcs in sorted(index.items()):
        print(f"\n  {path}:")
        for fn in funcs:
            print(f"    - {fn}")

    # Show actual files on disk
    print("\n" + "=" * 60)
    print(f"FILES ON DISK ({project_root})")
    print("=" * 60)
    for dirpath, dirnames, filenames in os.walk(project_root):
        for fname in sorted(filenames):
            fpath = os.path.join(dirpath, fname)
            relpath = os.path.relpath(fpath, project_root)
            print(f"\n# ===== {relpath} =====")
            with open(fpath) as f:
                print(f.read())

    print(f"\nProject written to: {project_root}")

    executor.shutdown(wait=False)


if __name__ == "__main__":
    main()
