"""
File-Routed Async Contract Agent Tree Experiment

Improvement over experiment003: when an agent submits a function, a separate
"file router" agent inspects the function and the current file index, then
assigns it a file path. The router can create new directories/files as needed.

This produces an index mapping each agent's function to a file path, simulating
how a real codebase would be organized.

The file router agent sees:
- The submitted function code
- The current file index (what's been placed where so far)
- The contract (if any)
And decides: which file should this function live in?

## Experiment Results (2026-03-27)

Model: claude-haiku-4-5
Root task: analyze_text — takes a string, returns word_count, sentence_count,
most_common_word, average_word_length.
Max depth: 2

### Tree Structure

    analyze_text                                [src/text_analysis/analyzer.py]
      count_words(text: str) -> int             [text/analysis.py]
      count_sentences(text: str) -> int         [src/text_analysis/metrics.py]
      find_most_common_word(text: str) -> str   [text_analysis/word_frequency.py]
      calculate_average_word_length(text: str)   [src/text_analysis/statistics.py]

### File Index

    src/text_analysis/analyzer.py    -> analyze_text
    src/text_analysis/metrics.py     -> count_sentences
    src/text_analysis/statistics.py  -> calculate_average_word_length
    text/analysis.py                 -> count_words
    text_analysis/word_frequency.py  -> find_most_common_word

### Observations

- File router successfully assigned functions to different files based on purpose.
- Router saw the evolving index and grouped related functions (metrics, statistics).
- Inconsistent top-level dirs (text/ vs text_analysis/ vs src/text_analysis/) because
  each child's router call runs concurrently and the first few see an empty index.
  Fix: route children after all are collected, not inline during submission.
- 4 children spawned this time (vs 3 in experiment003) — each metric got its own agent.
- The project layout section groups code by file, showing what a real codebase would
  look like.
"""

from pathlib import Path
from dotenv import load_dotenv
import anthropic
import json
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from uuid import uuid4

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = anthropic.Anthropic()
executor = ThreadPoolExecutor(max_workers=8)

# Thread-safe file index
_index_lock = threading.Lock()
file_index: dict[str, list[str]] = {}  # file_path -> [function_name, ...]

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

