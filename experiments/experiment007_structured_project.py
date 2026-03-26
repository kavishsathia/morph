"""
Structured Project Experiment

Improvement over experiment006: both the generator agents and the router agent
are taught good abstraction and project structure principles. The generation
prompts emphasize single responsibility, clear module boundaries, and separation
of concerns. The router enforces a conventional Python project layout.

Also uses a more complex task to stress-test multi-file organization.

Phase 1: Generate with structure-aware agents.
Phase 2: Route + write with structure-aware router.

## Experiment Results (2026-03-27)

Model: claude-haiku-4-5
Root task: CLI tool 'textstat' — reads a text file, prints report with total
words, sentences, top 5 words, avg word length, Flesch-Kincaid readability.
Max depth: 2, 12 functions generated across 3-level tree.

### Project Layout

    src/textstat/
      __init__.py     — package init with __all__ exports and __version__
      main.py         — entry point, orchestrates the pipeline
      parsing.py      — argument parsing, sentence/word tokenization
      io.py           — file reading, report printing, help text
      statistics.py   — word frequency, avg length, Flesch-Kincaid
      analysis.py     — syllable estimation, FK formula, top words

### File Index

    __init__.py   -> (package exports)
    main.py       -> main
    parsing.py    -> parse_arguments, analyze_text, validate_arguments,
                     extract_file_path, tokenize_sentences, tokenize_and_clean_words
    io.py         -> read_file, print_report, print_help
    statistics.py -> compute_statistics
    analysis.py   -> estimate_syllables, calculate_flesch_kincaid, get_top_words

### Observations

- 5 separate files with clear single responsibilities — big improvement over
  experiment006's single file output.
- __init__.py with proper __all__ exports and relative imports in main.py.
- module_hint drove the router: parsing hints -> parsing.py, io -> io.py,
  core -> analysis.py/statistics.py.
- 12 functions across a 3-level tree with parallel execution at every level.
- analysis.py vs statistics.py split is a bit arbitrary — both are "core"
  computation. Router created analysis.py on its own when it decided
  statistics.py was getting too focused on one function.
- Some redundancy in parsing.py (validate_arguments, extract_file_path alongside
  parse_arguments) — generator over-decomposed argument parsing.
- Bug persists: root agent names itself after first def in submitted code,
  not the actual entry point function.
"""

from pathlib import Path
from dotenv import load_dotenv
import anthropic
import json
import os
import tempfile
import threading
from collections import deque
from concurrent.futures import Future, ThreadPoolExecutor
from uuid import uuid4

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = anthropic.Anthropic()
executor = ThreadPoolExecutor(max_workers=8)

# ──────────────────────────────────────────────
# Phase 1: Generation (structure-aware)
# ──────────────────────────────────────────────

CONTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "function_name": {"type": "string"},
        "description": {"type": "string"},
        "module_hint": {
            "type": "string",
            "description": "Suggested module/layer this belongs to (e.g. 'parsing', 'models', 'io', 'core'). Helps the router.",
        },
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
You are a function implementer who writes well-structured, modular Python code.

Tools: spawn_child(contract), wait_for_child(task_id), wait_all(), submit_function(code).

Workflow: spawn children -> wait -> submit your code (calling children by name).

Design principles — follow these when deciding how to decompose:
- Single Responsibility: each function does ONE thing well.
- Separation of Concerns: separate I/O from logic, parsing from processing,
  data models from business logic.
- Clean Interfaces: functions take explicit typed parameters, not god-objects.
  Return specific types, not untyped dicts where a dataclass would be clearer.
- Appropriate Abstraction: don't over-decompose trivial tasks (a 3-line function
  doesn't need a child). Don't under-decompose complex ones.
- Module Hints: when spawning a child, include a module_hint in the contract
  (e.g. "parsing", "models", "io", "core", "utils") to help the router group
  related code. Think about which layer this function belongs to.

