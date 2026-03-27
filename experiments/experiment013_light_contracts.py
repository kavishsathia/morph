"""
Light Contracts React Agent Tree Experiment

Improvement over experiment012: contracts are lightweight. Instead of the parent
writing full TypeScript interfaces and multi-paragraph behavioral specs as JSON
strings, it writes a short natural language spec. The child is smart enough to
turn that into proper TypeScript.

Contract = name + kind + file_path + spec (a few sentences).

This should cut root agent output tokens and let it spawn all children faster,
ideally in a single batch.

## Experiment Results (2026-03-27)

Model: claude-sonnet-4-6
Root task: Product dashboard (same as exp008-012).
9 agents, 44 API calls, 200K tokens.

### Timing Summary

    Total wall clock:     130s
    Total API calls:      44
    Total tokens:         200,096 (186K in, 14K out)

### Agent Timings

    root             129.5s  (110s API, 19s waiting, 16 calls)
    mockProducts      28.8s  (6 calls)
    ProductCard       21.1s  (4 calls)
    ProductGrid       19.0s  (5 calls)
    SortControls      14.9s  (3 calls)
    useProducts        9.5s  (2 calls)
    LoadingSpinner     7.8s  (3 calls)
    SearchBar          7.5s  (3 calls)
    Product types      4.5s  (2 calls)

### Comparison

    | Metric         | Exp012 heavy | Exp013 light |
    |----------------|--------------|--------------|
    | Wall clock     | 188s         | 130s (-31%)  |
    | API calls      | 58           | 44 (-24%)    |
    | Tokens         | 300K         | 200K (-33%)  |
    | Root API calls | 27           | 16 (-41%)    |
    | Root wait time | 56s          | 19s (-66%)   |

### Key Findings

- Light contracts cut 31% off wall clock and 33% off tokens.
- Root went from 27 to 16 API calls — shorter contracts = faster spawning.
- Root wait time dropped from 56s to 19s — children finish faster relative
  to root because root spawns them sooner.
- Children average ~15s each, all running in parallel.
- The spec field is enough — children figure out TypeScript types on their own.

### Full progression

    Exp010 (sequential):      356s  247K tokens
    Exp011 (pipelined):       361s  393K tokens
    Exp012 (self-routing):    188s  300K tokens
    Exp013 (light contracts): 130s  200K tokens
"""

from pathlib import Path
from dotenv import load_dotenv
import anthropic
import json
import os
import tempfile
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from uuid import uuid4

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = anthropic.Anthropic()
executor = ThreadPoolExecutor(max_workers=8)

# ──────────────────────────────────────────────
# Timing
# ──────────────────────────────────────────────

@dataclass
class AgentTiming:
    name: str
    kind: str
    depth: int
    start: float = 0.0
    end: float = 0.0
    api_calls: list[float] = field(default_factory=list)
    wait_time: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total(self) -> float:
        return self.end - self.start

    @property
    def api_total(self) -> float:
        return sum(self.api_calls)

    @property
    def own_work(self) -> float:
        return self.total - self.wait_time


_timings_lock = threading.Lock()
agent_timings: list[AgentTiming] = []

# Shared index (for reporting only — agents don't read this)
_index_lock = threading.Lock()
file_index: dict[str, list[str]] = {}

_print_lock = threading.Lock()


def safe_print(msg: str):
    with _print_lock:
        print(msg)


# ──────────────────────────────────────────────
# Filesystem tools (available to all agents)
# ──────────────────────────────────────────────

def execute_fs_tool(tool_name: str, tool_input: dict, project_root: str) -> str:
    if tool_name == "read_file":
        fpath = os.path.join(project_root, tool_input["file_path"])
        if os.path.isdir(fpath):
            return f"Directory: {os.listdir(fpath)}"
        if os.path.exists(fpath):
            with open(fpath) as f:
                return f.read() or "(empty)"
        return f"Not found: {tool_input['file_path']}"

    elif tool_name == "append_to_file":
        if "content" not in tool_input:
            return "Error: missing content."
        fpath = os.path.join(project_root, tool_input["file_path"])
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, "a") as f:
            f.write(tool_input["content"])
        return f"Appended to {tool_input['file_path']}."

    elif tool_name == "replace_text":
        if "old_text" not in tool_input or "new_text" not in tool_input:
            return "Error: missing old_text/new_text."
        fpath = os.path.join(project_root, tool_input["file_path"])
        if not os.path.exists(fpath):
            return f"Not found: {tool_input['file_path']}"
        with open(fpath) as f:
            content = f.read()
        if tool_input["old_text"] not in content:
            return f"old_text not found in {tool_input['file_path']}."
        with open(fpath, "w") as f:
            f.write(content.replace(tool_input["old_text"], tool_input["new_text"], 1))
        return f"Replaced in {tool_input['file_path']}."

    return f"Unknown tool: {tool_name}"