TOOLS = [
    {
        "name": "spawn_child",
        "description": (
            "Spawn a child agent to implement a function according to a contract. "
            "This returns IMMEDIATELY with a task_id. The child runs in the background. "
            "You must call wait_for_child later to get the result. "
            "Spawn all your children first, then wait for them."
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
        "name": "wait_for_child",
        "description": (
            "Wait for a previously spawned child to finish. "
            "Returns success/failure."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "string",
                    "description": "The task_id returned by spawn_child.",
                },
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "wait_all",
        "description": (
            "Wait for ALL previously spawned children to finish. "
            "Returns a list of results (success/failure for each child)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "submit_function",
        "description": (
            "Submit the function you implemented. Call this exactly once, "
            "AFTER you have waited for all children. "
            "A file router agent will decide where to place this function."
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
You are a function implementer. You will be given a task or contract to implement.

You have four tools:
1. spawn_child(contract) - Spawn a child agent. Returns IMMEDIATELY with a task_id.
   The child runs in the background. Spawn ALL children first before waiting.
2. wait_for_child(task_id) - Wait for a single child to finish.
3. wait_all() - Wait for ALL pending children at once.
4. submit_function(function_code) - Submit your implementation. A file router will
   decide where to place your function in the project structure.

Workflow:
1. Decide what helper functions you need
2. spawn_child for each one (they run in parallel)
3. wait_all() OR wait_for_child for each task_id
4. submit_function with your code that calls the helpers

Rules:
- Only spawn children if decomposition makes sense.
- Do NOT spawn more than 3 children.
- Do NOT re-implement child functions in your submission.
- If a task is simple/atomic, just submit directly without spawning.
"""

FILE_ROUTER_SYSTEM = """\
You are a file router. Given a Python function and the current file index of the
project, decide which file this function should be placed in.

You can:
- Place it in an existing file if it logically belongs there
- Create a new file (and directories) if needed

Think about good project organization:
- Group related functions together
- Use descriptive directory/file names
- Follow Python conventions (snake_case files, logical module structure)
- Keep files focused — don't dump everything in one file

Respond with ONLY a JSON object: {"file_path": "path/to/file.py"}
Nothing else.
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


def route_function(function_name: str, function_code: str, contract: dict | None) -> str:
    """Ask the file router agent where to place this function."""
    with _index_lock:
        current_index = dict(file_index)

    index_str = json.dumps(current_index, indent=2) if current_index else "(empty — no files yet)"

    contract_str = ""
    if contract:
        contract_str = f"\n\nContract:\n{format_contract(contract)}"

    prompt = (
        f"Where should this function be placed?\n\n"
        f"Function name: {function_name}\n"
        f"```python\n{function_code}\n```"
        f"{contract_str}\n\n"
        f"Current file index:\n{index_str}"
    )

    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        system=FILE_ROUTER_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )

    text = next((b.text for b in response.content if b.type == "text"), "").strip()
    file_path = None

    # Try to parse JSON from the response (may be wrapped in markdown code block)
    for candidate in [text, text.strip("`").strip(), text.removeprefix("```json").removesuffix("```").strip()]:
        try:
            result = json.loads(candidate)
            file_path = result["file_path"]
            break
        except (json.JSONDecodeError, KeyError):
            continue

    if not file_path:
        # Fallback: extract path from text
        for line in text.split("\n"):
            if ".py" in line:
                file_path = line.strip().strip('"').strip("'")
                break
        else:
            file_path = f"src/{function_name}.py"

    # Update the index
    with _index_lock:
        if file_path not in file_index:
            file_index[file_path] = []
        file_index[file_path].append(function_name)

    safe_print(f"    [router] {function_name} -> {file_path}")
    return file_path


def run_agent(
    task: str,
    contract: dict | None = None,
    depth: int = 0,
    max_depth: int = 2,
) -> dict:
    indent = "  " * depth

    if contract:
        contract_str = format_contract(contract)
        fn_name = contract["function_name"]
        safe_print(f"{indent}[depth={depth}] Agent started: {fn_name}")
        user_prompt = f"Implement the following function according to this contract:\n\n{contract_str}"
    else:
        fn_name = "root"
        safe_print(f"{indent}[depth={depth}] Agent started: {task[:80]}")
        user_prompt = f"Generate a Python function for this task: {task}"

    tools = TOOLS if depth < max_depth else [TOOLS[3]]

    if depth >= max_depth:
        user_prompt += "\n\nIMPORTANT: You are at maximum depth. Just implement and submit directly."

    messages = [{"role": "user", "content": user_prompt}]

    children = []
    pending_futures: dict[str, tuple[Future, dict]] = {}
    my_function = None

    while True:
        response = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
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

                safe_print(f"{indent}  -> Spawning child (async): {child_name} [task_id={task_id}]")

                future = executor.submit(
                    run_agent,
                    task=child_name,
                    contract=child_contract,
                    depth=depth + 1,
                    max_depth=max_depth,
                )
                pending_futures[task_id] = (future, child_contract)

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps({
                        "task_id": task_id,
                        "message": f"Child '{child_name}' spawned. Use wait_for_child('{task_id}') or wait_all().",
                    }),
                })

            elif block.name == "wait_for_child":
                task_id = block.input["task_id"]

                if task_id not in pending_futures:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({
                            "success": False,
                            "message": f"Unknown task_id '{task_id}'.",
                        }),
                        "is_error": True,
                    })
                else:
                    future, child_contract = pending_futures[task_id]
                    child_name = child_contract["function_name"]
                    safe_print(f"{indent}  <- Waiting for child: {child_name} [task_id={task_id}]")

                    child_node = future.result()
                    children.append(child_node)

                    if child_node["function_code"] and child_node["function_code"] != "pass":
                        safe_print(f"{indent}  <- Child done: {child_name} [task_id={task_id}]")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({
                                "success": True,
                                "message": f"Child '{child_name}' finished successfully.",
                            }),
                        })
                    else:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({
                                "success": False,
                                "message": f"Child '{child_name}' failed.",
                            }),
                        })

                    del pending_futures[task_id]

            elif block.name == "wait_all":
                if not pending_futures:
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({
                            "results": [],
                            "message": "No pending children to wait for.",
                        }),
                    })
                else:
                    safe_print(f"{indent}  <- Waiting for all {len(pending_futures)} children...")
                    results_list = []
                    for tid, (future, child_contract) in list(pending_futures.items()):
                        child_name = child_contract["function_name"]
                        child_node = future.result()
                        children.append(child_node)

                        success = child_node["function_code"] and child_node["function_code"] != "pass"
                        safe_print(f"{indent}  <- Child done: {child_name} [task_id={tid}] ({'ok' if success else 'fail'})")
                        results_list.append({
                            "task_id": tid,
                            "function_name": child_name,
                            "success": success,
                        })

                    pending_futures.clear()
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps({
                            "results": results_list,
                            "message": f"All {len(results_list)} children finished.",
                        }),
                    })

            elif block.name == "submit_function":
                code = block.input["function_code"]
                extracted_name = fn_name
                for line in code.split("\n"):
                    if line.strip().startswith("def "):
                        extracted_name = line.strip().split("(")[0].replace("def ", "")
                        break

                # Route the function to a file via the file router agent
                assigned_path = route_function(extracted_name, code, contract)

                my_function = {
                    "function_code": code,
                    "function_name": extracted_name,
                    "file_path": assigned_path,
                }
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": f"Function submitted and routed to: {assigned_path}",
                })

        messages.append({"role": "user", "content": tool_results})

        if my_function is not None and response.stop_reason != "tool_use":
            break

        if my_function is not None:
            final = client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )
            break

    # Collect orphan children
    for task_id, (future, child_contract) in pending_futures.items():
        child_name = child_contract["function_name"]
        safe_print(f"{indent}  <- Collecting orphan child: {child_name} [task_id={task_id}]")
        child_node = future.result()
        children.append(child_node)

    if my_function is None:
        my_function = {"function_code": "pass", "function_name": fn_name, "file_path": "src/unknown.py"}

    actual_name = my_function.get("function_name", fn_name)
    node = {
        "function_name": actual_name,
        "function_code": my_function["function_code"],
        "file_path": my_function.get("file_path", "src/unknown.py"),
        "contract": contract,
        "children": children,
    }

    safe_print(f"{indent}[depth={depth}] Agent done: {actual_name}")
    return node


