"""
React Agent Tree Experiment (Sonnet)

Specialized for React/TypeScript. The agent tree mirrors the component tree.
Contracts contain both a props interface (TypeScript types) and behavioral
descriptions (state, effects, event handling, rendering logic).

The router places components, hooks, utils, and types into a conventional
React project layout.

Phase 1: Generate React components/hooks via contract-based agent tree.
Phase 2: Route + write to disk with React-aware file router.

Same as experiment008 but using claude-sonnet-4-6 instead of claude-haiku-4-5
to compare output quality.

## Experiment Results (2026-03-27)

Model: claude-sonnet-4-6
Root task: Product dashboard with search, sort, product cards, loading spinner,
custom hook, TypeScript types, mock data.
Max depth: 2, 8 modules (no duplicates).

### Project Layout

    src/
      App.tsx                                            — root (stub — bug)
      types/ProductTypes.ts                              — Product, SortField, SortOrder, SortConfig
      utils/mockProducts.ts                              — 12 products + fetchProducts() with delay
      hooks/useProducts.ts                               — search + sort with useMemo, effect cancellation
      components/
        ProductCard/ProductCard.tsx + index.ts            — image, stars, category badge, add-to-cart
        SearchBar/SearchBar.tsx + index.ts                — search icon, clear button
        SortControls/SortControls.tsx + index.ts          — 3 sort fields, asc/desc toggle arrows
        LoadingSpinner/LoadingSpinner.tsx + index.ts      — animated spinner with message

### Comparison with Haiku (experiment008)

    | Metric          | Haiku (exp008) | Sonnet (exp009) |
    |-----------------|----------------|-----------------|
    | Modules         | 15 (dupes)     | 8 (clean)       |
    | Tree depth used | 2 (re-spawned) | 1 (flat, smart) |
    | Types           | Basic Product  | 6 types/aliases |
    | Mock data       | 10 products    | 12 + async fetch|
    | Hook quality    | 2 conflicting  | 1 clean, useMemo|
    | Component UX    | Basic          | Icons, stars, hover effects |

### Observations

- Sonnet didn't re-spawn components that already existed — no duplicates.
- Richer type system: SortField, SortOrder, SortConfig, UseProductsReturn.
- Hook uses useMemo for filtered/sorted products, cancellation in useEffect.
- Components have significantly more polish: SVG icons, clear button, star
  ratings, category badges, hover animations, add-to-cart buttons.
- Bug: App.tsx is a stub (<></>) — root agent didn't wire up ProductDashboard.
  The root submitted its code before spawning the dashboard component.
- Router read files before writing to check for existing content — no dupes.
- Flat tree (depth 1 only) because Sonnet made better decomposition decisions
  and didn't need sub-decomposition.
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
# Phase 1: React generation
# ──────────────────────────────────────────────

CONTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string",
            "description": "Component or hook name, e.g. 'FilterPanel', 'useSearch'.",
        },
        "kind": {
            "type": "string",
            "enum": ["component", "hook", "util", "type"],
            "description": "What kind of module this is.",
        },
        "props_interface": {
            "type": "string",
            "description": (
                "TypeScript interface for the props/arguments. "
                "Write as a full interface block, e.g.:\n"
                "interface FilterPanelProps {\n"
                "  filters: Filter[];\n"
                "  onFilterChange: (filters: Filter[]) => void;\n"
                "}"
            ),
        },
        "behavior": {
            "type": "string",
            "description": (
                "Detailed behavioral specification. Describe:\n"
                "- What state this manages (useState)\n"
                "- What effects it runs (useEffect)\n"
                "- What events it handles and how\n"
                "- Conditional rendering logic\n"
                "- How it composes children\n"
                "- Any data transformations or computations"
            ),
        },
        "module_hint": {
            "type": "string",
            "description": "Where this belongs: 'components', 'hooks', 'utils', 'types', 'context', 'services'.",
        },
    },
    "required": ["name", "kind", "props_interface", "behavior"],
}

GEN_TOOLS = [
    {
        "name": "spawn_child",
        "description": (
            "Spawn a child agent to implement a React component, hook, util, or type. "
            "Define a contract with props_interface (TypeScript types) and behavior "
            "(state, effects, events, rendering). Returns immediately with task_id."
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
        "name": "submit_code",
        "description": (
            "Submit your React component/hook/util/type implementation. "
            "Only YOUR code — import children by name, don't re-implement them."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"code": {"type": "string"}},
            "required": ["code"],
        },
    },
]

GEN_SYSTEM = """\
You are a senior React/TypeScript developer. You implement components, hooks,
utilities, and types according to contracts.