# ──────────────────────────────────────────────
# Agent tools & system prompt
# ──────────────────────────────────────────────

CONTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "Component or hook name."},
        "kind": {"type": "string", "enum": ["component", "hook", "util", "type"]},
        "file_path": {"type": "string", "description": "Exact file path, e.g. 'src/components/SearchBar/SearchBar.tsx'."},
        "spec": {
            "type": "string",
            "description": (
                "Short natural language spec (2-4 sentences). Cover: "
                "what props it takes, what it renders/returns, key behaviors "
                "(state, effects, events). The child agent will figure out "
                "the exact TypeScript types and implementation details."
            ),
        },
    },
    "required": ["name", "kind", "file_path", "spec"],
}

GEN_TOOLS = [
    {
        "name": "read_file",
        "description": "Read a file's contents from the project.",
        "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}}, "required": ["file_path"]},
    },
    {
        "name": "append_to_file",
        "description": "Append content to a file. Creates file and directories if needed.",
        "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["file_path", "content"]},
    },
    {
        "name": "replace_text",
        "description": "Replace text in a file. Fails if old_text not found.",
        "input_schema": {"type": "object", "properties": {"file_path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["file_path", "old_text", "new_text"]},
    },
    {
        "name": "spawn_child",
        "description": (
            "Spawn a child agent to implement a module. The contract MUST include "
            "file_path — the exact path where the child should write its code. "
            "Returns immediately with task_id."
        ),
        "input_schema": {"type": "object", "properties": {"contract": CONTRACT_SCHEMA}, "required": ["contract"]},
    },
    {
        "name": "wait_all",
        "description": "Wait for ALL pending children at once.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "done",
        "description": "Signal that you are finished. Call this after writing your code and waiting for children.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

GEN_SYSTEM = """\
You are a senior React/TypeScript developer building a project on disk.

You have filesystem tools (read_file, append_to_file, replace_text) to write
code directly to project files. You also have spawn_child to delegate work.

WORKFLOW:
1. Write YOUR code directly to your assigned file using append_to_file.
   Also create barrel exports (index.ts) if you're a component.
2. Spawn children for sub-components/hooks/utils. Keep contracts SHORT —
   just name, kind, file_path, and a 2-4 sentence spec. The child agent
   is a senior dev, it will figure out the TypeScript details.
3. Spawn ALL children at once if possible (they run in parallel).
4. wait_all() for children to finish.
5. done() to signal completion.

PROJECT STRUCTURE:
    src/
      App.tsx
      components/ComponentName/ComponentName.tsx + index.ts
      hooks/useHookName.ts
      utils/utilName.ts
      types/index.ts

RULES:
- Write code DIRECTLY with append_to_file. .tsx for JSX, .ts for logic.
- Keep contracts brief — a few sentences, not full TypeScript interfaces.
- Max 4 children per agent. Spawn them all at once.
- Always call done() when finished.
"""

CHILD_SYSTEM = """\
You are a React/TypeScript developer. You have a contract with a file_path
and a short spec. Implement it.

Tools: read_file, append_to_file, replace_text, spawn_child, wait_all, done.

WORKFLOW:
1. Write your code to your file_path using append_to_file.
2. Create barrel export (index.ts) if you're a component.
3. Spawn children if needed (with file_path + short spec).
4. wait_all() if you spawned children, then done().

RULES:
- Implement what the spec describes. You decide the exact TypeScript types.
- Include proper imports. Use relative paths.
- Max 4 children. If simple, just write and done().
"""


def timed_api_call(timing, **kwargs):
    t0 = time.monotonic()
    response = client.messages.create(**kwargs)
    dt = time.monotonic() - t0
    timing.api_calls.append(dt)
    timing.input_tokens += response.usage.input_tokens
    timing.output_tokens += response.usage.output_tokens
    return response


def format_contract(contract: dict) -> str:
    lines = [
        f"  Name: {contract['name']}",
        f"  Kind: {contract.get('kind', 'component')}",
        f"  File path: {contract.get('file_path', '?')}",
        f"  Spec: {contract.get('spec', '')}",
    ]
    return "\n".join(lines)


def run_agent(task: str, contract: dict | None = None, depth: int = 0,
              max_depth: int = 2, project_root: str = "") -> dict:
    indent = "  " * depth
    if contract:
        name = contract["name"]
        kind = contract.get("kind", "component")
        file_path = contract.get("file_path", "?")
    else:
        name = "root"
        kind = "component"
        file_path = "src/App.tsx"

    timing = AgentTiming(name=name, kind=kind, depth=depth, start=time.monotonic())
    safe_print(f"{indent}[depth={depth}] Agent started: {name} ({kind}) -> {file_path}")

    if contract:
        user_prompt = (
            f"Implement this {kind} and write it to {file_path}:\n\n"
            f"{format_contract(contract)}"
        )
        system = CHILD_SYSTEM
    else:
        user_prompt = (
            f"Build this React application. Write the root component to src/App.tsx, "
            f"then spawn children for sub-components.\n\n{task}"
        )
        system = GEN_SYSTEM

    tools = GEN_TOOLS if depth < max_depth else [t for t in GEN_TOOLS if t["name"] in ("read_file", "append_to_file", "replace_text", "done")]
    if depth >= max_depth:
        user_prompt += "\n\nMax depth. Write your code directly and call done()."

    messages = [{"role": "user", "content": user_prompt}]
    children = []
    pending_futures: dict[str, tuple[Future, dict]] = {}
    is_done = False

    while not is_done:
        response = timed_api_call(
            timing, model="claude-sonnet-4-6", max_tokens=4096,
            system=system, tools=tools, messages=messages,
        )
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

        if response.stop_reason == "end_turn" and not tool_use_blocks:
            break
        if not tool_use_blocks:
            break

        messages.append({"role": "assistant", "content": response.content})
        tool_results = []

        for block in tool_use_blocks:
            if block.name in ("read_file", "append_to_file", "replace_text"):
                result = execute_fs_tool(block.name, block.input, project_root)
                # Track file writes in index
                if block.name in ("append_to_file", "replace_text"):
                    fp = block.input.get("file_path", "")
                    if fp:
                        with _index_lock:
                            if fp not in file_index:
                                file_index[fp] = []
                            if name not in file_index[fp]:
                                file_index[fp].append(name)
                safe_print(f"{indent}  [{block.name}] {block.input.get('file_path', '?')[:50]} -> {result[:40]}")
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": result})

            elif block.name == "spawn_child":
                child_contract = block.input["contract"]
                if isinstance(child_contract, str):
                    try:
                        child_contract = json.loads(child_contract)
                    except json.JSONDecodeError:
                        child_contract = {"name": child_contract, "kind": "component", "file_path": "src/unknown.tsx", "spec": child_contract}
                child_name = child_contract["name"]
                child_kind = child_contract.get("kind", "component")
                child_path = child_contract.get("file_path", "?")
                task_id = str(uuid4())[:8]
                safe_print(f"{indent}  -> Spawning: {child_name} ({child_kind}) -> {child_path} [{task_id}]")
                future = executor.submit(
                    run_agent, child_name, child_contract,
                    depth + 1, max_depth, project_root,
                )
                pending_futures[task_id] = (future, child_contract)
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"task_id": task_id})})

            elif block.name == "wait_all":
                if pending_futures:
                    safe_print(f"{indent}  <- Waiting for {len(pending_futures)} children...")
                    wait_start = time.monotonic()
                    results_list = []
                    for tid, (future, cc) in list(pending_futures.items()):
                        child_node = future.result()
                        children.append(child_node)
                        safe_print(f"{indent}  <- Done: {cc['name']}")
                        results_list.append({"name": cc["name"], "success": True})
                    timing.wait_time += time.monotonic() - wait_start
                    pending_futures.clear()
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": json.dumps({"results": results_list})})
                else:
                    tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": "No pending children."})

            elif block.name == "done":
                is_done = True
                tool_results.append({"type": "tool_result", "tool_use_id": block.id, "content": "Done."})

        messages.append({"role": "user", "content": tool_results})

    # Collect orphans
    for tid, (future, cc) in pending_futures.items():
        wait_start = time.monotonic()
        children.append(future.result())
        timing.wait_time += time.monotonic() - wait_start

    timing.end = time.monotonic()
    with _timings_lock:
        agent_timings.append(timing)

    safe_print(f"{indent}[depth={depth}] Agent done: {name} ({timing.total:.1f}s)")
    return {"name": name, "kind": kind, "file_path": file_path, "contract": contract, "children": children}


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def print_tree(node, indent=0):
    prefix = "  " * indent
    name = node["name"]
    kind = node.get("kind", "component")
    fp = node.get("file_path", "?")
    print(f"{prefix}{name} ({kind})  [{fp}]")
    for child in node["children"]:
        print_tree(child, indent + 1)


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

    project_root = tempfile.mkdtemp(prefix="morph_exp013_")
    total_start = time.monotonic()

    print("=" * 60)
    print("LIGHT CONTRACTS REACT AGENT TREE")
    print("=" * 60)
    print(f"\nRoot task: {root_task}")
    print(f"Project root: {project_root}\n")

    tree = run_agent(root_task, depth=0, max_depth=2, project_root=project_root)

    total_time = time.monotonic() - total_start

    # Results
    print("\n" + "=" * 60)
    print("COMPONENT TREE")
    print("=" * 60)
    print_tree(tree)

    print("\n" + "=" * 60)
    print("FILE INDEX")
    print("=" * 60)
    with _index_lock:
        for path, names in sorted(file_index.items()):
            print(f"  {path}: {', '.join(set(names))}")

    # Timing
    print("\n" + "=" * 60)
    print("TIMING REPORT")
    print("=" * 60)

    total_api_calls = sum(len(t.api_calls) for t in agent_timings)
    total_api_time = sum(t.api_total for t in agent_timings)
    total_input = sum(t.input_tokens for t in agent_timings)
    total_output = sum(t.output_tokens for t in agent_timings)

    print(f"\n  Total wall clock:        {total_time:.1f}s")
    print(f"  Total API calls:         {total_api_calls}")
    print(f"  Total API time:          {total_api_time:.1f}s")
    print(f"  Total input tokens:      {total_input:,}")
    print(f"  Total output tokens:     {total_output:,}")
    print(f"  Total tokens:            {total_input + total_output:,}")

    print(f"\n  --- Agent Timings ({len(agent_timings)} agents) ---")
    print(f"  {'Name':<30} {'Kind':<12} {'D':>1} {'Total':>7} {'API':>7} {'Wait':>7} {'Own':>7} {'#':>3} {'In':>8} {'Out':>7}")
    print(f"  {'-'*30} {'-'*12} {'-'} {'-'*7} {'-'*7} {'-'*7} {'-'*7} {'-'*3} {'-'*8} {'-'*7}")
    for t in sorted(agent_timings, key=lambda x: x.start):
        print(f"  {t.name:<30} {t.kind:<12} {t.depth} {t.total:>6.1f}s {t.api_total:>6.1f}s {t.wait_time:>6.1f}s {t.own_work:>6.1f}s {len(t.api_calls):>3} {t.input_tokens:>8,} {t.output_tokens:>7,}")

    # Parallelism
    serial_time = sum(t.total for t in agent_timings)
    print(f"\n  --- Parallelism ---")
    print(f"  Serial agent time:       {serial_time:.1f}s")
    print(f"  Actual wall clock:       {total_time:.1f}s")
    if total_time > 0:
        print(f"  Speedup:                 {serial_time / total_time:.1f}x")

    # Files on disk
    print(f"\n" + "=" * 60)
    print(f"FILES ON DISK ({project_root})")
    print("=" * 60)
    for dirpath, _, filenames in os.walk(project_root):
        for fname in sorted(filenames):
            fpath = os.path.join(dirpath, fname)
            relpath = os.path.relpath(fpath, project_root)
            print(f"\n# ===== {relpath} =====")
            with open(fpath) as f:
                lines = f.read().split("\n")
            if len(lines) > 50:
                print("\n".join(lines[:50]))
                print(f"  ... ({len(lines) - 50} more lines)")
            else:
                print("\n".join(lines))

    print(f"\nProject written to: {project_root}")
    executor.shutdown(wait=False)


if __name__ == "__main__":
    main()