Rules:
- Max 4 children per agent.
- Don't re-implement children in your submission.
- Keep functions focused and concise.
- Use type hints and docstrings.
- If a task is atomic, just submit directly.
"""

_print_lock = threading.Lock()


def safe_print(msg: str):
    with _print_lock:
        print(msg)


def format_contract(contract: dict) -> str:
    params = ", ".join(f"{p['name']}: {p['type']}" for p in contract.get("parameters", []))
    sig = f"def {contract['function_name']}({params}) -> {contract['return_type']}"
    lines = [f"  Signature: {sig}", f"  Description: {contract['description']}"]
    if contract.get("module_hint"):
        lines.append(f"  Module hint: {contract['module_hint']}")
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
        user_prompt += "\n\nMax depth reached. Implement and submit directly."

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
                module_hint = child_contract.get("module_hint", "")
                task_id = str(uuid4())[:8]
                hint_str = f" (module: {module_hint})" if module_hint else ""
                safe_print(f"{indent}  -> Spawning: {child_name}{hint_str} [{task_id}]")
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
    return {
        "function_name": actual_name,
        "function_code": my_function["function_code"],
        "contract": contract,
        "children": children,
    }


# ──────────────────────────────────────────────
# Phase 2: Filesystem routing (structure-aware)
# ──────────────────────────────────────────────

ROUTER_TOOLS = [
    {
        "name": "read_file",
        "description": "Read a file's contents. Returns error if not found.",
        "input_schema": {
            "type": "object",
            "properties": {"file_path": {"type": "string", "description": "Relative path from project root"}},
            "required": ["file_path"],
        },
    },
    {
        "name": "append_to_file",
        "description": "Append content to a file. Creates file and directories if needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["file_path", "content"],
        },
    },
    {
        "name": "replace_text",
        "description": "Replace a string in a file. Fails if old_text not found.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "old_text": {"type": "string"},
                "new_text": {"type": "string"},
            },
            "required": ["file_path", "old_text", "new_text"],
        },
    },
    {
        "name": "assign_file",
        "description": "Register this function in the index. Call ONCE per function.",
        "input_schema": {
            "type": "object",
            "properties": {
                "function_name": {"type": "string"},
                "file_path": {"type": "string"},
            },
            "required": ["function_name", "file_path"],
        },
    },
    {
        "name": "done",
        "description": "Signal you are done placing this function.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

ROUTER_SYSTEM = """\
You are a project architect routing Python functions into a well-structured project.

For each function:
1. assign_file — register it in the index
2. Write it to disk using read_file, append_to_file, replace_text
3. Add proper imports where needed
4. Call done