Tools: spawn_child(contract), wait_for_child(task_id), wait_all(), submit_code(code).

Workflow: decompose into children -> spawn them -> wait -> submit your code.

When defining contracts for children, include BOTH:
1. props_interface — the full TypeScript interface (props for components, args for hooks)
2. behavior — detailed behavioral spec: state management, effects, event handling,
   conditional rendering, data transformations, how it composes its own children.

React principles:
- Composition over inheritance. Break UI into focused, reusable components.
- Lift state up only when needed. Keep state as local as possible.
- Extract custom hooks for reusable stateful logic (data fetching, filtering, etc.).
- Extract shared types into dedicated type files.
- Components should be presentational where possible; push logic into hooks.
- Use TypeScript strictly — no `any`, proper generics where useful.
- Keep components under ~80 lines. If bigger, decompose further.

Rules:
- Max 4 children per agent.
- Don't re-implement children — import them by name.
- Use proper React patterns: functional components, hooks, proper key props.
- If a task is simple (a small presentational component), just submit directly.
"""

_print_lock = threading.Lock()


def safe_print(msg: str):
    with _print_lock:
        print(msg)


def format_contract(contract: dict) -> str:
    lines = [
        f"  Name: {contract['name']}",
        f"  Kind: {contract.get('kind', 'component')}",
    ]
    if contract.get("props_interface"):
        lines.append(f"  Props interface:\n    {contract['props_interface']}")
    if contract.get("behavior"):
        lines.append(f"  Behavior:\n    {contract['behavior']}")
    if contract.get("module_hint"):
        lines.append(f"  Module hint: {contract['module_hint']}")
    return "\n".join(lines)


def run_agent(task: str, contract: dict | None = None, depth: int = 0, max_depth: int = 2) -> dict:
    indent = "  " * depth
    if contract:
        name = contract["name"]
        kind = contract.get("kind", "component")
        safe_print(f"{indent}[depth={depth}] Agent started: {name} ({kind})")
        user_prompt = f"Implement this {kind} according to the contract:\n\n{format_contract(contract)}"
    else:
        name = "root"
        safe_print(f"{indent}[depth={depth}] Agent started: {task[:80]}")
        user_prompt = f"Build this React application: {task}"

    tools = GEN_TOOLS if depth < max_depth else [GEN_TOOLS[3]]
    if depth >= max_depth:
        user_prompt += "\n\nMax depth. Implement and submit directly."

    messages = [{"role": "user", "content": user_prompt}]
    children = []
    pending_futures: dict[str, tuple[Future, dict]] = {}
    my_code = None

    while True:
        response = client.messages.create(
            model="claude-sonnet-4-6", max_tokens=4096, system=GEN_SYSTEM,
            tools=tools, messages=messages,
        )
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if response.stop_reason == "end_turn" and not tool_use_blocks:
            if my_code is None:
                text = next((b.text for b in response.content if b.type == "text"), "")
                my_code = text
            break
        if not tool_use_blocks:
            break

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for block in tool_use_blocks:
            if block.name == "spawn_child":
                child_contract = block.input["contract"]
                child_name = child_contract["name"]
                child_kind = child_contract.get("kind", "component")
                module_hint = child_contract.get("module_hint", "")
                task_id = str(uuid4())[:8]
                hint_str = f" -> {module_hint}" if module_hint else ""
                safe_print(f"{indent}  -> Spawning: {child_name} ({child_kind}{hint_str}) [{task_id}]")
                future = executor.submit(run_agent, child_name, child_contract, depth + 1, max_depth)
                pending_futures[task_id] = (future, child_contract)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"task_id": task_id})})

            elif block.name == "wait_for_child":
                task_id = block.input["task_id"]
                if task_id not in pending_futures:
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"success": False}), "is_error": True})
                else:
                    future, cc = pending_futures.pop(task_id)
                    safe_print(f"{indent}  <- Waiting: {cc['name']}")
                    child_node = future.result()
                    children.append(child_node)
                    safe_print(f"{indent}  <- Done: {cc['name']}")
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"success": True})})

            elif block.name == "wait_all":
                safe_print(f"{indent}  <- Waiting for all {len(pending_futures)} children...")
                results_list = []
                for tid, (future, cc) in list(pending_futures.items()):
                    child_node = future.result()
                    children.append(child_node)
                    safe_print(f"{indent}  <- Done: {cc['name']}")
                    results_list.append({"name": cc["name"], "success": True})
                pending_futures.clear()
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"results": results_list})})

            elif block.name == "submit_code":
                my_code = block.input.get("code", block.input.get("function_code", "// empty"))
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": "Submitted."})

        messages.append({"role": "user", "content": tool_results})
        if my_code is not None and response.stop_reason != "tool_use":
            break
        if my_code is not None:
            client.messages.create(model="claude-sonnet-4-6", max_tokens=1024, system=GEN_SYSTEM, tools=tools, messages=messages)
            break

    for tid, (future, cc) in pending_futures.items():
        children.append(future.result())
    if my_code is None:
        my_code = "// empty"

    safe_print(f"{indent}[depth={depth}] Agent done: {name}")
    return {
        "name": name,
        "kind": contract.get("kind", "component") if contract else "component",
        "code": my_code,
        "contract": contract,
        "children": children,
    }


# ──────────────────────────────────────────────
# Phase 2: React-aware filesystem routing
# ──────────────────────────────────────────────

ROUTER_TOOLS = [
    {
        "name": "read_file",
        "description": "Read a file's contents.",
        "input_schema": {
            "type": "object",
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"],
        },
    },
    {
        "name": "append_to_file",
        "description": "Append content to a file. Creates file and directories if needed.",
        "input_schema": {
            "type": "object",
            "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["file_path", "content"],
        },
    },
    {
        "name": "replace_text",
        "description": "Replace text in a file.",
        "input_schema": {
            "type": "object",
            "properties": {"file_path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}},
            "required": ["file_path", "old_text", "new_text"],
        },
    },
    {
        "name": "assign_file",
        "description": "Register this module in the index. Call ONCE per module.",
        "input_schema": {
            "type": "object",
            "properties": {"name": {"type": "string"}, "file_path": {"type": "string"}},
            "required": ["name", "file_path"],
        },
    },
    {
        "name": "done",
        "description": "Signal you are done placing this module.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

ROUTER_SYSTEM = """\
You are a React project architect routing TypeScript modules into a well-structured project.

