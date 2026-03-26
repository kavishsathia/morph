"""
Async Contract-Based Recursive Agent Tree Experiment

Improvement over experiment002: spawning a child is non-blocking. The parent gets
back a task_id immediately and can spawn multiple children concurrently. It then
calls wait_for_child(task_id) or wait_all() to collect results. Children run in
parallel threads.

Tools:
- spawn_child(contract) -> returns {"task_id": "..."} immediately
- wait_for_child(task_id) -> blocks until child is done, returns success/failure
- wait_all() -> blocks until all pending children are done
- submit_function(function_code) -> submit the parent's own implementation

## Experiment Results (2026-03-27)

Model: claude-haiku-4-5
Root task: analyze_text — takes a string, returns word_count, sentence_count,
most_common_word, average_word_length.
Max depth: 2

### Tree Structure (with contracts)

    analyze_text
      count_words(text: str) -> int
      count_sentences(text: str) -> int
      analyze_words(text: str) -> tuple

### Post-Order Output

    1. count_words
    2. count_sentences
    3. analyze_words
    4. analyze_text

### Observations

- Agent used wait_all() to collect all 3 children at once (not wait_for_child).
- All 3 children ran concurrently — interleaved log output confirms parallel execution.
- Clean output, no duplication, valid combined module.
- Agent bundled most_common_word and average_word_length into a single
  analyze_words(text) -> tuple child, rather than spawning separate children.
  This is a reasonable design choice the model made on its own.
- Compared to experiment002: same contract-based interface quality, but children
  run in parallel instead of sequentially. The model naturally adopted the
  spawn-all-then-wait pattern as instructed.
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
            "Returns success/failure. You should wait for all children "
            "before submitting your own function."
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
            "Returns a list of results (success/failure for each child). "
            "Use this instead of calling wait_for_child multiple times."
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
You are a function implementer. You will be given a task or contract to implement.

You have four tools:
1. spawn_child(contract) - Spawn a child agent. Returns IMMEDIATELY with a task_id.
   The child runs in the background. Spawn ALL children first before waiting.
2. wait_for_child(task_id) - Wait for a single child to finish. Returns success/failure.
3. wait_all() - Wait for ALL pending children at once. Returns a list of results.
   Use this when you want to wait for everything.
4. submit_function(function_code) - Submit your implementation.

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

# Thread-safe print
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

    # At max depth, only submit
    tools = TOOLS if depth < max_depth else [TOOLS[3]]  # submit_function only

    if depth >= max_depth:
        user_prompt += "\n\nIMPORTANT: You are at maximum depth. Just implement and submit directly."

    messages = [{"role": "user", "content": user_prompt}]

    children = []
    pending_futures: dict[str, tuple[Future, dict]] = {}  # task_id -> (future, contract)
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

                # Launch child in background thread
                future = executor.submit(
                    run_agent,
                    task=child_name,
                    contract=child_contract,
                    depth=depth + 1,
                    max_depth=max_depth,
                )
                pending_futures[task_id] = (future, child_contract)

                # Return immediately with task_id
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps({
                        "task_id": task_id,
                        "message": f"Child '{child_name}' spawned. Use wait_for_child('{task_id}') to get the result.",
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

                    # Block until child finishes
                    child_node = future.result()
                    children.append(child_node)

                    if child_node["function_code"] and child_node["function_code"] != "pass":
                        safe_print(f"{indent}  <- Child done: {child_name} [task_id={task_id}]")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps({
                                "success": True,
                                "message": f"Child '{child_name}' finished successfully. You can call it with the contract signature.",
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
                            "message": f"All {len(results_list)} children finished. You can call them by their contract names.",
                        }),
                    })

            elif block.name == "submit_function":
                code = block.input["function_code"]
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
                system=SYSTEM_PROMPT,
                tools=tools,
                messages=messages,
            )
            break

    # Wait for any children that were never waited on
    for task_id, (future, child_contract) in pending_futures.items():
        child_name = child_contract["function_name"]
        safe_print(f"{indent}  <- Collecting orphan child: {child_name} [task_id={task_id}]")
        child_node = future.result()
        children.append(child_node)

    if my_function is None:
        my_function = {"function_code": "pass", "function_name": fn_name}

    actual_name = my_function.get("function_name", fn_name)
    node = {
        "function_name": actual_name,
        "function_code": my_function["function_code"],
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
        "contract": node.get("contract"),
    })
    return result


def print_tree(node: dict, indent: int = 0) -> None:
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
    print("ASYNC CONTRACT-BASED RECURSIVE AGENT TREE")
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

    print("\n" + "=" * 60)
    print("COMBINED MODULE")
    print("=" * 60)
    combined = "\n\n".join(fn["function_code"] for fn in functions)
    print(combined)

    executor.shutdown(wait=False)


if __name__ == "__main__":
    main()