Project structure rules:
- Use a clear package layout:
    src/
      <package_name>/
        __init__.py        (can be empty, but must exist for each package)
        models.py          (data classes, type definitions)
        parsing.py         (input parsing, text processing, tokenization)
        analysis.py        (core analysis/business logic)
        statistics.py      (numerical computations, aggregations)
        utils.py           (small shared helpers that don't fit elsewhere)
        io.py              (file I/O, formatting output)
        main.py            (entry points, orchestration, public API)

- Respect module_hint from contracts — it tells you which layer the function belongs to.
- Group functions by RESPONSIBILITY, not by who called them.
  Example: a parsing function used by the main entry point still goes in parsing.py.
- Each file should have a clear, single purpose. If a file is getting too many
  unrelated functions, split it.
- Add imports at the top of files. Use relative imports within the package
  (e.g. from .parsing import tokenize).
- Create __init__.py files for packages. Export the public API from __init__.py.
- Don't put everything in one file. Spread across at least 2-3 files for
  non-trivial projects.
- Read existing file content before appending to stay consistent.
"""


def execute_router_tool(tool_name: str, tool_input: dict, project_root: str,
                        file_index: dict[str, list[str]], assignments: dict[str, str]) -> str:
    if tool_name == "read_file":
        fpath = os.path.join(project_root, tool_input["file_path"])
        if os.path.isdir(fpath):
            files = os.listdir(fpath)
            return f"'{tool_input['file_path']}' is a directory containing: {files}"
        if os.path.exists(fpath):
            with open(fpath) as f:
                content = f.read()
            return content if content else "(empty file)"
        return f"Error: '{tool_input['file_path']}' does not exist."

    elif tool_name == "append_to_file":
        if "content" not in tool_input:
            return "Error: missing 'content' parameter."
        fpath = os.path.join(project_root, tool_input["file_path"])
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "a") as f:
            f.write(tool_input["content"])
        return f"Appended to {tool_input['file_path']}."

    elif tool_name == "replace_text":
        fpath = os.path.join(project_root, tool_input["file_path"])
        if not os.path.exists(fpath):
            return f"Error: '{tool_input['file_path']}' does not exist."
        if "old_text" not in tool_input or "new_text" not in tool_input:
            return "Error: missing 'old_text' or 'new_text' parameter."
        with open(fpath) as f:
            content = f.read()
        if tool_input["old_text"] not in content:
            return f"Error: old_text not found in '{tool_input['file_path']}'."
        content = content.replace(tool_input["old_text"], tool_input["new_text"], 1)
        with open(fpath, "w") as f:
            f.write(content)
        return f"Replaced in {tool_input['file_path']}."

    elif tool_name == "assign_file":
        fn_name = tool_input["function_name"]
        fp = tool_input["file_path"]
        assignments[fn_name] = fp
        file_index.setdefault(fp, []).append(fn_name)
        return f"Indexed: {fn_name} -> {fp}"

    elif tool_name == "done":
        return "Done."

    return f"Unknown tool: {tool_name}"


def route_all_functions(queue: deque[dict], project_root: str) -> dict[str, str]:
    file_index: dict[str, list[str]] = {}
    assignments: dict[str, str] = {}

    print(f"\n[Router] Writing to: {project_root}")

    while queue:
        fn = queue.popleft()
        fn_name = fn["function_name"]
        fn_code = fn["function_code"]
        contract = fn.get("contract")

        index_str = json.dumps(file_index, indent=2) if file_index else "(empty)"
        contract_str = f"\n\nContract:\n{format_contract(contract)}" if contract else ""
        module_hint = contract.get("module_hint", "") if contract else ""
        hint_str = f"\nModule hint: {module_hint}" if module_hint else ""

        prompt = (
            f"Place this function in the project:\n\n"
            f"Function: {fn_name}{hint_str}\n"
            f"```python\n{fn_code}\n```"
            f"{contract_str}\n\n"
            f"Current index:\n{index_str}\n\n"
            f"Remaining: {len(queue)} functions"
        )

        messages = [{"role": "user", "content": prompt}]
        done = False

        while not done:
            response = client.messages.create(
                model="claude-haiku-4-5", max_tokens=2048,
                system=ROUTER_SYSTEM, tools=ROUTER_TOOLS, messages=messages,
            )
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            if not tool_use_blocks:
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


def print_tree(node: dict, assignments: dict[str, str], indent: int = 0) -> None:
    prefix = "  " * indent
    name = node["function_name"]
    path = assignments.get(name, "?")
    contract = node.get("contract")
    hint = ""
    if contract and contract.get("module_hint"):
        hint = f" (hint: {contract['module_hint']})"
    if contract:
        params = ", ".join(f"{p['name']}: {p['type']}" for p in contract.get("parameters", []))
        sig = f"{name}({params}) -> {contract['return_type']}"
        print(f"{prefix}{sig}{hint}  [{path}]")
    else:
        print(f"{prefix}{name}  [{path}]")
    for child in node["children"]:
        print_tree(child, assignments, indent + 1)


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    root_task = (
        "Create a CLI tool called 'textstat' that reads a text file and prints a "
        "report with: total words, total sentences, top 5 most common words, "
        "average word length, and a readability score (Flesch-Kincaid). "
        "The tool should accept a file path as a command-line argument. "
        "Break this into well-organized modules: argument parsing, file I/O, "
        "text analysis, statistics, and the main entry point."
    )

    project_root = tempfile.mkdtemp(prefix="morph_exp007_")

    print("=" * 60)
    print("STRUCTURED PROJECT EXPERIMENT")
    print("=" * 60)
    print(f"\nRoot task: {root_task}")
    print(f"Project root: {project_root}\n")

    # Phase 1
    print("--- Phase 1: Generate ---\n")
    tree = run_agent(root_task, depth=0, max_depth=2)

    # Phase 2
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

    print("\n" + "=" * 60)
    print(f"FILES ON DISK ({project_root})")
    print("=" * 60)
    for dirpath, _, filenames in os.walk(project_root):
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