For each module:
1. assign_file — register it in the index
2. Write it to disk using read_file, append_to_file, replace_text
3. Call done

React project structure rules:
    src/
      components/
        ComponentName/
          ComponentName.tsx       (one component per file)
          index.ts                (barrel export)
      hooks/
        useHookName.ts            (one hook per file)
      utils/
        utilName.ts               (utility functions)
      types/
        index.ts                  (shared type definitions)
      context/
        ContextName.tsx           (React context providers)
      services/
        serviceName.ts            (API calls, data fetching)
      App.tsx                     (root component)

Rules:
- One component per file. File name matches component name.
- Each component folder gets an index.ts barrel: export { default } from './ComponentName';
- Hooks go in src/hooks/useXxx.ts — one hook per file.
- Shared types go in src/types/index.ts or src/types/modelName.ts.
- Respect the module_hint from the contract.
- Use .tsx for files with JSX, .ts for pure logic/types.
- Add proper imports at the top of each file. Use relative paths.
- Read files before writing to avoid duplicating content.
"""


def execute_router_tool(tool_name: str, tool_input: dict, project_root: str,
                        file_index: dict[str, list[str]], assignments: dict[str, str]) -> str:
    if tool_name == "read_file":
        fpath = os.path.join(project_root, tool_input["file_path"])
        if os.path.isdir(fpath):
            return f"'{tool_input['file_path']}' is a directory: {os.listdir(fpath)}"
        if os.path.exists(fpath):
            with open(fpath) as f:
                content = f.read()
            return content if content else "(empty file)"
        return f"File '{tool_input['file_path']}' does not exist."

    elif tool_name == "append_to_file":
        if "content" not in tool_input:
            return "Error: missing 'content' parameter."
        fpath = os.path.join(project_root, tool_input["file_path"])
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "a") as f:
            f.write(tool_input["content"])
        return f"Appended to {tool_input['file_path']}."

    elif tool_name == "replace_text":
        if "old_text" not in tool_input or "new_text" not in tool_input:
            return "Error: missing 'old_text' or 'new_text'."
        fpath = os.path.join(project_root, tool_input["file_path"])
        if not os.path.exists(fpath):
            return f"Error: '{tool_input['file_path']}' does not exist."
        with open(fpath) as f:
            content = f.read()
        if tool_input["old_text"] not in content:
            return f"Error: old_text not found in '{tool_input['file_path']}'."
        content = content.replace(tool_input["old_text"], tool_input["new_text"], 1)
        with open(fpath, "w") as f:
            f.write(content)
        return f"Replaced in {tool_input['file_path']}."

    elif tool_name == "assign_file":
        name = tool_input["name"]
        fp = tool_input["file_path"]
        assignments[name] = fp
        file_index.setdefault(fp, []).append(name)
        return f"Indexed: {name} -> {fp}"

    elif tool_name == "done":
        return "Done."

    return f"Unknown tool: {tool_name}"


def route_all_modules(queue: deque[dict], project_root: str) -> dict[str, str]:
    file_index: dict[str, list[str]] = {}
    assignments: dict[str, str] = {}

    print(f"\n[Router] Writing to: {project_root}")

    while queue:
        mod = queue.popleft()
        name = mod["name"]
        kind = mod.get("kind", "component")
        code = mod["code"]
        contract = mod.get("contract")

        index_str = json.dumps(file_index, indent=2) if file_index else "(empty)"
        contract_str = f"\n\nContract:\n{format_contract(contract)}" if contract else ""
        module_hint = contract.get("module_hint", "") if contract else ""
        hint_str = f"\nModule hint: {module_hint}" if module_hint else ""

        prompt = (
            f"Place this {kind} in the project:\n\n"
            f"Name: {name}\nKind: {kind}{hint_str}\n"
            f"```tsx\n{code}\n```"
            f"{contract_str}\n\n"
            f"Current index:\n{index_str}\n\n"
            f"Remaining: {len(queue)} modules"
        )

        messages = [{"role": "user", "content": prompt}]
        done = False

        while not done:
            response = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=2048,
                system=ROUTER_SYSTEM, tools=ROUTER_TOOLS, messages=messages,
            )
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            if not tool_use_blocks:
                messages.append({"role": "assistant", "content": response.content})
                messages.append({"role": "user", "content": "Please use the tools to assign and write this module."})
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
    result = [{"name": node["name"], "kind": node.get("kind", "component"), "code": node["code"], "contract": node.get("contract")}]
    for child in node["children"]:
        result.extend(pre_order_collect(child))
    return result


def print_tree(node: dict, assignments: dict[str, str], indent: int = 0) -> None:
    prefix = "  " * indent
    name = node["name"]
    kind = node.get("kind", "component")
    path = assignments.get(name, "?")
    contract = node.get("contract")
    hint = ""
    if contract and contract.get("module_hint"):
        hint = f" -> {contract['module_hint']}"
    print(f"{prefix}{name} ({kind}{hint})  [{path}]")
    for child in node["children"]:
        print_tree(child, assignments, indent + 1)


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    root_task = (
        "Build a React dashboard that displays a list of products. Features:\n"
        "- A search bar that filters products by name in real time\n"
        "- Sort buttons to sort by name, price, or rating\n"
        "- A product card component showing name, price, rating, and an image\n"
        "- A loading spinner while data is being fetched\n"
        "- Use a custom hook for the data fetching and filtering logic\n"
        "- TypeScript types for the Product model\n"
        "- The product data can be hardcoded as mock data in a utils file"
    )

    project_root = tempfile.mkdtemp(prefix="morph_exp009_")

    print("=" * 60)
    print("REACT AGENT TREE EXPERIMENT (SONNET)")
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
    print(f"\nQueue ({len(queue)} modules): {[m['name'] for m in queue]}")
    assignments = route_all_modules(queue, project_root)

    # Results
    print("\n" + "=" * 60)
    print("COMPONENT TREE")
    print("=" * 60)
    print_tree(tree, assignments)

    print("\n" + "=" * 60)
    print("FILE INDEX")
    print("=" * 60)
    index: dict[str, list[str]] = {}
    for name, path in assignments.items():
        index.setdefault(path, []).append(name)
    for path, names in sorted(index.items()):
        print(f"\n  {path}:")
        for n in names:
            print(f"    - {n}")

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