def post_order_collect(node: dict) -> list[dict]:
    result = []
    for child in node["children"]:
        result.extend(post_order_collect(child))
    result.append({
        "function_name": node["function_name"],
        "function_code": node["function_code"],
        "file_path": node.get("file_path"),
        "contract": node.get("contract"),
    })
    return result


def print_tree(node: dict, indent: int = 0) -> None:
    prefix = "  " * indent
    name = node["function_name"]
    file_path = node.get("file_path", "?")
    contract = node.get("contract")
    if contract:
        params = ", ".join(f"{p['name']}: {p['type']}" for p in contract.get("parameters", []))
        sig = f"{name}({params}) -> {contract['return_type']}"
        print(f"{prefix}{sig}  [{file_path}]")
    else:
        print(f"{prefix}{name}  [{file_path}]")
    for child in node["children"]:
        print_tree(child, indent + 1)


def main():
    root_task = (
        "Create a function called 'analyze_text' that takes a string and returns "
        "a dictionary with: word_count, sentence_count, most_common_word, "
        "and average_word_length. Break this into helper functions."
    )

    print("=" * 60)
    print("FILE-ROUTED ASYNC CONTRACT AGENT TREE")
    print("=" * 60)
    print(f"\nRoot task: {root_task}\n")

    tree = run_agent(root_task, depth=0, max_depth=2)

    print("\n" + "=" * 60)
    print("TREE STRUCTURE (with contracts + file paths)")
    print("=" * 60)
    print_tree(tree)

    print("\n" + "=" * 60)
    print("FILE INDEX")
    print("=" * 60)
    for path, funcs in sorted(file_index.items()):
        print(f"\n  {path}:")
        for fn in funcs:
            print(f"    - {fn}")

    print("\n" + "=" * 60)
    print("FUNCTIONS IN POST-ORDER")
    print("=" * 60)
    functions = post_order_collect(tree)
    for i, fn in enumerate(functions, 1):
        print(f"\n--- Function {i}: {fn['function_name']} -> {fn['file_path']} ---")
        if fn.get("contract"):
            print(f"Contract: {format_contract(fn['contract'])}")
            print()
        print(fn["function_code"])

    # Group by file
    print("\n" + "=" * 60)
    print("PROJECT LAYOUT")
    print("=" * 60)
    files: dict[str, list[str]] = {}
    for fn in functions:
        fp = fn["file_path"]
        if fp not in files:
            files[fp] = []
        files[fp].append(fn["function_code"])

    for fp, codes in sorted(files.items()):
        print(f"\n# ===== {fp} =====")
        print("\n\n".join(codes))

    executor.shutdown(wait=False)


if __name__ == "__main__":
    main()
